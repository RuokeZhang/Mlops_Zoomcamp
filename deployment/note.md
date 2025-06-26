## deployment ways
### Batch Offline
运行特征：定期执行（Run Regularly）. 

典型场景：按固定周期（如每日 / 每周）处理历史数据、生成离线报表、批量预测等，适合对实时性要求低但需全量数据计算的任务。
### Online
运行特征：持续运行（Up & Running All The Time）. 
1. Web Service（Web 服务）：提供实时接口，支持客户端通过HTTP直接调用模型或业务逻辑
2. Streaming（流处理）：处理实时数据流（如 Kafka / Flink 等），支持低延迟数据消费、实时计算（如订单实时监控、传感器数据实时分析）。

## Flask & Docker
[youtube video](https://www.youtube.com/watch?v=D7wfMAdgdF8&list=PL3MmuxUbc_hIUISrluw_A7wDSmfOhErJK&index=18])

### flask
Flask 自带的开发服务器（app.run()）是一个简单的 WSGI 服务器，但 仅用于开发环境。

生产中，需要使用**Gunicorn**运行 Flask 应用。

```shell
gunicorn --bind=0.0.0.0:9696 predict:app
```
去 predict.py 模块里找 app 这个 Flask 应用实例，然后用 Gunicorn 把它跑起来对外提供服务 。
### Creating a virtual environment with Pipenv
```bash
pipenv install scikit-learn==1.7.0 flask --python=3.12
、
pipenv shell #进入环境
```
why use pipenv?  
>不同版本的机器学习库可能存在 API 变化或算法实现差异, 比如我的LinearRegression是用skleaern 1.0.2训练出来的，那么我再加载它的时候，也需要用sklearn用它进行predict

### docker
```dockerfile
RUN pip install pipenv

WORKDIR /app
COPY [ "Pipfile", "Pipfile.lock", "./" ]
```
copy pipfile and the lock from the host machine to the container's current working directory(/app)

```dockerfile
ENTRYPOINT ["gunicorn", "--bind=0.0.0.0:9696", "predict:app"]
```
EXTRYPOINT specifies the command to run when the container starts

BUILD and RUN the container:
```
docker build -t ride-duration-prediction-service:v1 .
docker run -it --rm -p 9696:9696 ride-duration-prediction-service:v1
```