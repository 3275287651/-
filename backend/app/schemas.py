"""请求体模型（仅用于输入校验；响应体为动态结构，直接返回 dict）。"""
from typing import Any, Literal

from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class UserRegisterIn(BaseModel):
    phone: str = Field(min_length=6, max_length=20)
    password: str = Field(min_length=6, max_length=64)
    email: str | None = None
    nickname: str | None = None
    captcha: str | None = None
    captcha_key: str | None = None


class UserLoginIn(BaseModel):
    phone: str
    password: str


class TrademarkIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    trademark_no: str | None = Field(default=None, max_length=64, description="商标编号（官方注册号）")
    category: int | None = None
    products: str | None = None
    groups: str | None = None
    registration_date: str | None = None
    expiry_date: str | None = None
    legal_status: str | None = None
    application_count: int | None = None
    price: float | None = Field(default=None, description="金额，允许为空＝未定价")
    ai_description: str | None = None
    remark: str | None = None
    status: str | None = None
    is_featured: bool | None = None
    images: list[str] | None = None
    extra: dict[str, Any] | None = None


class BatchActionIn(BaseModel):
    action: Literal["on_shelf", "off_shelf", "delete", "set_price", "adjust_price",
                    "set_status", "set_featured", "set_category"]
    ids: list[int] = Field(default_factory=list)
    # set_price
    price: float | None = None
    # adjust_price
    adjust_mode: Literal["percent", "fixed", "set"] | None = None
    adjust_value: float | None = None
    # set_status
    status: str | None = None
    featured: bool | None = None
    category: int | None = None


class ImportCommitIn(BaseModel):
    batch_id: int
    mapping: dict[str, str] = Field(default_factory=dict)
    price_mode: Literal["from_file", "fixed", "none"] = "from_file"
    fixed_price: float | None = None
    status: Literal["on_sale", "off_shelf", "sold", "reserved"] = "off_shelf"
    import_mode: Literal["insert_only", "upsert"] = "insert_only"
    overwrite_images: bool = True
    is_featured: bool = False
    default_category: int | None = None


class ColumnUpdateIn(BaseModel):
    key: str
    visible: bool | None = None
    label: str | None = None
    sort: int | None = None


class QuoteItemIn(BaseModel):
    trademark_id: int
    quote_price: float | None = None


class QuoteCreateIn(BaseModel):
    title: str = "商标报价单"
    customer_name: str | None = None
    contact_phone: str | None = None
    remark: str | None = None
    expire_days: int = 7
    password: str | None = None
    items: list[QuoteItemIn] = Field(default_factory=list)


class SettingsIn(BaseModel):
    values: dict[str, Any]