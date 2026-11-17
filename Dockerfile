# SidAgent API (backend only; serve frontend/ separately or via any static host)
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY sid_agent ./sid_agent
EXPOSE 8000
CMD ["uvicorn", "sid_agent.api:app", "--host", "0.0.0.0", "--port", "8000"]
