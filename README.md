# 尚标易 · 商标交易撮合平台

现成商标展示 + 报价单撮合系统。核心是**用 Excel 批量管货**：上传你的商标表，系统自动识别列、按行提取图样、生成内部唯一编号，之后可批量上架 / 下架 / 改价 / 删除。

---

## 一、两条编号，互不干扰（重点）

| 编号 | 字段 | 来源 | 用途 | 是否可变 |
|------|------|------|------|----------|
| **唯一编号** | `serial_no` | 系统在导入时自动生成，格式 `TM-20260927-0001`（前缀-日期-当日流水号） | 系统内部识别、批次溯源、工单/合同引用 | 永不变更，覆盖更新时也保持不变 |
| **商标编号** | `trademark_no` | 你的 Excel「商标编号」列（官方注册号，如 `711386408046645262`） | 判重、更新已有记录、对外展示为「注册号」 | 可修改，是导入去重的唯一依据 |

界面上的区分：唯一编号带深蓝 `唯一` 徽标，商标编号带浅蓝 `注册号` 徽标，均支持一键复制；搜索框同时检索两者，输入 `TM-` 开头时提示「已按唯一编号前缀检索」。**前台不展示唯一编号**，只展示商标编号。

> 18–19 位的注册号超过 JavaScript 安全整数范围，系统全程按字符串处理，不会出现科学计数法或精度丢失。

## 二、金额（有就关联，没有就留空）

- Excel 里有「价格 / 金额 / 售价 / 报价 / 转让价」等列 → **自动识别并关联**。
- Excel 里没有金额列 → 该字段留空（数据库 `NULL`），前台显示「面议」，后台显示灰色「未定价」标签。
- 导入时可三选一：**跟随源表列** / **统一设为某价** / **不设金额**；导入后随时用**批量改价**补：「统一设为」「按比例调整（±%）」「统一加减（±元）」；按比例/加减会跳过未定价记录，避免把空值算成 0。
- 覆盖更新已有记录时，若源表没有金额，不会清空已有人工定价。

## 三、列自动渲染（上传什么 Excel，就出什么列）

导入时系统记录源表列结构：能对上的映射成系统字段，**对不上的原样存为自定义列**（如「货主」「成本价」「摆位」），并立刻出现在后台表格里，还可在「列设置」中控制显隐。列填充率为 0 的空列自动隐藏，不干扰视线。

导入完成后可随时在「列设置」抽屉里看到每列来源文件、数据形态与有值条数。

---

## 四、本地运行（Windows，无需 Docker）

```bash
# 后端（Python 3.10+，依赖：fastapi / sqlalchemy / openpyxl / pillow / pyjwt / python-multipart）
双击「启动后端.bat」        # 或 cd backend && python -m uvicorn app.main:app --port 8000 --reload

# 前端（Node 18+）
双击「启动前端.bat」        # 或 cd frontend && npm install && npm run dev
```

| 入口 | 地址 |
|------|------|
| 前台 | http://127.0.0.1:5173 |
| 运营后台 | http://127.0.0.1:5173/admin/login |
| 接口文档 | http://127.0.0.1:8000/api/docs |

默认账号 **admin / admin888**（登录后请立即在「运营账户」里改密码）。
本地默认使用 SQLite（`backend/data/trademark.db`），无需安装数据库；图片存放在 `backend/uploads/trademarks/`。

---

## 五、Docker 部署

### 5.1 单镜像（推荐：载入即用，无需 MySQL）

镜像包：`release/trademark-market-1.0.4.tar`（当前版本，含手机版自适应、客户寄售、内容迁移、网页头品牌化、纵深防护与授权升级链路）。
镜像 `trademark-market:1.0.4` 为**前后端一体**：内置 SQLite 数据库，前端静态资源由后端同端口托管，不依赖 MySQL / Redis / Nginx，一条 `docker run` 就能用。
（`release/trademark-market-1.0.3.tar`、`1.0.2.tar`、`1.0.0.tar` 为历史版本，保留用于回滚。）

