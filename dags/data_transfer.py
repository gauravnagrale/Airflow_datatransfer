from datetime import datetime, timedelta
import json
from pandas import json_normalize
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.operators.http_operator import SimpleHttpOperator
from airflow.sensors.http_sensor import HttpSensor 
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.operators.generic_transfer import GenericTransfer
 

#this is a default DAG when the DAG fails for some reason it automaatically re-tries for the 2 times as we mentioned and it retires after every 1min 
default_args = {
    'owner': 'Gaurav',
    'retries': 2,
    'retry_delay': timedelta(minutes=1)
}

with DAG(
    dag_id="Data_transfer",
    start_date=datetime(2023, 11, 22),
    default_args=default_args,
    description="Transfering the data from the source to destination DB",
    #schedule_interval='@daily',
    schedule_interval=timedelta(minutes=30),
    catchup=False
) as dag:
    #Creating the source table
    create_source_table = PostgresOperator(
        task_id="Create_source_man_table",
        postgres_conn_id='source_db_aiimsnew',
        sql='''
        CREATE TABLE IF NOT EXISTS airflow_source_users (
        uuid TEXT NOT NULL,
        title TEXT NOT NULL,
        firstname TEXT NOT NULL,
        lastname TEXT NOT NULL,
        gender TEXT NOT NULL,
        country TEXT NOT NULL,
        username TEXT NOT NULL,
        password TEXT NOT NULL,
        email TEXT NOT NULL,
        age INT NOT NULL
        )
        '''
    )

    create_destination_table = PostgresOperator(
        task_id="Create_dest_man_table",
        postgres_conn_id='dest_conn_id',
        sql='''
        CREATE TABLE IF NOT EXISTS airflow_destination_users (
        uuid TEXT NOT NULL,
        title TEXT NOT NULL,
        firstname TEXT NOT NULL,
        lastname TEXT NOT NULL,
        gender TEXT NOT NULL,
        country TEXT NOT NULL,
        username TEXT NOT NULL,
        password TEXT NOT NULL,
        email TEXT NOT NULL,
        age INT NOT NULL
        )
        '''
    )
    # Transfering the source data to the destination data: 
    # GenericTransfer task to upload data into the source table
    upload_data_to_destination = GenericTransfer(
        task_id='upload_man_data_to_destination',
        sql="SELECT * FROM airflow_source_users", #here i will not get the unique records
        destination_table="airflow_destination_users",
        source_conn_id="source_db_aiimsnew",
        destination_conn_id="dest_conn_id",
        #preoperator="TRUNCATE TABLE rand_users" ,#this ensures that # this line is for removing the data from the the destination table before pushing the new data
        dag=dag
    )

create_source_table>>create_destination_table