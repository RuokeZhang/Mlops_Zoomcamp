import os
import json
import boto3
import base64

import mlflow

kinesis_client = boto3.client('kinesis')

os.environ["AWS_PROFILE"] = "dev" # fill in with your AWS profile. More info: https://docs.aws.amazon.com/sdk-for-java/latest/developer-guide/setup.html#setup-credentials

TRACKING_SERVER_HOST = "3.87.201.140" # fill in with the public DNS of the EC2 instance
mlflow.set_tracking_uri(f"http://{TRACKING_SERVER_HOST}:5000")


PREDICTIONS_STREAM_NAME = os.getenv('PREDICTIONS_STREAM_NAME', 'ride_predictions')


RUN_ID = os.getenv('RUN_ID')

logged_model = f's3://mlflow-artifacts-remote-ruoke/2/models/m-417f292db2fe475d973e59f14411fea1/artifacts'

model = mlflow.pyfunc.load_model(logged_model)
print(model)
#dv_model=mlflow.sklearn.load_model(dv_model_path)




TEST_RUN = os.getenv('TEST_RUN', 'False') == 'True'

def prepare_features(ride):
    features = {}
    features['PU_DO'] = '%s_%s' % (ride['PULocationID'], ride['DOLocationID'])
    features['trip_distance'] = ride['trip_distance']
    #features= dv_model.transform([features])
    return features


def predict(features):
    pred = model.predict(features)
    return float(pred[0])


def lambda_handler(event, context):
    # print(json.dumps(event))
    
    predictions_events = []
    
    for record in event['Records']:
        encoded_data = record['kinesis']['data']
        decoded_data = base64.b64decode(encoded_data).decode('utf-8')
        ride_event = json.loads(decoded_data)

        # print(ride_event)
        ride = ride_event['ride']
        ride_id = ride_event['ride_id']
    
        features = prepare_features(ride)
        prediction = predict(features)
    
        prediction_event = {
            'model': 'ride_duration_prediction_model',
            'version': '123',
            'prediction': {
                'ride_duration': prediction,
                'ride_id': ride_id   
            }
        }

        if not TEST_RUN:
            kinesis_client.put_record(
                StreamName=PREDICTIONS_STREAM_NAME,
                Data=json.dumps(prediction_event),
                PartitionKey=str(ride_id)
            )
        
        predictions_events.append(prediction_event)


    return {
        'predictions': predictions_events
    }