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


def _process_user(ti):
    user_data = ti.xcom_pull(task_ids="extract_user")  # Extract the data using xcom_pull() function
    user = user_data['results'][0]
    
    processed_user = json_normalize({
        'gender': user['gender'],
        'title': user['name']['title'],
        'firstname': user['name']['first'],
        'lastname': user['name']['last'],
        'country': user['location']['country'], 
        'username': user['login']['username'],
        'password': user['login']['password'],
        'email': user['email'],
        'age': user['dob']['age']
    })
    
    processed_user.to_csv('/tmp/processed_user.csv', index=None, header=False)



#is this function we have defined where we have stored user details
def _store_user():
    #postgres hook is used to communicate with the external data source 
    hook = PostgresHook(postgres_conn_id='postgres')

    hook.copy_expert(
        sql="COPY rand_users FROM stdin WITH DELIMITER as ','",
        filename='/tmp/processed_user.csv'
    ) 

#this is a default DAG when the DAG fails for some reason it automaatically re-tries for the 2 times as we mentioned and it retires after every 1min 
default_args = {
    'owner': 'Gaurav',
    'retries': 2,
    'retry_delay': timedelta(minutes=1)
}

with DAG(
    dag_id="rand_user",
    start_date=datetime(2023, 10, 15),
    default_args=default_args,
    description="Creating the table for the user",
    schedule_interval='@daily',
    catchup=False
) as dag:
    #Creating the table
    create_table = PostgresOperator(
        task_id="Create_table",
        postgres_conn_id='postgres',
        sql='''
        CREATE TABLE IF NOT EXISTS rand_users (
        gender TEXT NOT NULL,
        title TEXT NOT NULL,
        firstname TEXT NOT NULL,
        lastname TEXT NOT NULL,
        country TEXT NOT NULL,
        username TEXT NOT NULL,
        password TEXT NOT NULL,
        email TEXT NOT NULL,
        age TEXT NOT NULL
        )
        '''
    )

    create_dest_table = PostgresOperator(
        task_id = "destinatin_table",
        postgres_conn_id = "Destination_table",
        sql = '''
        CREATE TABLE IF NOT EXISTS rand_dest_users (
        gender TEXT NOT NULL,
        title TEXT NOT NULL,
        firstname TEXT NOT NULL,
        lastname TEXT NOT NULL,
        country TEXT NOT NULL,
        username TEXT NOT NULL,
        password TEXT NOT NULL,
        email TEXT NOT NULL,
        age TEXT NOT NULL)
        '''
    )

    #Creating our first sensor
    #here we are checking if the api available
    is_api_available = HttpSensor(#This is the name of a AIRFLOW task
        task_id='is_api_available',#This is the unique identifier for the task within the context of an Airflow DAG. In this case, it's named 'is_api_available'.
        http_conn_id='rand_user',  # Replace with your actual HTTP connection ID
        endpoint='api/'
        # Endpoint URLs are essential for making requests to web services or APIs. 
        # When you make an HTTP request to an endpoint URL, you are specifying which resource or service you want to interact with.
    )

    #is this is the sensor which will extract the data from the api that we have mentioned 
    extract_user = SimpleHttpOperator(
        task_id='extract_user',
        http_conn_id='rand_user',
        endpoint='api/',
        method='GET',
        response_filter=lambda response: json.loads(response.text),
        log_response=True
    )

    #we are going to process the user 
    process_user = PythonOperator(
        task_id='process_user',
        python_callable=_process_user
    )

    store_user = PythonOperator(
        task_id='store_user',
        python_callable=_store_user
    )

    upload_data = GenericTransfer(
                        task_id='load_upload_data' ,
                        sql="select * from rand_users",
                        destination_table ="rand_dest_users"  ,
                        source_conn_id="postgres"  ,
                        destination_conn_id="Destination_table" ,
                        #preoperator="TRUNCATE TABLE rand_dest_users" ,#this ensures that 
                        dag=dag

                    )

create_table>>is_api_available>>extract_user>>process_user>>store_user>>create_dest_table>>upload_data