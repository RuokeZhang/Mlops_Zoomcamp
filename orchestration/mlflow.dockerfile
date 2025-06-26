FROM python:3.10-slim

RUN pip install mlflow==3.1.1 && \
    rm -rf /root/.cache/pip

EXPOSE 5000

CMD [ \
    "mlflow", "server", \
    "--backend-store-uri", "sqlite:///home/mlflow_data/mlflow.db", \
    "--host", "0.0.0.0", \
    "--port", "5000" \
]