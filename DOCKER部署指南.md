# WC2026 世界杯预测网站 - QNAP NAS Docker 部署指南

## 访问端口

你的 QNAP 管理入口是 `http://bmhlfc.top:8088/`，这个端口通常已经被 QNAP 管理界面占用，不建议再给网站容器使用。

默认部署后访问：

```text
http://bmhlfc.top:2026/
```

如果你确实想换端口，可以在部署时设置 `APP_PORT`，例如 `APP_PORT=12306`。

注意：如果 `http://bmhlfc.top:12306/` 已经由 QNAP Web Station 或其他服务占用，Docker 绑定 `12306:80` 时会报 `port is already allocated`。当前建议用 `2026` 作为 Docker 入口，避开这个占用。

如果部署后 `http://bmhlfc.top:2026/` 外网打不开，请在路由器端口转发和 QNAP 防火墙里放行 `2026`。

## 方式一：用脚本上传并启动

前提：你的 NAS 已启用 SSH，电脑上可用 `ssh`、`scp`、`tar`。

在项目根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\deploy-nas.ps1 -NasHost bmhlfc.top -NasUser admin -AppPort 2026
```

脚本会做这些事：

1. 打包当前项目，排除 `node_modules`、`venv`、本地日志和本地 SQLite 文件。
2. 上传到 NAS 的 `/tmp/wc2026-nas-docker.tar.gz`。
3. 解压到 `/share/CACHEDEV1_DATA/Web/wc2026`。
4. 在 NAS 上执行 `APP_PORT=2026 docker compose up -d --build`。

密码不要写进项目文件，按 SSH 提示在终端输入即可。

如果出现 `connect to host bmhlfc.top port 22: Connection timed out`，说明当前电脑连不到 NAS 的 SSH 端口。请检查：

1. QNAP 控制台是否启用了 SSH 服务。
2. QNAP 防火墙是否允许 22 端口。
3. 路由器是否把外网 22 转发到 NAS。
4. 如果电脑和 NAS 在同一个局域网，优先把 `-NasHost bmhlfc.top` 换成 NAS 的局域网 IP。
5. 如果 SSH 不是 22 端口，用 `-NasSshPort` 指定，例如 `-NasSshPort 2222`。

## 方式二：手动上传后 Docker Compose

如果 SSH 连不上，可以用 QNAP 网页管理界面上传：

1. 打开 `http://bmhlfc.top:8088/`。
2. 进入 File Station。
3. 上传 `wc2026-nas-docker.zip` 到 `/share/CACHEDEV1_DATA/Web/wc2026` 或 Web 目录下的新文件夹。
4. 在 File Station 里解压这个 zip。
5. 打开 Container Station，用解压目录里的 `docker-compose.yml` 创建应用，或在 NAS 终端里执行下面命令。

1. 在 NAS 上创建目录：

```bash
mkdir -p /share/CACHEDEV1_DATA/Web/wc2026
```

2. 把项目上传到这个目录，至少包含：

```text
backend/
frontend/
docker-compose.yml
.env.nas.example
```

3. 在 NAS 终端执行：

```bash
cd /share/CACHEDEV1_DATA/Web/wc2026
cp .env.nas.example .env
docker compose up -d --build
```

4. 打开：

```text
http://bmhlfc.top:2026/
```

## Compose 说明

当前 `docker-compose.yml` 包含两个服务：

- `wc2026-frontend`：Nginx 托管前端页面，并把 `/api` 反向代理到后端。
- `wc2026-backend`：FastAPI 后端，容器内端口 `8000`，不直接暴露到公网。

后端 SQLite 数据文件放在 Docker volume：

```text
wc2026-backend-data:/app/data
```

所以重建容器不会丢数据。

## 实时数据同步

后端已内置比赛实时数据同步任务，默认每 60 秒读取一次：

```text
/app/data/matches.live.json
```

这个文件可以由 NAS 定时脚本、人工维护，或后续接入的官方/供应商接口写入。示例结构在：

```text
backend/data/matches.live.example.json
```

部署到 NAS 后，如果要让已完赛比赛自动进入首页、赛程、数据统计和比赛详情页，请把真实赛果写入 Docker volume 对应的 `/app/data/matches.live.json`。不要把模型预测比分写入该文件；只有官方赛果、进球、首发、观众人数和技术统计应写入实时 feed。

可在 `.env` 调整同步频率：

```text
LIVE_SYNC_ENABLED=true
LIVE_SYNC_INTERVAL_SECONDS=60
```

未配置 `matches.live.json` 时，系统会把已过预计完场时间但没有赛果的比赛标记为“等待官方赛果”，不会拿预测比分计算积分榜。

## 常用命令

```bash
docker compose ps
docker compose logs -f
docker compose logs -f frontend
docker compose logs -f backend
docker compose restart
docker compose down
docker compose up -d --build
```

## 更新网站

把新代码上传到同一个 NAS 目录后执行：

```bash
cd /share/CACHEDEV1_DATA/Web/wc2026
docker compose up -d --build
```

## 常见问题

如果 `2026` 端口被占用，修改 `.env`：

```text
APP_PORT=2027
```

然后执行：

```bash
docker compose up -d
```

如果页面能打开但预测接口失败，查看后端日志：

```bash
docker compose logs -f backend
```

如果 `/predict`、`/stats` 刷新后 404，说明 Nginx 配置没有正确加载，确认 `frontend/nginx.conf` 已在镜像构建上下文中。
