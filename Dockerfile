FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# ✅ ELIMINAMOS la línea problemática
# Las carpetas se crean automáticamente

EXPOSE 8080

CMD ["python", "app.py"]
