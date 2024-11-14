# Dockerfile for python_service  
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY src src
COPY processed_data processed_data
COPY .env.template .env

EXPOSE 8080

CMD ["uvicorn", "src.api.agent_service:app", "--host", "0.0.0.0", "--port", "8000"]