**方式一：双击 `载入镜像并启动.bat`** —— 自动完成「载入镜像 → 启动容器 → 打开浏览器」，并在镜像已存在时跳过重复载入。

**方式二：命令行两步**

```bash
docker load -i release/trademark-market-1.0.4.tar

docker run -d --name trademark -p 8080:8000 \
  -v trademark-data:/app/data -v trademark-uploads:/app/uploads \
  --restart=always trademark-market:1.0.4
```

打开 `http://127.0.0.1:8080`，后台 `http://127.0.0.1:8080/admin/login`，默认账号 **admin / admin888**（首次启动自动创建）。

**说明**

| 项目 | 说明 |
|------|------|
| 数据库 | 容器内 SQLite：`/app/data/trademark.db`（自动建表，无需初始化） |
| 图样与导入文件 | `/app/uploads`（按批次分目录存放） |
| 持久化 | 上面两个路径已声明为 docker 卷，`docker run` 里用命名卷挂载，删容器不丢数据 |
| 开机自启 | `--restart=always`，Docker 重启后容器自动拉起 |
| 换端口 | 把 `-p 8080:8000` 改成 `-p 80:8000`（前面可再挂宝塔/Nginx 做 HTTPS） |
| 健康检查 | 内置 `HEALTHCHECK` 探针，`docker ps` 会显示 `(healthy)` |

**可选环境变量**（在 `docker run` 上加 `-e`）

| 变量 | 默认 | 用途 |
|------|------|------|
| `DEFAULT_ADMIN_PASSWORD` | `admin888` | 首次启动创建的管理员密码 |
| `SECRET_KEY` | dev 占位值 | 登录令牌签名密钥，**公网部署务必自定义** |
| `SERIAL_PREFIX` | `TM` | 唯一编号前缀（唯一编号格式 `TM-20260927-0001`） |
| `SITE_NAME` | 尚标易 | 站点名 |
| `DATABASE_URL` | SQLite | 想用 MySQL 时填 `mysql+pymysql://用户:密码@主机:3306/trademark?charset=utf8mb4`（镜像已内置 pymysql + cryptography 驱动，同一镜像即可切换） |

**升级**：改完代码后

```bash
docker build --provenance=false --sbom=false --build-arg APP_VERSION=1.0.4 -t trademark-market:1.0.4 .
docker save -o release/trademark-market-1.0.4.tar trademark-market:1.0.4
# 服务器上：
docker load -i trademark-market-1.0.4.tar
docker rm -f trademark
docker run -d --name trademark -p 8080:8000 \
  -v trademark-data:/app/data -v trademark-uploads:/app/uploads \
  --restart=always trademark-market:1.0.4
```

数据都在卷里，换镜像不会丢。回滚就是重新 `docker run` 上一版镜像。
**换镜像后首次启动会自动做加法式数据库迁移**：模型里新增而老库缺失的列会被自动 `ALTER TABLE` 补上（非空列带默认值，历史行自动填），所以「新镜像 + 旧数据卷」不会因为缺列报错。结构性变更（改类型、删列、加约束）仍需人工迁移。

> 小版本升级（如 1.0.3 → 1.0.4）时，记得把 `载入镜像并启动.bat` 里的 `IMAGE` 与 `TARFILE` 两行版本号一起改掉。

**把本地已有数据搬进容器**（例如本地 SQLite 里的 1489 件商标与图样）

```bash
docker cp backend/data/trademark.db trademark:/app/data/
docker cp backend/uploads/trademarks/. trademark:/app/uploads/trademarks/
docker restart trademark
```

### 5.2 多容器方案（MySQL + Nginx，docker-compose）

适合需要独立数据库、多副本或已有 MySQL 运维体系的场景：

```bash
cp .env.example .env      # 必改：SECRET_KEY、MYSQL_PASSWORD、DEFAULT_ADMIN_PASSWORD
docker compose up -d --build
docker compose logs -f backend
```

