from datetime import datetime
import requests
from bs4 import BeautifulSoup
import pandas as pd
import boto3
from botocore.exceptions import NoCredentialsError
from botocore.config import Config  
import io
import pyarrow as pa
import pyarrow.parquet as pq
import warnings
import logging
from airflow.providers.mysql.hooks.mysql import MySqlHook
from sqlalchemy import create_engine, MetaData, Table, Column, inspect
from sqlalchemy.dialects.mysql import VARCHAR, INTEGER, FLOAT




def bronze_to_silver(endpoint_url, aws_access_key_id, aws_secret_access_key, bucket_name):

    minio_client = boto3.client(
        's3',
        endpoint_url=endpoint_url,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key
    )

    try:

        objects  = minio_client.list_objects_v2(Bucket=bucket_name)
        
        if 'Contents' not in objects :
            raise Exception(f"Nenhum arquivo encontrado no bucket {bucket_name}")
            
       
        latest_file = max(objects['Contents'], key=lambda x: x['LastModified'])
        key = latest_file['Key']
        
        logging.info(f"Processando arquivo: {key}")

        response = minio_client.get_object(Bucket=bucket_name, Key=key)
        buffer = io.BytesIO(response['Body'].read())
        df = pd.read_parquet(buffer)

       
        df['Entradas nas Paradas'] = df['Entradas nas Paradas'].str.strip()
        
        entradas_split = df['Entradas nas Paradas'].str.split(',', expand=True)
        df_long = entradas_split.melt(ignore_index=False, value_name='Entrada_Parada').dropna()

      
        df_long.reset_index(inplace=True)

        df_normalizado = pd.merge(df[['Posição', 'Artista', 'Álbum', 'Ano']].reset_index(), df_long, on='index').drop(columns=['index'])
        
        df_normalizado = df_normalizado.drop_duplicates(subset=['Artista', 'Álbum', 'Ano', 'Entrada_Parada'])

        
        df_normalizado.drop(columns=['variable'], inplace=True)

        df_normalizado = df_normalizado.rename(columns={
            'Posição': 'Posicao',
            'Artista': 'Artista',
            'Álbum': 'Album',
            'Ano': 'Ano',
            'Entrada_Parada': 'Entrada_Parada'
            })

        df = df_normalizado

        output_buffer = io.BytesIO()
        df.to_parquet(output_buffer)
        
        silver_key = f"silver_{key}"

        minio_client.put_object(
            Bucket=bucket_name,
            Key=silver_key,
            Body=output_buffer.getvalue()
        )

        print(f"Arquivo transformado e salvo como {silver_key}")
        
        mysql_hook = MySqlHook(mysql_conn_id='mariadb_local')
        connection = mysql_hook.get_conn()
        table_name = "albums_silver"

        with connection.cursor() as cursor:
               
                create_columns = []
                for column in df.columns:
                   
                    if 'int' in str(df[column].dtype):
                        col_type = 'INT'
                    elif 'float' in str(df[column].dtype):
                        col_type = 'FLOAT'
                    else:
                        col_type = 'VARCHAR(255)'
                    
                    create_columns.append(f"{column} {col_type}")
                
                
                create_table_sql = f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    {', '.join(create_columns)}
                )
                """
                cursor.execute(create_table_sql)
                logging.info(f"Tabela {table_name} criada/verificada com sucesso.")

               
                placeholders = ', '.join(['%s'] * len(df.columns))
                columns = ', '.join(df.columns)
                
                
                insert_sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
                
                
                for _, row in df.iterrows():
                    cursor.execute(insert_sql, tuple(row))

                connection.commit()
                logging.info(f"Dados inseridos na tabela {table_name}.")

        print(f"Arquivo transformado e salvo como {silver_key} e na tabela {table_name} do MariaDB")
        return silver_key, table_name

    except Exception as e:
        print(f"Erro durante a transformação ou salvamento: {str(e)}")
        raise
  




    