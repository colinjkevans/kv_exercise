FROM python:3

WORKDIR /opt/kv-service

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

CMD gunicorn --bind 0.0.0.0:8080 'main:create_app(backend_type="in_memory")'