FROM apache/airflow:3.0.1
ADD requirements.txt .
RUN pip install apache-airflow -r requirements.txt