"""FastAPI 应用入口。"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, select, text

from .config import (
    CORS_ORIGINS, DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_USERNAME, FRONTEND_DIST, SITE_NAME, UPLOAD_DIR,
)
from .database import Base, SessionLocal, engine
from .models import Admin, ImportBatch, TrademarkColumn
from .routers import (
    admin_misc, auth, content, imports, public, quotes, submissions, system, trademarks,
)
from .security import hash_password
from .settings_store import ensure_defaults

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s | %(message)s")
logger = logging.getLogger("trademark")


def _default_literal(col) -> str | None:
    """取出列定义里的静态默认值，转成 SQL 字面量；动态默认值（如 datetime.now）返回 None。"""
    d = getattr(col, "default", None)
    if d is None or getattr(d, "is_callable", False) or getattr(d, "arg", None) is None:
        return None
    v = d.arg
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def _auto_migrate() -> list[str]:
    """加法式迁移：模型里新增、老库里缺失的列自动补齐。

    非空列会带上模型里声明的静态默认值一起 ALTER（SQLite / MySQL 均支持），
    历史行会自动获得默认值，例如 source_type='self'、review_status='approved'。
    结构性变更（改类型、删列、加约束）仍需人工迁移；长期建议引入 Alembic。
    """
    insp = inspect(engine)
    added: list[str] = []
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if not insp.has_table(table.name):
                continue
            existing = {c["name"] for c in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name in existing:
                    continue
                literal = _default_literal(col)
                ddl = f"ALTER TABLE {table.name} ADD COLUMN {col.name} {col.type.compile(engine.dialect)}"
                if not col.nullable:
                    if literal is None:
                        logger.warning("跳过非空且无静态默认值的列 %s.%s，需人工迁移",
                                       table.name, col.name)
                        continue
                    ddl += f" NOT NULL DEFAULT {literal}"
                elif literal is not None:
                    ddl += f" DEFAULT {literal}"
                conn.execute(text(ddl))
                added.append(f"{table.name}.{col.name}")
    if added:
        logger.info("数据库自动迁移，新增列：%s", "、".join(added))
    return added


def _backfill_defaults() -> None:
    """为历史数据补齐新增列的语义默认值（Python 端默认值不会作用于已有行）。"""
    db = SessionLocal()
    try:
        changed = 0
        for stmt in (
            "UPDATE trademarks SET source_type='self' WHERE source_type IS NULL",
            "UPDATE trademarks SET review_status='approved' WHERE review_status IS NULL",
            "UPDATE trademark_images SET kind='design' WHERE kind IS NULL",
        ):
            changed += db.execute(text(stmt)).rowcount or 0
        db.commit()
        if changed:
            logger.info("历史数据补齐默认值：%s 行", changed)
    finally:
        db.close()


def _bootstrap() -> None:
    Base.metadata.create_all(bind=engine)
    _auto_migrate()
    _backfill_defaults()
    db = SessionLocal()
    try:
        ensure_defaults(db)
        if not db.execute(select(Admin).limit(1)).scalar_one_or_none():
            db.add(Admin(
                username=DEFAULT_ADMIN_USERNAME,
                password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
                name="超级管理员",
                role="admin",
            ))
            db.commit()
            logger.info("已创建默认管理员：%s / %s", DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD)
        # 核心列元数据（幂等）：让表格在没有任何导入时也有骨架
        from .importer import CORE_COLUMN_META

        existing = {c.key for c in db.execute(select(TrademarkColumn)).scalars()}
        added = False
        for key, label, dtype, sort, visible in CORE_COLUMN_META:
            if key not in existing:
                db.add(TrademarkColumn(key=key, label=label, kind="core",
                                       data_type=dtype, sort=sort, visible=visible))
                added = True
        if added:
            db.commit()
        # 清理中断的导入批次
        stuck = db.execute(select(ImportBatch).where(ImportBatch.status.in_(["running", "analyzing"]))).scalars().all()
        for b in stuck:
            b.status = "failed"
            b.message = "服务重启导致中断，请重新上传文件后导入"
        if stuck:
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _bootstrap()
    logger.info("%s 后端已启动", SITE_NAME)
    yield


app = FastAPI(title=f"{SITE_NAME} API", version="1.0.0", lifespan=lifespan,
              docs_url="/api/docs", openapi_url="/api/openapi.json")

# 纵深防护中间件：限流 → 请求签名/防重放 → 授权拦截
# 放在 CORS 之前注册，使 CORS 成为最外层，保证 429/401/403 也带上跨域头
from .hardening import HardeningMiddleware  # noqa: E402

app.add_middleware(HardeningMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Captcha-Key", "Content-Disposition"],
)

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(UPLOAD_DIR)), name="media")

app.include_router(auth.router)
app.include_router(trademarks.router)
app.include_router(imports.router)
app.include_router(submissions.router)
app.include_router(content.router)
app.include_router(admin_misc.router)
app.include_router(public.router)
app.include_router(quotes.router)
app.include_router(system.router)


@app.get("/api/health")
def health():
    return {"ok": True, "service": SITE_NAME}


@app.exception_handler(Exception)
async def unhandled(request, exc):  # noqa: ANN001
    logger.exception("未处理异常：%s", exc)
    return JSONResponse(status_code=500, content={"detail": f"服务器内部错误：{exc}"})


# 单容器部署：前端已构建时由后端直接托管（同一端口），前端路由回退到 index.html
from fastapi import HTTPException  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402

_dist = FRONTEND_DIST
if _dist.exists():
    _assets = _dist / "assets"
    if _assets.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets)), name="assets")

    _INDEX = _dist / "index.html"

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):  # noqa: ANN202
        if full_path.startswith(("api/", "media/")):
            raise HTTPException(404, "接口不存在")
        target = _dist / full_path
        if full_path and target.is_file():
            return FileResponse(target)
        return FileResponse(_INDEX)

    logger.info("已挂载前端静态资源：%s", _dist)