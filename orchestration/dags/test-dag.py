from airflow import DAG
from airflow.operators.bash import BashOperator
from sklearn.feature_extraction import DictVectorizer
from sklearn.metrics import root_mean_squared_error
from airflow.operators.python import get_current_context

from datetime import datetime
import pandas as pd
import os
import mlflow
import xgboost as xgb
import pickle
from airflow.decorators import task, dag

mlflow.set_tracking_uri("http://mlflow:5000")  # Docker内部地址
mlflow.set_experiment("nyc-taxi-experiment")
def read_dataframe(year: int, month: int) -> pd.DataFrame:
    url = f'https://d37ci6vzurychx.cloudfront.net/trip-data/green_tripdata_{year}-{month:02d}.parquet'

    df = pd.read_parquet(url)

    df['duration'] = df.lpep_dropoff_datetime - df.lpep_pickup_datetime
    df.duration = df.duration.apply(lambda td: td.total_seconds() / 60)

    df = df[(df.duration >= 1) & (df.duration <= 60)]

    categorical = ['PULocationID', 'DOLocationID']
    df[categorical] = df[categorical].astype(str)

    df['PU_DO'] = df['PULocationID'] + '_' + df['DOLocationID']

    return df

def create_X(df, dv=None):
    categorical = ['PU_DO']
    numerical = ['trip_distance']
    dicts = df[categorical + numerical].to_dict(orient='records')

    if dv is None:
        dv = DictVectorizer(sparse=True)
        X = dv.fit_transform(dicts)
    else:
        X = dv.transform(dicts)

    return X, dv

@dag(
    dag_id="newyork-taxi-predictor-dag",
    start_date=datetime(2023, 1, 1),
    catchup=False,
    schedule="@daily"
)
def taxi_pipeline():
    @task
    def read_data(**context):
        os.makedirs("tmp/data", exist_ok=True)
        os.makedirs("models", exist_ok=True)
        context = get_current_context()
    
        # 直接从上下文获取逻辑日期
        logical_date = context["logical_date"]
        year = logical_date.year
        month = logical_date.month
        train_df = read_dataframe(year, month)
        next_year = year + 1 if month == 12 else year
        next_month = 1 if month == 12 else month + 1
        val_df = read_dataframe(next_year, next_month)
        
        train_df_path = f'tmp/data/train_{year}_{month:02d}.parquet'
        val_df_path = f'tmp/data/val_{next_year}_{next_month:02d}.parquet'
        train_df.to_parquet(train_df_path, index=False)
        val_df.to_parquet(val_df_path, index=False)

        
        return train_df_path, val_df_path

    @task
    def feature_engineering(paths):   
        train_df_path, val_df_path = paths 
        train_df = pd.read_parquet(train_df_path)
        val_df = pd.read_parquet(val_df_path)

        X_train, dv = create_X(train_df)
        y_train = train_df['duration'].values
        
        X_val, _ = create_X(val_df, dv)
        y_val = val_df['duration'].values

        #dump them to temp file
        feature_path="tmp/features.pkl"
        with open(feature_path, "wb") as f:
                pickle.dump((X_train, y_train, X_val, y_val, dv), f)
        
        return feature_path
        
    @task
    def train_and_evaluate(feature_path):
        #get dfs
        with open(feature_path, "rb") as f:
            X_train, y_train, X_val, y_val, dv = pickle.load(f)
            
        with mlflow.start_run() as run:
            train = xgb.DMatrix(X_train, label=y_train)
            valid = xgb.DMatrix(X_val, label=y_val)

            best_params = {
                'learning_rate': 0.09585355369315604,
                'max_depth': 30,
                'min_child_weight': 1.060597050922164,
                'objective': 'reg:squarederror',
                'reg_alpha': 0.018060244040060163,
                'reg_lambda': 0.011658731377413597,
                'seed': 42
            }

            mlflow.log_params(best_params)

            booster = xgb.train(
                params=best_params,
                dtrain=train,
                num_boost_round=30,
                evals=[(valid, 'validation')],
                early_stopping_rounds=50
            )

            y_pred = booster.predict(valid)
            rmse = root_mean_squared_error(y_val, y_pred)
            mlflow.log_metric("rmse", rmse)

            with open("models/preprocessor.b", "wb") as f_out:
                pickle.dump(dv, f_out)
            mlflow.log_artifact("models/preprocessor.b", artifact_path="preprocessor")

            mlflow.xgboost.log_model(booster, artifact_path="models_mlflow")
            model_uri = f"runs:/{run.info.run_id}/models_mlflow"
            mlflow.register_model(model_uri, "nyc-taxi-model")

            run_id = run.info.run_id
            #make sure the returned type is string
            if not isinstance(run_id, str):
                run_id = str(run_id)

            return run_id
        
    cleanup_task = BashOperator(
        task_id="cleanup",
        bash_command="rm -rf tmp/*",
        trigger_rule="all_done"
        )

    paths = read_data()
    features = feature_engineering(paths)
    model_run = train_and_evaluate(features)
    model_run >> cleanup_task



dag = taxi_pipeline()

