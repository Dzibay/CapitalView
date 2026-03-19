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

# Яндекс.Метрика counter id — нужен на build-time для подстановки в index.html и для кода SPA
ARG VITE_YM_COUNTER_ID=108158122
ENV VITE_YM_COUNTER_ID=$VITE_YM_COUNTER_ID

# Яндекс.Вебмастер verification id — подставляется в meta-тег в index.html на build-time
ARG VITE_YANDEX_VERIFICATION_ID=84cad37df98909ab
ENV VITE_YANDEX_VERIFICATION_ID=$VITE_YANDEX_VERIFICATION_ID

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
