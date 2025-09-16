# centralna_biciklana/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Instaliranje sistemskih zavisinosti
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Kopiranje requirements fajla
COPY requirements.txt .

# Instaliranje Python paketa
RUN pip install --no-cache-dir -r requirements.txt

# Kopiranje aplikacije
COPY . .

# Exposing port
EXPOSE 5000

# Komanda za pokretanje aplikacije
CMD ["python", "bike_shop_novi_sad_app.py"]