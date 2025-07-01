
## training
使用文件：experiment_tracking/duration-prediction.ipynb

see the MLflow UI: ```mlflow server --backend-store-uri sqlite:///mlflow.db --port 5000```

在代码里log model之后，model会存在mlruns/1/models中

## register model
使用文件：experiment_tracking/manipulate.ipynb


可以在UI里面register，也可以在代码里register
```python
run_id='f5b4bd2300ec4943955d253603ec3e29'
model_uri = f"runs:/{run_id}/models_mlflow"
#register model
mlflow.register_model(model_uri=model_uri, name="nyc-taxi-xgboost")
```

## run on AWS
使用文件：experiment_tracking/scenario-3.ipynb

https://www.youtube.com/watch?v=1ykg4YmbFVA&list=PL3MmuxUbc_hIUISrluw_A7wDSmfOhErJK&index=13

### EC2
1. create an instance
2. it will automatically create a security group, we need to add TCP rule for the inbound rule! (specify port=5000) 
3. security group **rule** id: sgr-0eee750b0df01148e
4. security group id: sg-0d9c8fd7d057ed4ff
5. ```pip install mlflow boto3 psycopg2-binary```
6. 可以看到同一VPC的其它资源
```shell
[ec2-user@ip-172-31-84-225 ~]$ aws s3 ls
2025-07-01 07:22:08 mlflow-artifacts-remote-ruoke
```

### RDS
1. 允许来自 EC2 所在安全组（sg-0d9c8fd7d057ed4ff）的流量访问 5432 端口（PostgreSQL 默认端口）
2. RDS与EC2属于同一VPC
3. postgresql的安全组：sg-06d091ccf0102a36d
4. 用户名postgres, 密码bNugbMpSpmy086EIg7Zm
5. 数据库标识符：mlflow-database

```shell
#进入EC2
ssh -i "mlflow-ec2-pair.pem" ec2-user@ec2-13-219-80-155.compute-1.amazonaws.com
#在EC2启动mlflow server
mlflow server -h 0.0.0.0 -p 5000 --backend-store-uri postgresql://postgres:bNugbMpSpmy086EIg7Zm@mlflow-database.ca5csqkw4lt9.us-east-1.rds.amazonaws.com:5432/mlflow_db --default-artifact-root s3://mlflow-artifacts-remote-ruoke
```

![s3](./image/image.png)