访问 `http://服务器IP:8080`，后台 `http://服务器IP:8080/admin/login`。

**编排内容**：`mysql:8.0`（utf8mb4）+ 后端（FastAPI，含 Excel 解析）+ 前端（Nginx 托管静态资源并反代 `/api`、`/media`）。
未纳入 Redis：当前图形验证码用进程内存实现，单副本部署无需 Redis；将来扩容多副本时再引入并改造验证码存储。

**数据持久化卷**：`mysql_data`（数据库）、`tm_uploads`（图样与导入文件）、`tm_data`。升级时用 `docker compose pull && docker compose up -d`，这三个卷不会丢。

**宝塔面板步骤**：面板「Docker」→ 安装 Docker 管理器 → 上传项目目录（或用 Git 拉取）→ 复制 `.env` 并改密码 → 终端执行 `docker compose up -d --build` → 在「网站」里新建站点并反向代理到 `http://127.0.0.1:8080` → 申请 SSL 证书并开启强制 HTTPS。

### 5.3 备份

单镜像方案（SQLite）：

```bash
docker cp trademark:/app/data/trademark.db backup_$(date +%F).db
docker run --rm -v trademark-uploads:/data -v $(pwd):/backup alpine tar czf /backup/uploads_$(date +%F).tar.gz -C /data .
```

多容器方案（MySQL）：

```bash
docker exec tm-mysql mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" trademark > backup_$(date +%F).sql
docker run --rm -v trademark-market_tm_uploads:/data -v $(pwd):/backup alpine tar czf /backup/uploads_$(date +%F).tar.gz -C /data .
```

---

## 六、批量导入流程

后台 →「商标管理 / 批量导入」：

1. **上传**：拖拽或点击选择，支持一次多选 `.xlsx / .xlsm / .csv`（旧版 `.xls` 请先另存为 xlsx）。
2. **列映射与预览**：系统自动识别表头（商标名 / 类别 / 商标编号 / 金额 / 产品服务 / 群组 / 注册日期 / 申请量 / AI释义 / 备注 / 图样），可手动改；对不上的列默认「★ 作为自定义列保留」。下方实时预览前 20 行，**图样按 Excel 行号自动关联**。
3. **导入设置**：金额来源、重复处理（跳过 / 覆盖更新）、导入后状态、是否精选、缺类别时的默认类别。
4. **执行**：后台任务 + 进度轮询，结束显示新增 / 更新 / 跳过 / 失败数量，失败与跳过明细可下载 CSV。

导入记录在「导入批次」页，可回溯每个文件的列结构与错误明细，可选择「仅删批次记录」或「连同该批商标一起删除」。

**解析说明**：图样取自 Excel 单元格中的浮动图片，按锚点行号与数据行一一对应（已针对你现有的 554 件 / 935 件表格验证：全部 `TwoCellAnchor`、1 行 1 图、准确率 100%）。锚点异常时会按最接近的数据行兜底关联并给出提示。

## 七、其他已实现能力

