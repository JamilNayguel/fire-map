from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import requests
import pandas as pd
from pymongo import MongoClient
import os

# Configuración de la DAG de Airflow
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'etl_firms_data',
    default_args=default_args,
    description='ETL pipeline para datos de FIRMS',
    schedule_interval='@hourly',  # Se ejecutará cada hora
    start_date=datetime(2024, 11, 5),
    catchup=False,
) as dag:

    def extract_data():
        url = "https://firms.modaps.eosdis.nasa.gov/api/country/csv/f3b08242c742d92cac5e2a660c4e8eaf/MODIS_NRT/BOL/1"
        response = requests.get(url)
        response.raise_for_status()  # Lanzará un error si la solicitud no tiene éxito

        # Guardamos los datos en un DataFrame para manejarlos
        data = pd.read_csv(pd.compat.StringIO(response.text))
        data = data.to_dict(orient='records')
        return data

    def load_to_mongodb(data):
        # Conexión a MongoDB
        client = MongoClient('mongodb://mongo:27017/')
        db = client['etl_database']
        collection = db['firms_data']

        # Limpiamos la colección antes de insertar los nuevos datos
        collection.delete_many({})
        collection.insert_many(data)
        client.close()

    # Tarea de extracción
    extract_task = PythonOperator(
        task_id='extract_data',
        python_callable=extract_data
    )

    # Tarea de carga
    load_task = PythonOperator(
        task_id='load_to_mongodb',
        python_callable=load_to_mongodb,
        op_args=[extract_task.output]
    )

    extract_task >> load_task  # Definimos el orden de ejecución
