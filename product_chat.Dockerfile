# Dockerfile for streamlit_app
FROM python:3.11.9-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY src src

EXPOSE 8080

CMD ["streamlit", "run", "src/app/copilot.py", "--server.port", "8080", "--server.address", "0.0.0.0"]