- 商标列表：多条件筛选（类别 / 状态 / 已定价·未定价 / 金额区间 / 注册日期区间 / 精选）、搜索、点击列排序、分页 20–200、单条详情抽屉、一键复制两个编号。
- 批量操作：上架、下架、删除（二次确认）、统一改价、按比例调价、统一加减、标记已售出 / 预留中、设 / 取消精选、批量改类别、导出 Excel（含图样链接列或嵌入图片，前两列固定为唯一编号与商标编号）。
- 到期提醒：按 30 / 90 / 180 / 365 天筛选，显示剩余天数，支持批量改状态；注册日期缺失有效期时按 +10 年自动推算。
- 数据看板：商标状态分布、未定价数量、图样总数、客户与报价单数、近 30 天访问趋势、类别与价格区间分布。
- 前台：首页（Hero / 类别入口 / 精选 / 最新上架 / 交易流程）、商标列表（筛选 + 卡片网格 + 排序 + 分页）、详情页（字段开关受后台控制、同类别推荐）、收藏、报价单购物车（逐项调价）、生成报价单（分享链接可加访问密码 + 有效期 + 导出 Excel）、报价单分享页（密码校验 / 过期提示）。
- 后台配置：网站基础信息、客服微信与二维码、首页轮播图（最多 5 张）、详情页字段开关、交易流程步骤、SEO、系统参数；运营账户管理（超级管理员 / 普通运营）；操作日志。
- **客户寄售（C2B2C）**：客户在前台「我要卖标」上传自己的商标 → **商标图样与商标证两份独立材料**（商标证仅后台与提交人可见，前台不公开）→ 客户自定价 → 后台「寄售审核」通过（可改价、可直接上架）或驳回（原因必填）。审核前该商品在前台**完全不可见**（接口返回 404、不进列表与搜索）；通过并上架后才对外展示。客户可在个人中心「我的寄售」查看状态、修改后重新提交（回到待审核）或撤回。
- **内容包迁移（镜像与内容分离）**：后台「内容迁移」一键导出 ZIP（全部业务数据 + 图样/商标证/Logo 等上传文件），在另一个实例上导入即原样恢复，实现换服务器/换镜像时内容独立搬迁；导入为「清空并整体替换」，失败自动回滚，且**不影响运营账户与操作日志**。
- **网页头品牌化**：后台改网站名称 / Logo / 浏览器图标（favicon）后，浏览器标签页标题与图标、前台与后台各页面标题会立即跟随（配置接口禁用缓存，不用等浏览器缓存过期）。
- **手机版自适应（前台，后台仍为 PC 版）**：四档断点 1100 / 820 / 700 / 620px。窄屏下主导航收进抽屉并内置搜索、站点名自动收敛为短名（避免「尚标易 · 商标交易…」这类省略号截断）、报价单/分享页/我的报价单三处宽表自动堆叠成卡片（不再左右拖动）、弹窗统一收敛为屏幕宽、输入框字号 ≥16px 避免 iOS 聚焦放大、筛选与分页重排、触控目标 ≥44px，并适配刘海屏安全区（`viewport-fit=cover` + `safe-area-inset`）。已用 375 / 720px 真实渲染逐页测量：无横向溢出、无文本截断、无元素重叠。
- 安全：PBKDF2 密码哈希、JWT 令牌、角色权限校验（网站配置 / 账户管理 / 内容迁移 / 日志仅超级管理员）、图形验证码。

## 八、目录结构

```
├─ backend/                 FastAPI 服务
│  ├─ app/
│  │  ├─ excel_reader.py    Excel 解析：动态列识别、图片按行提取、类型清洗
│  │  ├─ importer.py        导入服务：分析快照 → 落库、唯一编号分配、去重更新
│  │  ├─ exporter.py        导出（编号前置、图样内嵌可选）
│  │  ├─ serial.py          唯一编号生成器 TM-YYYYMMDD-NNNN
│  │  ├─ models.py          数据模型（双编号 / 可空金额 / extra 动态列 / 寄售来源与审核）
│  │  ├─ hardening.py       纵深防护：限流 / 请求签名与防重放 / 实例指纹 / 授权校验
│  │  └─ routers/           认证、商标、导入、寄售提交与审核、内容包、系统与授权、前台、报价单、后台杂项
│  ├─ tools/                厂商侧工具（不随镜像交付）
│  │  ├─ license_gen.py     生成密钥对 / 签发授权码 / 校验授权码
│  │  └─ upgrade_sign.py    生成并签名升级清单
│  ├─ e2e_check.py          真实数据端到端自测（导入/双编号/检索/批量操作/导出）
│  ├─ e2e_dynamic.py        动态列 + 去重 + 覆盖更新自测
│  ├─ e2e_submission.py     客户寄售全链路 + 内容包导入导出自测
│  ├─ e2e_hardening.py      限流 / 授权码（篡改·过期·换机）/ 升级清单签名自测
│  ├─ e2e_signature.py      请求签名与防重放自测（需 SIGN_MODE=write 启动）
│  └─ container_check.py    容器实例业务验收（对已运行容器跑一遍完整流程）
│                            container_check_v11.py 额外覆盖寄售审核、内容包、网页头配置
├─ private_keys/            授权私钥目录（已 .gitignore 排除，务必离线备份）
├─ frontend/                Vue3 + Vite + TS + Element Plus
│  └─ src/
│     ├─ admin/             后台页面（含 SubmissionReview 寄售审核、ContentTransfer 内容迁移、SystemInfo 系统与授权）
│     ├─ site/              前台页面（含 SellSubmission 我要卖标）
│     ├─ utils/branding.ts  网页头品牌化（标题 + favicon）
│     └─ utils/signing.ts   请求签名（Web Crypto HMAC-SHA256 + nonce 防重放）
├─ Dockerfile               单镜像构建（前端构建 → 后端一体，内置 SQLite）
├─ release/                 导出的镜像包：trademark-market-1.0.4.tar（当前）、1.0.3 / 1.0.2 / 1.0.0（回滚用）
├─ 载入镜像并启动.bat        一键：docker load + docker run + 打开浏览器
├─ docker-compose.yml       多容器编排（MySQL + Nginx），见 5.2
└─ 启动后端.bat / 启动前端.bat   本地开发用（不需要 Docker）
```

