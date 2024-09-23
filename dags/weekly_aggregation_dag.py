from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 9, 10),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'weekly_aggregation',
    default_args=default_args,
    description='Run weekly aggregation for user actions',
    schedule_interval='0 7 * * *',
)

aggregate_task = BashOperator(
    task_id='run_aggregation',
    bash_command='python /path/to/script.py {{ ds }}',
    dag=dag,
)

aggregate_task
