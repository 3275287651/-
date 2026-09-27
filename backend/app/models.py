"""数据模型。

核心设计要点（业务方明确要求）：
1. 双编号体系，严格分离：
   - serial_no    唯一编号：系统在上传/录入时自动生成，格式 TM-20260927-0001，内部识别用，永不变更。
   - trademark_no 商标编号：来自 Excel 的官方注册号（如 711386408046645262），是外部权威标识，用于去重/更新。
   两者语义不同，界面上分列展示、分别检索，禁止互相覆盖。
2. price 允许为空：Excel 有价格列则关联，没有则留空（NULL），前台显示为「面议」。
3. extra 动态列：Excel 中出现、系统未预置的列，原样入库，驱动前端表格动态渲染。
"""
from datetime import date, datetime

from sqlalchemy import (
    JSON, Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

TrademarkStatus = ("on_sale", "off_shelf", "sold", "reserved")
STATUS_LABELS = {
    "on_sale": "在售",
    "off_shelf": "已下架",
    "sold": "已售出",
    "reserved": "预留中",
}


# --------------------------------------------------------------------------- #
# 运营账户 / 客户
# --------------------------------------------------------------------------- #
class Admin(Base):
    __tablename__ = "admins"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(50), default="")
    role: Mapped[str] = mapped_column(String(20), default="operator")  # admin | operator
    status: Mapped[int] = mapped_column(Integer, default=1)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(100), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nickname: Mapped[str] = mapped_column(String(50), default="")
    status: Mapped[int] = mapped_column(Integer, default=1)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# --------------------------------------------------------------------------- #
# 商标
# --------------------------------------------------------------------------- #
class Trademark(Base):
    __tablename__ = "trademarks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ---- 双编号 ----
    serial_no: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, index=True,
        comment="唯一编号：系统自动生成，如 TM-20260927-0001",
    )
    trademark_no: Mapped[str | None] = mapped_column(
        String(64), unique=True, nullable=True, index=True,
        comment="商标编号（官方注册号），来自 Excel，如 711386408046645262",
    )

    # ---- 核心字段 ----
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    category: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    products: Mapped[str | None] = mapped_column(Text, nullable=True)
    groups: Mapped[str | None] = mapped_column(String(500), nullable=True)
    registration_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    legal_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    application_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price: Mapped[float | None] = mapped_column(
        Numeric(12, 2), nullable=True, index=True,
        comment="金额：Excel 有则关联，无则留空（NULL）",
    )
    ai_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ---- 运营字段 ----
    status: Mapped[str] = mapped_column(String(20), default="off_shelf", index=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    quote_count: Mapped[int] = mapped_column(Integer, default=0)

    # ---- 动态列：Excel 未预置的列原样保存 ----
    extra: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # ---- 溯源 ----
    source_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    import_batch_id: Mapped[int | None] = mapped_column(
        ForeignKey("import_batches.id", ondelete="SET NULL"), nullable=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    images: Mapped[list["TrademarkImage"]] = relationship(
        back_populates="trademark", cascade="all, delete-orphan", order_by="TrademarkImage.sort"
    )

    __table_args__ = (
        Index("ix_tm_status_cat", "status", "category"),
    )


class TrademarkImage(Base):
    __tablename__ = "trademark_images"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trademark_id: Mapped[int] = mapped_column(
        ForeignKey("trademarks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True)
    source_row: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="来源 Excel 行号，便于溯源")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    trademark: Mapped[Trademark] = relationship(back_populates="images")


# --------------------------------------------------------------------------- #
# 动态列注册表：驱动后台表格「按上传的 Excel 自动渲染列」
# --------------------------------------------------------------------------- #
class TrademarkColumn(Base):
    __tablename__ = "trademark_columns"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), default="extra")  # core | extra
    data_type: Mapped[str] = mapped_column(String(20), default="text")  # text | number | date | price
    sort: Mapped[int] = mapped_column(Integer, default=100)
    visible: Mapped[bool] = mapped_column(Boolean, default=True)
    filled_count: Mapped[int] = mapped_column(Integer, default=0, comment="有值的记录数，用于隐藏空列")
    first_seen_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# --------------------------------------------------------------------------- #
# 导入批次
# --------------------------------------------------------------------------- #
class ImportBatch(Base):
    __tablename__ = "import_batches"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sheet_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    image_count: Mapped[int] = mapped_column(Integer, default=0)
    columns_json: Mapped[list | None] = mapped_column(JSON, nullable=True, comment="源表列结构快照")
    mapping_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="列映射方案")
    options_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="导入选项：默认价/状态/模式")

    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    # pending | running | done | failed
    progress: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    errors_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


# --------------------------------------------------------------------------- #
# 客户行为
# --------------------------------------------------------------------------- #
class Favorite(Base):
    __tablename__ = "favorites"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    trademark_id: Mapped[int] = mapped_column(ForeignKey("trademarks.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    __table_args__ = (UniqueConstraint("user_id", "trademark_id", name="uq_fav_user_tm"),)


class Quote(Base):
    __tablename__ = "quotes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quote_no: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(200), default="商标报价单")
    customer_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_original: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total_quote: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    password: Mapped[str | None] = mapped_column(String(50), nullable=True)
    expire_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    last_view_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    items: Mapped[list["QuoteItem"]] = relationship(
        back_populates="quote", cascade="all, delete-orphan"
    )


class QuoteItem(Base):
    __tablename__ = "quote_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quote_id: Mapped[int] = mapped_column(ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False, index=True)
    trademark_id: Mapped[int | None] = mapped_column(ForeignKey("trademarks.id", ondelete="SET NULL"), nullable=True)
    serial_no: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="快照：唯一编号")
    trademark_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="快照：商标编号")
    trademark_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    category: Mapped[int | None] = mapped_column(Integer, nullable=True)
    original_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    quote_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    quote: Mapped[Quote] = relationship(back_populates="items")


# --------------------------------------------------------------------------- #
# 站点配置 / 内容
# --------------------------------------------------------------------------- #
class SiteSetting(Base):
    __tablename__ = "site_settings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(60), unique=True, nullable=False, index=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    group: Mapped[str] = mapped_column(String(30), default="basic")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class Banner(Base):
    __tablename__ = "banners"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    link_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    subtitle: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class OperationLog(Base):
    __tablename__ = "operation_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin_id: Mapped[int | None] = mapped_column(ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    admin_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    target_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    receiver_type: Mapped[str] = mapped_column(String(20), default="admin")
    receiver_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)


class VisitLog(Base):
    """极简访问统计，用于后台看板趋势图。"""
    __tablename__ = "visit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    day: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)