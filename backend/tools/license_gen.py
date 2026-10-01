# -*- coding: utf-8 -*-
"""授权码签发工具（厂商侧专用，不要放进交付给客户的镜像里）。

授权是 Ed25519 非对称签名：
  · 私钥只在你手上（本工具生成，保存在 private_keys/ 下，已被 .gitignore 排除）；
  · 公钥填进客户实例的环境变量 LICENSE_PUBLIC_KEY；
  · 客户实例只能验证签名，无法伪造授权码 —— 即使拿到镜像源码也签不出新授权。

用法：
  python tools/license_gen.py init
  python tools/license_gen.py show-key
  python tools/license_gen.py issue --customer "某某公司" --expires 2027-12-31
  python tools/license_gen.py issue --customer "某公司" --expires 2027-12-31 --instance <客户实例指纹>
  python tools/license_gen.py verify --key "eyJ..."

依赖：cryptography（pip install cryptography）
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DEFAULT_KEY_PATH = Path(__file__).resolve().parent.parent.parent / "private_keys" / "license_private.pem"

BANNER = "=" * 66


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _load_private(path: Path):
    from cryptography.hazmat.primitives import serialization

    if not path.exists():
        sys.exit(f"找不到私钥：{path}\n请先执行： python tools/license_gen.py init")
    return serialization.load_pem_private_key(path.read_bytes(), password=None)


def cmd_init(args) -> None:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    path = Path(args.private_key)
    if path.exists() and not args.force:
        sys.exit(f"私钥已存在：{path}（如需覆盖请加 --force）")
    path.parent.mkdir(parents=True, exist_ok=True)
    private_key = Ed25519PrivateKey.generate()
    path.write_bytes(private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ))
    public_raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw,
    )
    print(BANNER)
    print("密钥对已生成")
    print(BANNER)
    print(f"私钥（务必备份、绝不外传、不要提交到 git）：\n  {path}")
    print(f"\n公钥 hex（填进客户实例的环境变量 LICENSE_PUBLIC_KEY）：\n  {public_raw.hex()}")
    print(f"\n公钥 base64（等价写法，任选其一）：\n  {_b64(public_raw)}")
    print("\n下一步：把公钥配到实例，然后为每个客户签发授权码")
    print("  docker run ... -e LICENSE_PUBLIC_KEY=<上面那串 hex> ...")


def cmd_show_key(args) -> None:
    private_key = _load_private(Path(args.private_key))
    from cryptography.hazmat.primitives import serialization

    public_raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw,
    )
    print(f"公钥 hex：\n  {public_raw.hex()}")
    print(f"公钥 base64：\n  {_b64(public_raw)}")


def cmd_issue(args) -> None:
    private_key = _load_private(Path(args.private_key))
    try:
        datetime.strptime(args.expires, "%Y-%m-%d")
    except ValueError:
        sys.exit("到期日期格式应为 YYYY-MM-DD，例如 2027-12-31")

    payload = {
        "v": 1,
        "customer": args.customer,
        "instance": args.instance or "*",
        "expires": args.expires,
        "features": [f.strip() for f in (args.features or "all").split(",") if f.strip()],
        "issued": date.today().isoformat(),
    }
    body = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")
    signature = private_key.sign(body)
    key = f"{_b64(body)}.{_b64(signature)}"

    print(BANNER)
    print("授权码（发给客户，粘贴到后台「系统与授权」页）")
    print(BANNER)
    print(f"  授权对象：{payload['customer']}")
    print(f"  到期日期：{payload['expires']}")
    print(f"  绑定实例：{'不限（*）' if payload['instance'] == '*' else payload['instance']}")
    print(f"  功能项  ：{', '.join(payload['features'])}")
    print("\n授权码：\n")
    print(key)
    if args.out:
        Path(args.out).write_text(key + "\n", encoding="utf-8")
        print(f"\n已写入文件：{args.out}")


def cmd_verify(args) -> None:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    payload_b64, sig_b64 = args.key.strip().split(".", 1)
    body = _unb64(payload_b64)
    if args.public:
        raw = bytes.fromhex(args.public) if len(args.public) == 64 else _unb64(args.public)
        Ed25519PublicKey.from_public_bytes(raw).verify(_unb64(sig_b64), body)
        print("签名有效（使用命令行提供的公钥）")
    else:
        _load_private(Path(args.private_key)).public_key().verify(_unb64(sig_b64), body)
        print("签名有效（使用私钥对应的公钥）")
    print(json.dumps(json.loads(body), ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="授权码签发工具")
    parser.add_argument("--private-key", dest="private_key", default=str(DEFAULT_KEY_PATH),
                        help="私钥路径（默认 private_keys/license_private.pem）")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="生成密钥对")
    p.add_argument("--force", action="store_true", help="覆盖已存在的私钥")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("show-key", help="打印公钥")
    p.set_defaults(func=cmd_show_key)

    p = sub.add_parser("issue", help="签发授权码")
    p.add_argument("--customer", required=True, help="授权对象（公司/个人名称）")
    p.add_argument("--expires", required=True, help="到期日期 YYYY-MM-DD")
    p.add_argument("--instance", default="*", help="绑定实例指纹，默认 * 表示不限")
    p.add_argument("--features", default="all", help="功能项，逗号分隔，默认 all")
    p.add_argument("--out", help="同时写入文件")
    p.set_defaults(func=cmd_issue)

    p = sub.add_parser("verify", help="校验授权码")
    p.add_argument("--key", dest="key", required=True, help="授权码")
    p.add_argument("--public", help="用指定公钥校验（hex 或 base64）")
    p.set_defaults(func=cmd_verify)

    args = parser.parse_args()
    # verify 子命令的 --key 与全局 --key 同名，这里把授权码放回 args.key
    args.func(args)


if __name__ == "__main__":
    main()