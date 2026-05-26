FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything first
COPY . .

# Verify fonts exist and are valid (must be >50KB)
RUN echo "=== Font check ==" && ls -lh /app/fonts/ && \
    python3 -c "
import os, sys
for f in ['Vazir.ttf','Vazir-Bold.ttf']:
    p = f'/app/fonts/{f}'
    size = os.path.getsize(p) if os.path.exists(p) else 0
    print(f'{f}: {size} bytes')
    if size < 50000:
        print(f'ERROR: {f} too small!')
        sys.exit(1)
print('Fonts OK')
"

CMD ["python", "main.py"]
