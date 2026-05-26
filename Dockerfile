FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download Vazir fonts directly into image
RUN mkdir -p /app/fonts && \
    curl -fL -o /app/fonts/Vazir.ttf \
      "https://cdn.jsdelivr.net/gh/rastikerdar/vazir-font@v30.1.0/dist/Vazir.ttf" && \
    curl -fL -o /app/fonts/Vazir-Bold.ttf \
      "https://cdn.jsdelivr.net/gh/rastikerdar/vazir-font@v30.1.0/dist/Vazir-Bold.ttf" && \
    ls -lh /app/fonts/

COPY . .

CMD ["python", "-m", "app.main"]
