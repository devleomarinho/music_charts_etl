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
from airflow.providers.mysql.hooks.mysql import MySqlHook
from sqlalchemy import create_engine, MetaData, Table, Column, inspect
from sqlalchemy.dialects.mysql import VARCHAR, INTEGER, FLOAT

def scrape_albums():
    warnings.filterwarnings("ignore", message="Unverified HTTPS request")
    
    years = range(1950, 2024)
    base_url_zeros = "https://tsort.info/music/da{}.htm"
    base_url_others = "https://tsort.info/music/ay{}.htm"
    
    all_data = []

    def extract_data_from_table(soup):
        rows = soup.select('table.albumlist tr')[1:]
        data = []
        
        for row in rows:
            pos = row.find("td", class_="pos").text.strip()
            artist = row.find("td", class_="aat").text.strip()
            album = row.find("td", class_="att").text.strip()
            year = row.find("td", class_="ayr").text.strip()
            chart_entries = row.find("td", class_="ach").text.strip()
            
            data.append({
                "Posição": pos,
                "Artista": artist,
                "Álbum": album,
                "Ano": year,
                "Entradas nas Paradas": chart_entries
            })
        
        return data

    for year in years:
        if year % 10 == 0:
            url = base_url_zeros.format(year)
        else:
            url = base_url_others.format(year)

        try:
            response = requests.get(url, verify=False)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                data = extract_data_from_table(soup)
                all_data.extend(data)
            else:
                print(f"Erro ao acessar a página do ano {year}")
        except requests.exceptions.SSLError as e:
            print(f"Erro SSL ao acessar {url}: {e}")

    df = pd.DataFrame(all_data)
    return df

def upload_to_minio(df):
    endpoint_url = "http://minio:9000"
    aws_access_key_id = "minioadmin"
    aws_secret_access_key = "minio@1234!"
    bucket_name = "landing"
    object_name = f"bronze_albums_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet"

   
    table = pa.Table.from_pandas(df)
    buf = io.BytesIO()
    pq.write_table(table, buf)
    buf.seek(0)

    config = Config(
        signature_version='s3v4',
        s3={'addressing_style': 'path'},
        retries={'max_attempts': 3}
    )

    s3_client = boto3.client(
        's3',
        endpoint_url=endpoint_url,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        verify=False,
        config=config
    )

    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=object_name,
            Body=buf.getvalue()
        )
        print(f"Arquivo enviado para {bucket_name}/{object_name} com sucesso!")
        return object_name
    except NoCredentialsError:
        print("Credenciais não encontradas")
        raise
    except Exception as e:
        print(f"Erro detalhado ao enviar arquivo: {str(e)}")
        raise


def upload_to_mariadb(df):
    
    df.columns = [col.replace(' ', '_').replace('á', 'a').replace('ã', 'a') for col in df.columns]
    
    print("Colunas normalizadas:")
    print(df.columns)
    
    mysql_hook = MySqlHook(mysql_conn_id='mariadb_local')
    connection = mysql_hook.get_conn()
    table_name = "albums_bronze"

    try:
        with connection.cursor() as cursor:
            
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
    {', '.join([f"`{col}` TEXT" if col == 'Entradas_nas_Paradas' else f"`{col}` VARCHAR(255)" for col in df.columns])}
)
            """
            print("\nSQL para criar tabela:")
            print(create_table_sql)
            
            cursor.execute(create_table_sql)
            print(f"\nTabela {table_name} verificada/criada no MariaDB")

            
            for index, row in df.iterrows():
                values = [str(val) if val is not None else '' for val in row]
                
                insert_sql = f"""
                INSERT INTO {table_name} ({', '.join([f"`{col}`" for col in df.columns])})
                VALUES ({', '.join(['%s'] * len(df.columns))})
                """
                cursor.execute(insert_sql, values)

            connection.commit()
            print(f"Dados inseridos na tabela {table_name} no MariaDB")
            return table_name

    except Exception as e:
        print(f"Erro ao enviar arquivo para MariaDB: {str(e)}")
        print("\nDetalhes do erro:")
        print(f"Tipo do erro: {type(e)}")
        raise

    finally:
        if connection:
            connection.close()

            
def process_landing():
    try:

        df = scrape_albums()
        minio_filename = upload_to_minio(df)
        mariadb_table = upload_to_mariadb(df)

        return {
            "minio_filename": minio_filename,
            "mariadb_table": mariadb_table
        }
    
    except Exception as e:
        print(f"Erro ao processar landing: {str(e)}")
        raise