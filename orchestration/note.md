
## Docker

1. 获取最新版本的Airflow Docker Compose文件
```bash
curl -LfO 'https://airflow.apache.org/docs/apache-airflow/3.0.0/docker-compose.yaml'
```
2. 添加MLflow服务到`docker-compose.yaml`中（从mlflow.dockerfile构建）：
```yaml
  mlflow:
    build:
      context: .
      dockerfile: mlflow.dockerfile
    ports:
      - "5000:5000"
    environment:
      MLFLOW_TRACKING_URI: http://mlflow:5000
    networks:
      - airflow-network
```
3. 安装Python库：
   - 创建`airflow.dockerfile`：
   ```Dockerfile
   FROM apache/airflow:3.0.0
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   ```
   - 修改`docker-compose.yaml`，使Airflow服务基于自定义Dockerfile构建：
   ```yaml
   services:
     airflow-webserver:
       build:
         context: .
         dockerfile: airflow.dockerfile
       ...
   ```
   - 在`requirements.txt`中列出所有需要的库，例如：
   ```
   mlflow
   scikit-learn
   xgboost
   pandas
   pyarrow
   ```
4. 启动容器：
```bash
docker compose up
```

5. 进入容器检查网络
```bash
docker exec -it 10abc6933fd0 sh
curl -v https://d37ci6vzurychx.cloudfront.net/trip-data/green_tripdata_2025-01.parquet
```
## Airflow 3.0 基础
1. 定义DAG（使用TaskFlow API）：
```python
from airflow.decorators import dag, task
from datetime import datetime
@dag(
    dag_id='etl_workflow',
    start_date=datetime(2023, 1, 1),
    schedule_interval='@daily',
    default_args={
        'owner': 'jdoe',
        'retries': 1
    },
    catchup=False
)
def etl_pipeline():
    @task
    def extract():
        # 使用TaskFlow API获取上下文
        from airflow.operators.python import get_current_context
        context = get_current_context()
        execution_date = context['logical_date']  # 在Airflow 2.2+中，使用logical_date代替execution_date
        year = execution_date.year
        month = execution_date.month
        # 从URL读取数据
        url = f'https://d37ci6vzurychx.cloudfront.net/trip-data/green_tripdata_{year}-{month:02d}.parquet'
        df = pd.read_parquet(url)
        # ... 数据处理 ...
        return processed_data_path
    @task
    def transform(data_path):
        # 读取数据并进行特征工程
        ...
        return transformed_data_path
    @task
    def load(transformed_data_path):
        # 加载数据
        ...
    # 定义任务依赖
    data = extract()
    transformed_data = transform(data)
    load(transformed_data)
# 生成DAG
etl_dag = etl_pipeline()
```
2. 测试单个任务（在Docker容器中执行）：
```bash
docker exec -it orchestration-airflow-worker-1 airflow tasks test etl_workflow extract 2025-06-25
```
3. 列出所有DAG：
```bash
docker exec -it orchestration-airflow-webserver-1 airflow dags list
```
4. 调度器会自动启动（在docker-compose中已经包含了scheduler服务）。
## MLflow 设置
在Airflow任务中设置MLflow跟踪URI（使用Docker服务名）：
```python
mlflow.set_tracking_uri("http://mlflow:5000")  # Docker内部网络，使用服务名
```
## 工作流中的参数传递（TaskFlow API）
在TaskFlow API中，任务之间的参数传递通过函数参数和返回值自动处理（使用XCom）。同时，如果需要访问执行上下文（如执行时间），使用`get_current_context()`：
```python
@task
def read_data():
    from airflow.operators.python import get_current_context
    context = get_current_context()
    logical_date = context['logical_date']  # 执行日期
    year = logical_date.year
    month = logical_date.month
    # ... 处理数据 ...
    return data_path
@task
def process_data(data_path):
    # 直接使用上游任务返回的data_path
    ...
```