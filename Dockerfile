FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# ✅ SOLUCIÓN: Usar mkdir -p (ya lo tienes) pero con bandera -p
# ✅ CORRECCIÓN: Asegurar que no falle si existe
RUN mkdir -p data databases || true

EXPOSE 8080

CMD ["python", "app.py"]
