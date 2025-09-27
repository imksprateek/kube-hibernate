FROM python:3.11-slim

WORKDIR /app

COPY wake_listener.py .

RUN pip install flask

CMD ["python", "wake_listener.py"]
