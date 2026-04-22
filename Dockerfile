FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md openenv.yaml ./
COPY blackstart_city ./blackstart_city
COPY server ./server
COPY inference.py client.py models.py ./

RUN pip install --no-cache-dir -e .

ENV PYTHONUNBUFFERED=1
ENV ENABLE_WEB_INTERFACE=true

CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
