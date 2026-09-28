# syntax=docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /app

# Системные зависимости для asyncpg + CA для opensource.tbank.ru
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Russian Trusted CA (Минцифры): нужен для pip (opensource.tbank.ru / t-tech-investments)
# и runtime gRPC. Включаем Sub CA + Sub CA RSA2024 (актуальный intermediate T-Bank).
COPY backend/certs/russian_trusted_root_ca.pem \
     backend/certs/russian_trusted_sub_ca.pem \
     backend/certs/russian_trusted_sub_ca_rsa2024.pem \
     /usr/local/share/ca-certificates/tbank/
RUN cat /etc/ssl/certs/ca-certificates.crt \
        /usr/local/share/ca-certificates/tbank/russian_trusted_root_ca.pem \
        /usr/local/share/ca-certificates/tbank/russian_trusted_sub_ca.pem \
        /usr/local/share/ca-certificates/tbank/russian_trusted_sub_ca_rsa2024.pem \
        > /etc/ssl/certs/ca-certificates-with-russian.crt
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates-with-russian.crt \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates-with-russian.crt \
    CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates-with-russian.crt

# Копируем зависимости
COPY backend/requirements.txt .

# Устанавливаем зависимости (BuildKit cache для pip ускоряет пересборки)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt gunicorn

# Копируем код приложения и SQL для init_db
COPY backend/ .
COPY database/ /app/database/

# Порт приложения
EXPOSE 5000

# Запуск: Gunicorn + Uvicorn workers для production
CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:5000"]
