# QNAP Container Station 创建失败处理

如果看到类似错误：

```text
unable to prepare context: path "/share/CACHEDEV1_DATA/.qpkg/container-station/data/application/docker-compose/backend" not found
```

原因是 Container Station 会把 `docker-compose.yml` 复制到自己的应用目录执行，导致相对路径 `./backend`、`./frontend` 指向错误位置。

本项目的 `docker-compose.yml` 已改为使用 `PROJECT_DIR`：

```text
PROJECT_DIR=/share/CACHEDEV1_DATA/Web/wc2026
```

请确认 NAS 上这个目录里存在：

```text
backend/
frontend/
docker-compose.yml
.env
```

推荐流程：

1. 把 `wc2026-nas-docker.zip` 上传到 `/share/CACHEDEV1_DATA/Web/wc2026`。
2. 解压后确认不是多套了一层目录。
3. 复制 `.env.nas.example` 为 `.env`。
4. 确认 `.env` 里 `PROJECT_DIR=/share/CACHEDEV1_DATA/Web/wc2026`。
5. 再用 Container Station 创建应用。

如果之后仍提示 Docker Hub timeout：

```text
Get "https://registry-1.docker.io/v2/": i/o timeout
```

那是 NAS 访问 Docker Hub 超时。需要在 QNAP/Docker 设置 registry mirror，或先在能联网的机器上 build/pull 镜像后再导入 NAS。
