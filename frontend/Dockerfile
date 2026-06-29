# 构建 React/Vite 前端
FROM public.ecr.aws/docker/library/node:22-alpine AS build

WORKDIR /app

COPY package*.json ./
ARG NPM_REGISTRY=
RUN if [ -n "$NPM_REGISTRY" ]; then \
      npm config set registry "$NPM_REGISTRY"; \
    fi && npm ci

COPY . .
RUN npm run build

# 使用 Nginx Alpine 镜像托管静态文件
FROM public.ecr.aws/docker/library/nginx:1.27-alpine

RUN rm /etc/nginx/conf.d/default.conf

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/ /usr/share/nginx/html/

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://127.0.0.1/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
