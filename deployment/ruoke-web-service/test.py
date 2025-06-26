import predict
import requests
ride={
    "PULocationID": 10,
    "DOLocationID": 20,
    "trip_distance": 35
}
response=requests.post('http://localhost:9696/predict', json=ride)
print(response.json())

