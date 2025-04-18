from datetime import datetime
import requests
from bs4 import BeautifulSoup
import pandas as pd
import boto3
import io
import logging
import warnings
from airflow.providers.mysql.hooks.mysql import MySqlHook

def silver_to_gold(endpoint_url, aws_access_key_id, aws_secret_access_key, bucket_name):
    
    try:
        
        minio_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
        )

        
        objects = minio_client.list_objects_v2(Bucket=bucket_name, Prefix='silver_bronze_albums_')
        
        if 'Contents' not in objects:
            raise Exception(f"Nenhum arquivo encontrado no bucket {bucket_name}")
                
        
        latest_file = max(objects['Contents'], key=lambda x: x['LastModified'])
        key = latest_file['Key']
            
        logging.info(f"Processando arquivo: {key}")

        
        response = minio_client.get_object(Bucket=bucket_name, Key=key)
        buffer = io.BytesIO(response['Body'].read())
        df = pd.read_parquet(buffer)
        
        

        def create_dim_artist(df):
            
            artistas = df['Artista'].unique()
            
            dim_artista = pd.DataFrame({
                'nome_artista': artistas
            })
            
            # Adicionando ID como chave primária
            dim_artista['artista_id'] = range(1, len(dim_artista) + 1)
            
            # Reordenando colunas para ter o ID como primeira coluna
            dim_artista = dim_artista[['artista_id', 'nome_artista']]
            
            return dim_artista

        def create_dim_album(df, dim_artista):
            
            albums = df[['Album', 'Artista', 'Ano']].drop_duplicates()
            
            # Criando o DataFrame base
            dim_album = pd.DataFrame({
                'nome_album': albums['Album'],
                'artista': albums['Artista'],
                'ano_lancamento': albums['Ano']
            })
            
            # Gerando o album_id como chave primária
            dim_album['album_id'] = range(1, len(dim_album) + 1)
            
            # Adicionando referência para artista_id
            dim_album = pd.merge(
                dim_album, 
                dim_artista[['artista_id', 'nome_artista']], 
                left_on='artista', 
                right_on='nome_artista', 
                how='left'
            )
            
            # Removendo a coluna duplicada e reorganizando
            dim_album = dim_album.drop('nome_artista', axis=1)
            dim_album = dim_album[['album_id', 'nome_album', 'artista_id', 'artista', 'ano_lancamento']]
            
            return dim_album

        def create_dim_parada(df):
            
            paradas = df['Entrada_Parada'].unique()
            
            dim_parada = pd.DataFrame({
                'entrada_parada': paradas
            })
            
            # Adicionando ID como chave primária
            dim_parada['parada_id'] = range(1, len(dim_parada) + 1)
            
            # Reordenando para ter o ID como primeira coluna
            dim_parada = dim_parada[['parada_id', 'entrada_parada']]
            
            return dim_parada

        def create_fact_album_parada(df, dim_album, dim_parada):
            # Criando tabela fato que relaciona albuns com suas entradas nas paradas
            
            # Preparando os dados com as colunas originais relevantes
            fact_data = df[['Album', 'Artista', 'Entrada_Parada', 'Posicao']].copy()
            
            # Juntando com dim_album para obter album_id
            fact_data = pd.merge(
                fact_data,
                dim_album[['album_id', 'nome_album', 'artista']],
                left_on=['Album', 'Artista'],
                right_on=['nome_album', 'artista'],
                how='left'
            )
            
            # Juntando com dim_parada para obter parada_id
            fact_data = pd.merge(
                fact_data,
                dim_parada[['parada_id', 'entrada_parada']],
                left_on='Entrada_Parada',
                right_on='entrada_parada',
                how='left'
            )
            
            # Criando a tabela fato final
            fact_album_parada = pd.DataFrame({
                'album_id': fact_data['album_id'],
                'parada_id': fact_data['parada_id'],
                'posicao': fact_data['Posicao']
            })
            
            # Adicionando um ID único para a tabela fato
            fact_album_parada['fact_id'] = range(1, len(fact_album_parada) + 1)
            
            # Reordenando colunas
            fact_album_parada = fact_album_parada[['fact_id', 'album_id', 'parada_id', 'posicao']]
            
            return fact_album_parada

        def get_charts_data():
           
            warnings.filterwarnings("ignore", message="Unverified HTTPS request")
            
            url = "https://tsort.info/music/charta.htm"
            all_data = []

            def extract_data_from_table(soup):
                
                
                table = soup.find('table', class_='chartlist')
                if not table:
                    logging.error("Tabela 'chartlist' não encontrada na página.")
                    return []
                
                
                rows = table.find_all('tr')[1:]  
                data = []
                
                for row in rows:
                    
                    name = row.find("td", class_="nam")
                    period_covered = row.find("td", class_="sta")
                    max_pos = row.find("td", class_="max")
                    num_entries = row.find("td", class_="ent")
                    region = row.find("td", class_="reg")
                    type_ = row.find("td", class_="typ")
                    description = row.find("td", class_="des")
                    
                    
                    if not all([name, period_covered, max_pos, num_entries, region, type_, description]):
                        logging.warning(f"Linha incompleta encontrada: {row}")
                        continue  
                    
                    data.append({
                        "name": name.text.strip(),
                        "period_covered": period_covered.text.strip(),
                        "max_pos": max_pos.text.strip(),
                        "num_entries": num_entries.text.strip(),
                        "region": region.text.strip(),
                        "type": type_.text.strip(),
                        "description": description.text.strip()
                    })
                
                return data

            try:
                response = requests.get(url, verify=False)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    data = extract_data_from_table(soup)
                    all_data.extend(data)
                else:
                    logging.error(f"Erro ao acessar a página: {response.status_code}")
            except requests.exceptions.SSLError as e:
                logging.error(f"Erro SSL ao acessar {url}: {e}")
            except Exception as e:
                logging.error(f"Erro ao fazer web scraping: {e}")
                raise

            # Adicionando chart_id para tabela de paradas
            df_charts = pd.DataFrame(all_data)
            df_charts['chart_id'] = range(1, len(df_charts) + 1)
            
            # Reordenando para ter o ID como primeira coluna
            cols = ['chart_id'] + [col for col in df_charts.columns if col != 'chart_id']
            df_charts = df_charts[cols]
            
            return df_charts

        def save_to_minio(df, prefix, minio_client, bucket_name):
            
            output_buffer = io.BytesIO()
            df.to_parquet(output_buffer)
            gold_key = f"gold_{prefix}_{datetime.now().strftime('%Y%m%d%H%M%S')}.parquet"
            
            minio_client.put_object(
                Bucket=bucket_name,
                Key=gold_key,
                Body=output_buffer.getvalue()
            )
            
            logging.info(f"Arquivo {gold_key} salvo no MinIO.")

        def save_to_mariadb(df, table_name):
           
            mysql_hook = MySqlHook(mysql_conn_id='mariadb_local')
            connection = mysql_hook.get_conn()

            with connection.cursor() as cursor:
                # Verificar se a tabela existe e excluir para recriar com as novas estruturas
                cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                
                # Definir tipos de colunas
                create_columns = []
                for column in df.columns:
                    if column.endswith('_id'):
                        col_type = 'INT'
                    elif 'int' in str(df[column].dtype):
                        col_type = 'INT'
                    elif 'float' in str(df[column].dtype):
                        col_type = 'FLOAT'
                    else:
                        col_type = 'VARCHAR(255)'
                    
                    create_columns.append(f"{column} {col_type}")
                
                # Adicionar chave primária para tabelas dimensionais
                primary_key = ""
                if table_name == 'dim_artista':
                    primary_key = ", PRIMARY KEY (artista_id)"
                elif table_name == 'dim_album':
                    primary_key = ", PRIMARY KEY (album_id)"
                elif table_name == 'dim_parada':
                    primary_key = ", PRIMARY KEY (parada_id)"
                elif table_name == 'charts_data':
                    primary_key = ", PRIMARY KEY (chart_id)"
                elif table_name == 'fact_album_parada':
                    primary_key = ", PRIMARY KEY (fact_id)"
                
                # Criar a tabela
                create_table_sql = f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    {', '.join(create_columns)}{primary_key}
                )
                """
                cursor.execute(create_table_sql)
                logging.info(f"Tabela {table_name} criada/verificada com sucesso.")

                # Inserir dados
                placeholders = ', '.join(['%s'] * len(df.columns))
                columns = ', '.join(df.columns)
                insert_sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
                
                for _, row in df.iterrows():
                    cursor.execute(insert_sql, tuple(row))

                connection.commit()
                logging.info(f"Dados inseridos na tabela {table_name}.")

        # Criar as tabelas dimensionais na ordem correta
        dim_artista = create_dim_artist(df)
        dim_parada = create_dim_parada(df)
        dim_album = create_dim_album(df, dim_artista)
        df_charts = get_charts_data()
        
        # Criar a tabela fato que relaciona as dimensões
        fact_album_parada = create_fact_album_parada(df, dim_album, dim_parada)
        
        # Salvar no MinIO
        save_to_minio(dim_artista, 'dim_artista', minio_client, bucket_name)
        save_to_minio(dim_album, 'dim_album', minio_client, bucket_name)
        save_to_minio(dim_parada, 'dim_parada', minio_client, bucket_name)
        save_to_minio(df_charts, 'charts_data', minio_client, bucket_name)
        save_to_minio(fact_album_parada, 'fact_album_parada', minio_client, bucket_name)
        
        # Salvar no MariaDB
        save_to_mariadb(dim_artista, 'dim_artista')
        save_to_mariadb(dim_album, 'dim_album')
        save_to_mariadb(dim_parada, 'dim_parada')
        save_to_mariadb(df_charts, 'charts_data')
        save_to_mariadb(fact_album_parada, 'fact_album_parada')
        
        logging.info("Camada Gold criada com sucesso!")
        
    except Exception as e:
        logging.error(f"Erro na criação da camada Gold: {e}")
        raise