"""唯一编号生成器。

业务约束：唯一编号由系统自动生成，与 Excel 里的「商标编号」完全独立，
不参与去重，不允许人工改写，仅用于系统内部识别与工单/合同引用。
格式：TM-20260927-0001（前缀-导入日期-当日流水号，流水号按天重置）
"""
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import SERIAL_PAD, SERIAL_PREFIX
from .models import Trademark


def _prefix(day: date | None = None) -> str:
    d = day or date.today()
    return f"{SERIAL_PREFIX}-{d.strftime('%Y%m%d')}-"


def _max_seq(db: Session, prefix: str) -> int:
    """当天已用的最大流水号。改为取 max(serial_no) 字符串排序，避免全表扫描。"""
    latest = db.execute(
        select(func.max(Trademark.serial_no)).where(Trademark.serial_no.like(f"{prefix}%"))
    ).scalar()
    if not latest:
        return 0
    try:
        return int(str(latest).rsplit("-", 1)[-1])
    except (ValueError, IndexError):
        return 0


def next_serial(db: Session, day: date | None = None) -> str:
    """生成单个唯一编号。"""
    prefix = _prefix(day)
    return f"{prefix}{_max_seq(db, prefix) + 1:0{SERIAL_PAD}d}"


class SerialAllocator:
    """批量导入时使用：一次性读游标，之后在内存里递增，避免逐条查询。"""

    def __init__(self, db: Session, day: date | None = None):
        self.prefix = _prefix(day)
        self._cursor = _max_seq(db, self.prefix)

    def next(self) -> str:
        self._cursor += 1
        return f"{self.prefix}{self._cursor:0{SERIAL_PAD}d}"

    @property
    def allocated(self) -> int:
        return self._cursor