FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    pandas \
    requests \
    matplotlib \
    reportlab

RUN mkdir -p /app/data

COPY script.py /app/script.py

CMD ["python", "script.py"]
