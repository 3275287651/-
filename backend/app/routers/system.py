"""系统与授权：版本信息、授权码校验、升级包校验与暂存、重启应用。

升级的设计（不搞"一键静默升级"那种危险动作）：
  厂商侧用 UPGRADE_KEY 对升级清单做 HMAC-SHA256 签名 → 运维把清单与镜像包上传到本页 →
  本实例校验签名与 sha256 完整性 → 落到 data/upgrades/ 并给出准确的 docker 应用命令。
  这样既能防「假升级包投毒」，也不会让本服务去执行替换自身代码这类高危动作。
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..config import APP_VERSION, UPGRADE_DIR, UPGRADE_KEY
from ..database import get_db
from ..deps import current_admin, require_super_admin
from ..hardening import (
    clear_license_cache, current_license, hardening_status, instance_id, version_info,
)
from ..models import Admin, OperationLog
from ..settings_store import set_values

router = APIRouter(prefix="/api/admin/system", tags=["admin-system"])


def canonical_manifest(manifest: dict) -> bytes:
    """签名与校验共用的规范化字节串：去掉 signature 字段、键排序、紧凑分隔符。"""
    body = {k: v for k, v in manifest.items() if k != "signature"}
    return json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def verify_manifest(manifest: dict) -> tuple[bool, str]:
    if not UPGRADE_KEY:
        return False, "本实例未配置升级校验密钥（UPGRADE_KEY），无法校验升级清单"
    signature = str(manifest.get("signature") or "")
    if not signature:
        return False, "升级清单缺少 signature 字段"
    expected = hmac.new(UPGRADE_KEY.encode("utf-8"), canonical_manifest(manifest),
                        hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return False, "升级清单签名校验失败（清单可能被篡改，或双方密钥不一致）"
    return True, ""


def _version_tuple(text: str) -> tuple:
    parts = []
    for piece in str(text).replace("v", "").split("."):
        parts.append(int(piece) if piece.isdigit() else 0)
    return tuple(parts + [0, 0, 0])[:3]


# --------------------------------------------------------------------------- #
@router.get("/version")
def version(admin: Admin = Depends(current_admin)):
    """当前版本与实例指纹：所有登录用户可见（后台页脚/关于处展示）。"""
    info = version_info()
    info.update({
        "app_name": "现成商标交易平台",
        "python": f"{__import__('sys').version_info.major}.{__import__('sys').version_info.minor}",
        "license_valid": current_license().valid,
    })
    return info


@router.get("/status")
def status(db: Session = Depends(get_db), admin: Admin = Depends(require_super_admin)):
    """当前防护姿态与授权状态（仅超级管理员）。"""
    data = hardening_status()
    data["version"] = version_info()
    data["upgrade"] = {
        "key_configured": bool(UPGRADE_KEY),
        "staged": _staged_files(),
    }
    return data


# --------------------------------------------------------------------------- #
# 授权码
# --------------------------------------------------------------------------- #
@router.put("/license")
def save_license(payload: dict, db: Session = Depends(get_db),
                 admin: Admin = Depends(require_super_admin)):
    key = str(payload.get("key") or "").strip()
    if not key:
        raise HTTPException(400, "请填写授权码")
    set_values(db, {"license_key": key})
    clear_license_cache()
    result = current_license(force=True)
    db.add(OperationLog(admin_id=admin.id, admin_name=admin.name or admin.username,
                        action="license_update", target_type="system",
                        detail=json.dumps({"valid": result.valid, "customer": result.customer,
                                           "expires": result.expires_at,
                                           "reason": result.reason}, ensure_ascii=False)))
    db.commit()
    if not result.valid:
        raise HTTPException(400, f"授权码未通过校验：{result.reason}")
    return {"ok": True, "license": result.as_dict(), "message": "授权码已保存并生效"}


@router.delete("/license")
def clear_license(db: Session = Depends(get_db), admin: Admin = Depends(require_super_admin)):
    set_values(db, {"license_key": ""})
    clear_license_cache()
    db.add(OperationLog(admin_id=admin.id, admin_name=admin.name or admin.username,
                        action="license_clear", target_type="system"))
    db.commit()
    return {"ok": True, "license": current_license(force=True).as_dict()}


# --------------------------------------------------------------------------- #
# 升级
# --------------------------------------------------------------------------- #
@router.post("/upgrade/check")
def upgrade_check(payload: dict, admin: Admin = Depends(require_super_admin)):
    """校验厂商签发的升级清单，并给出「是否有新版本」的结论。"""
    manifest = payload.get("manifest")
    if not isinstance(manifest, dict):
        raise HTTPException(400, "请提供升级清单 JSON")
    ok, why = verify_manifest(manifest)
    if not ok:
        raise HTTPException(400, why)
    remote = str(manifest.get("version") or "")
    newer = _version_tuple(remote) > _version_tuple(APP_VERSION)
    return {
        "ok": True,
        "signed": True,
        "current_version": APP_VERSION,
        "remote_version": remote,
        "released_at": manifest.get("released_at"),
        "notes": manifest.get("notes"),
        "images": manifest.get("images") or [],
        "has_update": newer,
        "message": f"发现新版本 {remote}，可上传镜像包进行校验" if newer else "当前已是最新版本",
    }


def _staged_files() -> list[dict]:
    files = []
    for p in sorted(UPGRADE_DIR.glob("*"), key=lambda x: x.stat().st_mtime, reverse=True):
        if p.is_file():
            files.append({
                "name": p.name,
                "size": p.stat().st_size,
                "megabytes": round(p.stat().st_size / 1024 / 1024, 1),
                "staged_at": datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
            })
    return files


@router.post("/upgrade/stage")
async def upgrade_stage(manifest_json: str = File(...), file: UploadFile = File(...),
                        db: Session = Depends(get_db),
                        admin: Admin = Depends(require_super_admin)):
    """上传镜像包 + 升级清单：校验签名与 sha256 后落到 data/upgrades/。"""
    try:
        manifest = json.loads(manifest_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(400, "升级清单不是合法 JSON") from exc
    ok, why = verify_manifest(manifest)
    if not ok:
        raise HTTPException(400, why)

    target_name = Path(file.filename or "package.bin").name
    if not target_name.endswith((".tar", ".tar.gz", ".zip")):
        raise HTTPException(400, "仅接受 .tar / .tar.gz / .zip 升级包")
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "升级包为空")

    digest = hashlib.sha256(raw).hexdigest()
    expected = ""
    for image in manifest.get("images") or []:
        if str(image.get("file") or "") == target_name:
            expected = str(image.get("sha256") or "").lower()
            break
    if not expected:
        raise HTTPException(
            400, f"升级清单中没有声明文件 {target_name}（清单里的文件："
                 f"{'、'.join(str(i.get('file')) for i in manifest.get('images') or []) or '无'}）")
    if digest != expected:
        raise HTTPException(400, f"升级包校验失败：清单声明的 sha256 与文件实际值不一致（实际 {digest[:16]}…）")

    target = UPGRADE_DIR / target_name
    target.write_bytes(raw)

    images = manifest.get("images") or []
    commands = [f"docker load -i data/upgrades/{target_name}"]
    for image in images:
        repo = image.get("name") or "trademark-market"
        tag = image.get("tag") or manifest.get("version")
        commands += [
            "docker rm -f trademark",
            f"docker run -d --name trademark -p 8080:8000 "
            f"-v trademark-data:/app/data -v trademark-uploads:/app/uploads "
            f"--restart=always {repo}:{tag}",
        ]
        break

    db.add(OperationLog(admin_id=admin.id, admin_name=admin.name or admin.username,
                        action="upgrade_stage", target_type="system",
                        detail=json.dumps({"file": target_name, "sha256": digest,
                                           "version": manifest.get("version")}, ensure_ascii=False)))
    db.commit()
    return {
        "ok": True,
        "staged": {"name": target_name, "sha256": digest, "megabytes": round(len(raw) / 1024 / 1024, 1)},
        "version": manifest.get("version"),
        "commands": commands,
        "message": "升级包已校验并暂存。数据在数据卷中，换镜像不会丢；按下面命令应用即可。",
    }


@router.delete("/upgrade/staged/{name}")
def delete_staged(name: str, admin: Admin = Depends(require_super_admin)):
    target = (UPGRADE_DIR / Path(name).name)
    if not target.exists():
        raise HTTPException(404, "暂存文件不存在")
    target.unlink()
    return {"ok": True, "staged": _staged_files()}


@router.post("/restart")
def restart(admin: Admin = Depends(require_super_admin)):
    """重启本进程（容器 --restart=always 会自动拉起）。

    注意：这只重启当前镜像里的服务，不会替换镜像本身 —— 换版本请先 docker load 新镜像。
    """
    threading.Timer(1.5, lambda: os._exit(0)).start()
    return {"ok": True, "message": "服务将在 2 秒内重启（容器会由 --restart=always 自动拉起），请稍后刷新页面"}


@router.get("/instance")
def instance():
    """实例指纹（无需登录也能看，便于客户把指纹提供给我们签发授权码）。"""
    return {"instance_id": instance_id()}