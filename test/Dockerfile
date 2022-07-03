FROM python:3

WORKDIR /opt/kv-store

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

CMD ["gunicorn", "--bind", "0.0.0.0:8081", "test_service:app"]