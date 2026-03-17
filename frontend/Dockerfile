# Stage 1: сборка
FROM node:20-alpine AS builder

WORKDIR /app

# Копируем package files
COPY package.json package-lock.json* ./

# Устанавливаем зависимости
RUN npm ci

# Копируем исходники
COPY . .

# API URL — относительный путь, nginx проксирует /api на backend
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# Сборка с увеличенным лимитом памяти (2 ГБ)
RUN NODE_OPTIONS="--max-old-space-size=2048" npm run build

# Stage 2: nginx для раздачи статики
FROM nginx:alpine

# Копируем собранное приложение
COPY --from=builder /app/dist /usr/share/nginx/html

# Копируем конфиг nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
