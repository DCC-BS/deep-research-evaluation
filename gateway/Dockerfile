FROM python:3.15-slim
RUN pip install --no-cache-dir fastapi==0.118.0 "uvicorn[standard]==0.37.0" httpx==0.28.1 pyyaml==6.0.3
WORKDIR /app
COPY app.py .
# Runs as root: Docker Desktop maps bind-mount ownership, so a fixed UID cannot write ./logs.
EXPOSE 4000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "4000"]
