FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    vlc \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as an unprivileged user (data lives in /home/audook/.audook, see docker-compose.yml)
RUN useradd --create-home --uid 1000 audook \
    && mkdir -p /home/audook/.audook \
    && chown -R audook:audook /home/audook /app
USER audook
ENV HOME=/home/audook

ENV AUDOOK_HEADLESS=1

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=3)" || exit 1

CMD ["python", "audook_backend.py"]