## 九、环境变量

| 变量 | 默认 | 说明 |
|------|------|------|
| `DATABASE_URL` | SQLite 文件 | 生产用 `mysql+pymysql://用户:密码@mysql:3306/trademark?charset=utf8mb4` |
| `SECRET_KEY` | dev 占位值 | 令牌签名密钥，**生产必须修改** |
| `SERIAL_PREFIX` | `TM` | 唯一编号前缀 |
| `DEFAULT_ADMIN_USERNAME/PASSWORD` | admin / admin888 | 首次启动创建的管理员 |
| `UPLOAD_DIR` / `DATA_DIR` | backend 下 | 图片与数据目录，容器内映射到数据卷 |
| `MAX_UPLOAD_MB` | 100 | 单文件上传上限 |
| `CORS_ORIGINS` | 本地端口 | 前后端不同域时填写前端地址 |
| `APP_VERSION` / `BUILD_TIME` | 1.0.4 / 空 | 版本与构建时间，后台「系统与授权」页展示 |
| `UPGRADE_KEY` | 空 | 升级清单 HMAC 签名密钥；不配则无法校验升级包 |
| `TRUST_PROXY` | `false` | 反向代理（Nginx / 瑞数）后面部署时置 `true`，才信任 `X-Forwarded-For` |
| `RATE_LIMIT_PER_MIN` / `RATE_LIMIT_LOGIN_PER_MIN` | 600 / 30 | 单 IP 每分钟请求上限（普通接口 / 验证码注册登录） |
| `SIGN_MODE` | `off` | 请求签名与防重放：`off` / `write`（仅写操作）/ `all`；**启用后必须 HTTPS** |
| `SIGN_WINDOW_SECONDS` | 300 | 签名时间戳允许漂移窗口（秒） |
| `LICENSE_PUBLIC_KEY` | 空 | 授权公钥（hex 或 base64）；不配则授权模块不启用 |
| `LICENSE_ENFORCE` | `warn` | 超期处理：`warn` / `block_admin_write` / `block_all` |

## 十、安全、授权与升级（防逆向 / 防爬 / 升级链路）

### 10.1 先说清楚能力边界（不夸大）

- **前端代码无法真正保密**：JS 最终要在浏览器里执行，混淆只能提高读代码门槛，不能"防止逆向"。
- **后端也是**：只要把镜像交付出去，`docker save` 解包就能看到源码 —— 所以最有效的保护是**SaaS 自营交付**（代码与数据都不出你的服务器）。
- 本系统提供的是**抬高门槛 + 防滥用**的组合：能挡住脚本化抓取、批量爬取、请求重放、伪造升级包；挡不住有资源、有耐心的定向破解。
- 「防逆向（保护代码）」与「防爬（保护数据）」是两件不同的事，下面的措施分别对应。

