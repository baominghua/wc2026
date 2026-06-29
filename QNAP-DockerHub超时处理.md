# QNAP Docker Hub 超时处理

如果报错：

```text
failed to resolve source metadata for docker.io/library/python:3.13-slim
Get "https://registry-1.docker.io/v2/": i/o timeout
```

说明 NAS 访问 Docker Hub 超时。项目已把默认基础镜像改成 Amazon ECR Public 的 Docker Official Images 镜像：

```text
PYTHON_BASE_IMAGE=public.ecr.aws/docker/library/python:3.13-slim
NODE_BASE_IMAGE=public.ecr.aws/docker/library/node:22-alpine
NGINX_BASE_IMAGE=public.ecr.aws/docker/library/nginx:1.27-alpine
```

部署步骤：

1. 重新上传最新的 `wc2026-nas-docker.zip`。
2. 解压到 `/share/CACHEDEV1_DATA/Web/wc2026`。
3. 复制 `.env.nas.example` 为 `.env`。
4. 确认 `.env` 里有上面三个 `*_BASE_IMAGE`。
5. 重新创建 Container Station 应用。

如果 ECR Public 也超时，可以在 `.env` 里把这三个值改成你 NAS 可访问的私有镜像或镜像仓库地址。

构建依赖源也已支持配置：

```text
PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
NPM_REGISTRY=https://registry.npmmirror.com
```

这些只影响 Python/npm 包下载，不影响基础镜像下载。基础镜像下载失败时，优先处理 `*_BASE_IMAGE` 或 QNAP 的 registry mirror。
