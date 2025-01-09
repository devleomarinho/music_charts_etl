import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import boto3
import io
import logging


# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def google_sheet_to_minio_etl(sheet_id, sheet_name, bucket_name, endpoint_url, access_key, secret_key):
    # Configuração do cliente MinIO
    minio_client = boto3.client(
        's3',
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key
    )

    def get_google_sheet_data(sheet_id, sheet_name):
        try:
            scope = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
            creds = Credentials.from_service_account_file('/opt/airflow/config_airflow/credentials.json', scopes=scope)
            client = gspread.authorize(creds)
            sheet = client.open_by_key(sheet_id).worksheet(sheet_name)
            try:
                data = sheet.get_all_records()
            except gspread.exceptions.GSpreadException as e:
                if 'A linha de cabeçalho na planilha não é única.' in str(e):
                    logging.warning(f"Erro ao usar get_all_records() (cabeçalhos duplicados): {e}")
                    expected_headers = {
                        'Clientes_Bike': ["ClienteID", "Cliente", "Estado", "Sexo", "Status"],
                        'Vendedores_Bike': ["VendedorID", "Vendedor"],
                        'Produtos_Bike': ["ProdutoID", "Produto", "Preco"],
                        'Vendas_Bike': ["VendasID", "VendedorID", "ClienteID", "Data", "Total"],
                        'ItensVendas_Bike': ["ProdutoID", "VendasID", "Quantidade", "ValorUnitario", "ValorTotal", "Desconto", "TotalComDesconto"]
                    }.get(sheet_name, None)
                    if expected_headers:
                        data = sheet.get_all_records(expected_headers=expected_headers)
                    else:
                        raise
            if not data:
                raise ValueError(f"Nenhum dado foi retornado para a planilha {sheet_name}")

            df = pd.DataFrame(data)
            return df
        except Exception as e:
            logging.error(f"Erro ao obter dados da planilha do Google: {e}")
            raise

    try:
        df = get_google_sheet_data(sheet_id, sheet_name)
        parquet_buffer = io.BytesIO()
        df.to_parquet(parquet_buffer, index=False)
        parquet_buffer.seek(0)
        minio_client.put_object(Bucket=bucket_name, Key=f"{sheet_name}/data.parquet", Body=parquet_buffer.getvalue())
    except Exception as e:
        logging.error(f"Erro ao processar a planilha {sheet_name}: {e}")
        raise
    