### 10.2 已实现（四层，按需开启）

| 层 | 内容 | 开启方式 | 默认 |
|---|---|---|---|
| 1. 限流 | 单 IP 滑动窗口：普通接口 600/分，凭证类接口 30/分，超限返回 429 并带 `Retry-After` | `RATE_LIMIT_PER_MIN` / `RATE_LIMIT_LOGIN_PER_MIN` | **开启** |
| 2. 请求签名 + 防重放 | 写操作必须带 `X-TS` / `X-Nonce` / `X-Sign`（HMAC-SHA256，密钥=登录令牌，签名覆盖 `方法+路径+时间戳+nonce+请求体摘要`），5 分钟时间窗 + nonce 一次性 | `SIGN_MODE=write`（或 `all`） | 关闭 |
| 3. 授权（License） | Ed25519 非对称签名授权码，可绑定实例指纹、带到期时间；超期可只提示或直接拦截 | `LICENSE_PUBLIC_KEY` + `LICENSE_ENFORCE` | 仅提示 |
| 4. 升级链路 | 升级清单 HMAC 签名 + 升级包 sha256 校验，通过后才暂存并给出应用命令 | `UPGRADE_KEY` | 未配置 |

另外还做了：关闭 uvicorn 指纹（`--no-server-header`）、`X-Content-Type-Options` / `Referrer-Policy` 响应头、运营账户与操作日志不进内容包、`.gitignore` 排除运行数据与私钥。

**启用第 2 层前请注意**：签名的密钥是登录令牌，需要浏览器具备 Web Crypto —— 只有 HTTPS（或 localhost）可用；同时任何第三方对接方（含自带脚本）也要按同一规则签名。建议先 `SIGN_MODE=off` 跑通业务，上线 HTTPS 后再切 `write`。

### 10.3 授权码：怎么签发、怎么生效

```bash
# ① 厂商侧（只在你这里执行一次）：生成密钥对
python tools/license_gen.py init
#   → 私钥写到 private_keys/license_private.pem（已被 .gitignore 排除，务必离线备份）
#   → 打印公钥 hex，填进实例环境变量 LICENSE_PUBLIC_KEY

# ② 客户实例启动时带上公钥
docker run ... -e LICENSE_PUBLIC_KEY=<公钥hex> -e LICENSE_ENFORCE=block_admin_write ...

# ③ 客户在后台「系统与授权」页复制实例指纹给你，你签发授权码
python tools/license_gen.py issue --customer "某某公司" --expires 2027-12-31 --instance <实例指纹>
#   不带 --instance 则绑定为 *（不限实例）

# ④ 客户把授权码粘到后台「系统与授权 → 授权码」保存即可
```

要点：**私钥永远不出你的电脑**，客户实例里只有公钥，所以即使客户拿到镜像源码也签不出新授权码。想收回授权就让授权码到期，或把 `LICENSE_ENFORCE` 切到拦截档。

### 10.4 升级：怎么发版、客户怎么升

```bash
# ① 厂商侧：构建并导出新镜像
docker build --provenance=false --sbom=false --build-arg APP_VERSION=1.0.4 \
  -t trademark-market:1.0.4 .
docker save -o release/trademark-market-1.0.4.tar trademark-market:1.0.4

# ② 生成并签名升级清单（需设置 UPGRADE_KEY，与客户实例一致）
set UPGRADE_KEY=你的升级密钥
python tools/upgrade_sign.py --version 1.0.4 --file ../release/trademark-market-1.0.4.tar \
  --tag 1.0.4 --notes "修复若干问题"
#   → 输出一段 JSON

# ③ 客户后台「系统与授权 → 升级」：粘贴清单 → 校验 → 上传 tar → 得到应用命令
docker load -i data/upgrades/trademark-market-1.0.4.tar
docker rm -f trademark && docker run -d --name trademark -p 8080:8000 \
  -v trademark-data:/app/data -v trademark-uploads:/app/uploads \
  --restart=always trademark-market:1.0.4
```

