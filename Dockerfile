# Dockerfile
FROM python:3.11.8-slim-bookworm

# Устанавливаем системные зависимости,
# часто нужны для сборки некоторых Python-пакетов
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл с зависимостями
COPY requirements.txt .

# Устанавливаем Python-зависимости
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY ./catalog /catalog

# Устанавливаем рабочую директорию
WORKDIR /catalog
RUN python scripts.py
# Команда для запуска приложения
# Используем порт 80 внутри контейнера
ENTRYPOINT ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "80"]
