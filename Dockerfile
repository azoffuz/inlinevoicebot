FROM python:3.11-slim

# Tizim paketlarini yangilash va FFmpeg o'rnatish
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Kutubxonalarni o'rnatish
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Loyiha fayllarini ko'chirish
COPY . .

# Render uchun port
ENV PORT=8080
EXPOSE 8080

# Botni ishga tushirish
CMD ["python", "main.py"]
