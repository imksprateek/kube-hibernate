FROM python:3.11-slim
WORKDIR /app
COPY controller.py .
RUN pip install kubernetes prometheus-api-client pytz
CMD ["python", "controller.py"]