刻意**不做"一键静默替换自身代码"**：那种设计一旦被投毒就是整个站点失守。现在的做法是"验签 + 落盘 + 给人执行命令"，安全边界清晰。数据都在数据卷里，换镜像不会丢。

### 10.5 前端混淆与后端二进制化

```bash
# 前端混淆（默认开启，构建时生效）
OBFS_ENABLE=true npx vite build      # 关闭：OBFS_ENABLE=false
#   实测：33 个业务 chunk 870KB → 920KB，第三方大包（>400KB）不混淆以保证兼容与构建速度

# 后端二进制化（可选镜像，镜像内不含明文 .py）
docker build --target hardened -t trademark-market:1.0.3-hardened .
```

混淆配置刻意保守（不开 `selfDefending` / `debugProtection`，避免破坏运行与排障）；只混淆业务代码，不动第三方库。

### 10.6 如果采购了瑞数（或其它动态防护/WAF）

瑞数是**按授权收费的商业产品**，部署形态一般是反向代理或云防护，不在应用代码里。接入时只需保证两件事：

```nginx
# Nginx 在瑞数之后（或瑞数云防护回源到你）时：把真实客户端 IP 透传进来
location / {
    proxy_pass http://127.0.0.1:8080;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;   # 瑞数会填真实客户端 IP
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

同时把实例的 `TRUST_PROXY=true`（这样限流按真实 IP 计算，而不是把瑞数的出口 IP 当成所有人）。瑞数自身的 JS 挑战、动态 token 由它在边缘完成，不需要改业务代码。

**采购时建议向瑞数确认这几点**：按域名还是按实例授权、是否支持你这种"后端 API + SPA"结构、回源时真实 IP 放在哪个头（`X-Forwarded-For` / 自定义头）、以及是否提供源站白名单（只允许瑞数回源）。

## 十一、已知边界与后续建议

1. 导入为单进程后台任务（进度可轮询）。当前 935 件 + 935 张图约 3 秒；若单批上万件，建议接入 Celery 队列分片处理。
2. 图形验证码为进程内存实现，多副本部署前需换成 Redis。
3. 报价单导出提供 Excel；PDF 需额外引入 WeasyPrint 或前端打印样式（未实现）。
4. 未实现：邮件通知（SMTP）、浏览历史、图片自动压缩与水印、SEO 服务端预渲染。前台为 SPA，若需要搜索引擎收录详情页，建议后续加预渲染或 SSR。
5. 前台页面为客户端渲染，首屏数据接口已合并（首页一次返回 config/banners/featured/latest/categories/stats），减少请求数。
6. 限流与 nonce 防重放都是**进程内存**实现（与图形验证码同理）：单实例足够，多副本部署前需换成 Redis；否则每个副本各算一份额度。
7. 授权与升级校验依赖环境变量中的密钥/公钥：密钥丢失可重新 `init` 并重新签发（公钥随之更换，旧授权码会失效），因此**私钥与 `UPGRADE_KEY` 请离线备份**。
8. 请求签名（`SIGN_MODE`）启用后，任何不签名的对接方（含自带脚本）都会被拒；对外提供 API 时建议单独开一条只读通道，而不是关闭签名。
9. 卡片与详情页的图样清晰度取决于导入图源的像素：现有 Excel 抽出的图样多为 150×150，卡片宽于 150px（桌面 4 列约 280px、平板 3 列约 210px）时会被放大。要更清晰需换更高分辨率的源图，或后续加一档 `<picture>`/多尺寸派生图。

---

> 计划书中的「待确认事项」（域名备案、公司资质、客服话术、Logo/VI）仍可在后台「网站配置」里随时替换，不影响系统运行。