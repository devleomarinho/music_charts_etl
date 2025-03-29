from datetime import datetime, timedelta
from airflow.decorators import dag
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup
from tasks.task_bronze_layer import process_landing
from tasks.task_silver_layer import bronze_to_silver
from tasks.task_gold_layer import silver_to_gold


default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

@dag(
    dag_id='main_dag',
    default_args=default_args,
    description='Main DAG calling different tasks',
    schedule_interval=timedelta(days=1),
    catchup=False
)


def main_dag():

    endpoint_url = "http://minio:9000"
    aws_access_key_id = "minioadmin"
    aws_secret_access_key = "minio@1234!"
    bucket_name = "landing"
 
    with TaskGroup("group_task_bronze", tooltip="Tasks processadas de scraping de álbuns para minio, salvando em .parquet") as group_task_bronze:
        PythonOperator(
            task_id='task_bronze',
            python_callable=process_landing
        )

    

    with TaskGroup("group_task_silver", tooltip="Tasks processadas de bronze para silver layer") as group_task_silver:
        PythonOperator(
            task_id='task_silver',
            python_callable=bronze_to_silver,
            op_args=[
                endpoint_url,
                aws_access_key_id, 
                aws_secret_access_key,
                bucket_name
            ]
        )

    with TaskGroup("group_task_gold", tooltip="Tasks processadas de silver para gold layer") as group_task_gold:
        PythonOperator(
            task_id='task_gold',
            python_callable=silver_to_gold,
            op_args=[
                endpoint_url,
                aws_access_key_id, 
                aws_secret_access_key,
                bucket_name
            ]
        )

    
    group_task_bronze >> group_task_silver >> group_task_gold

main_dag_instance = main_dag()