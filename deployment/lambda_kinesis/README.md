https://www.youtube.com/watch?v=TCqr9HNcrsI&list=PL3MmuxUbc_hIUISrluw_A7wDSmfOhErJK

## IAM
https://596387592324.signin.aws.amazon.com/console

username: ruoke_IAM.  
password: the cat

## Role
在使用lambda时，由于这个服务需要访问到别的服务,所以我们需要给lambda一些权限，因此给他设置一个role。  
官方定义的role的描述如下：
Allows Lambda functions to call AWS services on your behalf.

## Lambda

```python
def lambda_handler(event, context):
    
    print(json.dumps(event))
    prediction=10.0
    
    return {
        'ride_duration':prediction
    }
```
lambda可以接收json,运行逻辑，返回json
## kinesis
在terminal配置好access key,然后运行这个，发送一条数据
```shell
KINESIS_STREAM_INPUT=ride-events
aws kinesis put-record \
    --stream-name ${KINESIS_STREAM_INPUT} \
    --partition-key 1 \
    --data "Hello, this is a test."
```
kinesis会给我返回这个.   


```shell
{
    "ShardId": "shardId-000000000000",
    "SequenceNumber": "49664789992496579505708561839081281359433102459270070274"
}

```
Kinesis 数据流由多个分片组成，每个分片是一个有序的、不可变的数据序列。  
相同 PartitionKey 的记录会被写入同一个分片

sequenceNumber是Kinesis 为每条记录分配的唯一标识符，在同一个分片内，按写入顺序递增。

## lambda+kinesis
```json
{
    "Records": [
        {
            "kinesis": {
                "kinesisSchemaVersion": "1.0",
                "partitionKey": "1",
                "sequenceNumber": "49664789992496579505708561794343772478774127454792450050",
                "data": "Hellothisisatest",
                "approximateArrivalTimestamp": 1751437510.905
            },
            "eventSource": "aws:kinesis",
            "eventVersion": "1.0",
            "eventID": "shardId-000000000000:49664789992496579505708561794343772478774127454792450050",
            "eventName": "aws:kinesis:record",
            "invokeIdentityArn": "arn:aws:iam::596387592324:role/lambda-kinesis-role",
            "awsRegion": "us-east-1",
            "eventSourceARN": "arn:aws:kinesis:us-east-1:596387592324:stream/ride-events"
        }
    ]
}

```
给lambda加一个trigger，选择创建的kinesis流。可以发现kinesis发给lambda的event长这个样子

### 编码的情况
```shell
# 原始 JSON（注意：必须是单行）
json='{"ride":{"PULocationID":130,"DOLocationID":205,"trip_distance":3.66},"ride_id":136}'

# 生成 Base64（Linux/macOS 系统）
encoded=$(echo -n "$json" | base64)

# 执行命令
KINESIS_STREAM_INPUT=ride-events
aws kinesis put-record \
  --stream-name ${KINESIS_STREAM_INPUT} \
  --partition-key 1 \
  --data "$encoded"
```

对应的代码如下
```py
def lambda_handler(event, context):
    for record in event['Records']:
        encoded_data = record['kinesis']['data']
        decoded_data = base64.b64decode(encoded_data).decode('utf-8')
        ride_event = json.loads(decoded_data)
        print(ride_event)
```

### lambda读kinesis，并输出到kinesis
1. 首先要创建写kinesis的策略，然后把该策略赋予到lambda_kinesis角色
2. 这是lambda function中写kinesis流的代码
```python
kinesis_client.put_record(
    StreamName=PREDICTIONS_STREAM_NAME,
    Data=json.dumps(prediction_event),
    PartitionKey=str(ride_id)
)
```

3. 以下是读kinesis流的指令
```python
KINESIS_STREAM_OUTPUT='ride_predictions'
SHARD='shardId-000000000000'

SHARD_ITERATOR=$(aws kinesis \
    get-shard-iterator \
        --shard-id ${SHARD} \
        --shard-iterator-type TRIM_HORIZON \
        --stream-name ${KINESIS_STREAM_OUTPUT} \
        --query 'ShardIterator' \
)

RESULT=$(aws kinesis get-records --shard-iterator $SHARD_ITERATOR)

echo ${RESULT} | jq -r '.Records[0].Data' | base64 --decode
```
### sklearn：log/加载模型
见experiment_tracking/duration-prediction-s3.ipynb

```py
pipeline = Pipeline([
    ('dv', dv),
    ('model', lr)
])

mlflow.sklearn.log_model(pipeline, 'lr_dv_model')
```
此时就把dv和model一起log了，也被保存在S3中。

```py
logged_model = f's3://mlflow-artifacts-remote-ruoke/2/models/m-417f292db2fe475d973e59f14411fea1/artifacts'

model = mlflow.pyfunc.load_model(logged_model)

```
需要用到模型时，直接加载即可！

## Containerization
Lambda支持通过容器镜像部署，可以用官方提供的基础镜像：public.ecr.aws/lambda/python:3.9.2025.07.05.07  
见本目录的 Dockerfile。这个镜像里面有一个 lambda 的服务，主要内容是路由。也会将环境变量用来

dockerfile 里面指定：开始执行 lambda_handler 这个函数，
往 lambda 基础镜像这个 URL 发送请求：http://localhost:8080/2015-03-31/functions/function/invocations，lambda_handler就可以接收 event 并且开始处理

这个

```shell
docker build -t stream-model-duration:v1 .

docker run -it --rm \
    -p 8080:8080 \
    -e PREDICTIONS_STREAM_NAME="ride_predictions" \
    -e TEST_RUN="True" \
    -e AWS_DEFAULT_REGION="us-east-1" \
    -e AWS_ACCESS_KEY_ID="" \
    -e AWS_SECRET_ACCESS_KEY="" \
    stream-model-duration:v1
```

接着创建一个 ECR 容器
```shell
aws ecr create-repository --repository-name duration-model

# 我们需要给本地的 docker 一个凭证去访问 ECR
# 获取登录令牌（带Profile）
TOKEN=$(aws ecr get-login-password --region us-east-1 --profile mlops)
# 执行Docker登录（替换为你的ECR仓库地址）
docker login -u AWS -p $TOKEN https://596387592324.dkr.ecr.us-east-1.amazonaws.com

# push
REMOTE_URI="596387592324.dkr.ecr.us-east-1.amazonaws.com/duration-model"
REMOTE_TAG="v1"
REMOTE_IMAGE=${REMOTE_URI}:${REMOTE_TAG}

LOCAL_IMAGE="stream-model-duration:v1"
docker tag ${LOCAL_IMAGE} ${REMOTE_IMAGE}
docker push ${REMOTE_IMAGE}
```