"""站点配置读写：键值对 + 默认值，键名与计划书配置项一一对应。"""
from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import SiteSetting

DEFAULT_SETTINGS: dict[str, str] = {
    # 基础信息
    "site_name": "尚标易 · 商标交易平台",
    "site_subtitle": "精选现成商标 · 即买即用 · 全程代办",
    "logo_url": "",
    "icp": "京ICP备00000000号",
    "copyright": "© 2026 尚标易 商标交易平台 版权所有",
    "contact_phone": "400-000-0000",
    "address": "北京市朝阳区建国路 88 号",
    "company_intro": "我们专注于现成商标转让撮合服务，覆盖第 3、29、31、35 类等热门类别，"
                     "所有商标均为自有货源，价格公开，转让全程代办。",
    # 客服
    "service_wechat": "shangbiaoyi2026",
    "service_qr": "",
    "service_hours": "周一至周六 09:00-18:00",
    "service_text": "添加客服微信，1 对 1 协助选标与过户",
    # 首页
    "banner": "[]",
    "process_steps": json.dumps([
        {"title": "挑选商标", "desc": "按类别、价格、注册日期筛选，查看核定商品与法律状态"},
        {"title": "加入报价单", "desc": "多个商标一起议价，一键生成专属报价单"},
        {"title": "联系客服", "desc": "加微信确认标的情况与转让细节，签订合同"},
        {"title": "完成转让", "desc": "提交材料、办理公证与商标局过户，全程代办"},
    ], ensure_ascii=False),
    # 详情页字段开关
    "display_fields": json.dumps({
        "trademark_no": True, "category": True, "products": True, "groups": True,
        "registration_date": True, "expiry_date": True, "legal_status": True,
        "application_count": True, "ai_description": True, "remark": True,
        "source_file": False, "serial_no": False,
    }, ensure_ascii=False),
    # SEO
    "seo_home_title": "现成商标转让_商标交易平台_即买即用",
    "seo_home_keywords": "商标转让,现成商标,商标购买,29类商标,35类商标",
    "seo_home_desc": "精选现成商标，价格公开透明，全程代办过户。",
    # 系统
    "quote_default_days": "7",
    "image_max_mb": "5",
    "export_watermark": "false",
    "watermark_text": "尚标易",
    "password_min_len": "8",
}

# 前台可见的配置键（其余仅在后台返回）
PUBLIC_KEYS = {
    "site_name", "site_subtitle", "logo_url", "icp", "copyright", "contact_phone",
    "address", "company_intro", "service_wechat", "service_qr", "service_hours",
    "service_text", "process_steps", "display_fields", "seo_home_title",
    "seo_home_keywords", "seo_home_desc", "quote_default_days",
}


def ensure_defaults(db: Session) -> None:
    exists = {s.key for s in db.execute(select(SiteSetting)).scalars()}
    added = False
    for k, v in DEFAULT_SETTINGS.items():
        if k not in exists:
            db.add(SiteSetting(key=k, value=v))
            added = True
    if added:
        db.commit()


def get_all(db: Session) -> dict[str, str]:
    ensure_defaults(db)
    data = {s.key: s.value for s in db.execute(select(SiteSetting)).scalars()}
    return {**DEFAULT_SETTINGS, **data}


def get_public(db: Session) -> dict:
    allv = get_all(db)
    out = {k: allv.get(k) for k in PUBLIC_KEYS}
    for k in ("process_steps", "display_fields"):
        try:
            out[k] = json.loads(out.get(k) or "[]")
        except json.JSONDecodeError:
            out[k] = [] if k == "process_steps" else {}
    try:
        out["banner"] = json.loads(allv.get("banner") or "[]")
    except json.JSONDecodeError:
        out["banner"] = []
    return out


def set_values(db: Session, values: dict) -> None:
    ensure_defaults(db)
    existing = {s.key: s for s in db.execute(select(SiteSetting)).scalars()}
    for k, v in values.items():
        if isinstance(v, (dict, list)):
            v = json.dumps(v, ensure_ascii=False)
        if k in existing:
            existing[k].value = "" if v is None else str(v)
        else:
            db.add(SiteSetting(key=k, value="" if v is None else str(v)))
    db.commit()