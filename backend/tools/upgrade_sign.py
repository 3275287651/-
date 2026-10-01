# -*- coding: utf-8 -*-
"""升级清单签名工具（厂商侧专用）。

流程：
  1) 本工具对清单做 HMAC-SHA256 签名（密钥 = UPGRADE_KEY，厂商与客户实例各持同一把）；
  2) 客户在后台「系统与授权 → 升级」上传清单 JSON + 镜像包；
  3) 客户实例校验签名与 sha256，通过后暂存并给出应用命令。

这样能挡住「伪造升级包投毒」，但不会让客户的服务去自行替换代码。

用法：
  set UPGRADE_KEY=xxxx            （Windows；Linux 用 export）
  python tools/upgrade_sign.py --version 1.0.4 --file ../release/trademark-market-1.0.4.tar --tag 1.0.4 --notes "修复若干问题"

输出可直接粘贴到后台「升级清单」输入框。
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
from datetime import date
from pathlib import Path

BANNER = "=" * 66


def canonical(manifest: dict) -> bytes:
    body = {k: v for k, v in manifest.items() if k != "signature"}
    return json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="生成并签名升级清单")
    parser.add_argument("--version", required=True, help="新版本号，如 1.0.4")
    parser.add_argument("--file", required=True, help="镜像包路径（.tar）")
    parser.add_argument("--tag", help="镜像 tag，默认与版本号相同")
    parser.add_argument("--name", default="trademark-market", help="镜像名")
    parser.add_argument("--notes", default="", help="更新说明")
    parser.add_argument("--released", default=date.today().isoformat(), help="发布日期")
    parser.add_argument("--key", default=os.getenv("UPGRADE_KEY", ""), help="校验密钥，默认取环境变量 UPGRADE_KEY")
    parser.add_argument("--out", help="同时写入 JSON 文件")
    args = parser.parse_args()

    if not args.key:
        sys.exit("缺少校验密钥：请设置环境变量 UPGRADE_KEY 或用 --key 传入")

    tar_path = Path(args.file)
    if not tar_path.exists():
        sys.exit(f"找不到升级包：{tar_path}")

    raw = tar_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    manifest = {
        "version": args.version,
        "released_at": args.released,
        "notes": args.notes,
        "images": [{
            "name": args.name,
            "tag": args.tag or args.version,
            "file": tar_path.name,
            "sha256": digest,
        }],
    }
    manifest["signature"] = hmac.new(args.key.encode("utf-8"), canonical(manifest),
                                     hashlib.sha256).hexdigest()

    print(BANNER)
    print(f"升级包：{tar_path.name}  {len(raw)/1024/1024:.1f} MB")
    print(f"SHA256：{digest}")
    print(BANNER)
    text = json.dumps(manifest, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"清单已写入：{args.out}")
    print("\n把下面这段清单粘贴到后台「系统与授权 → 升级」：\n")
    print(text)


if __name__ == "__main__":
    main()