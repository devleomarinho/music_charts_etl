#%%
import requests
from bs4 import BeautifulSoup
import pandas as pd
import warnings
import logging

#%%
def get_charts_data():
    """Realizar web scraping da página de charts"""
    warnings.filterwarnings("ignore", message="Unverified HTTPS request")
    
    url = "https://tsort.info/music/charta.htm"
    all_data = []

    def extract_data_from_table(soup):
        """Extrair dados da tabela de charts"""
        # Encontrar a tabela
        table = soup.find('table', class_='chartlist')
        if not table:
            logging.error("Tabela 'chartlist' não encontrada na página.")
            return []
        
        # Encontrar todas as linhas da tabela (ignorando o cabeçalho)
        rows = table.find_all('tr')[1:]  # Pular a linha de cabeçalho
        data = []
        
        for row in rows:
            # Extrair as colunas da tabela
            name = row.find("td", class_="nam")
            period_covered = row.find("td", class_="sta")
            max_pos = row.find("td", class_="max")
            num_entries = row.find("td", class_="ent")
            region = row.find("td", class_="reg")
            type_ = row.find("td", class_="typ")
            description = row.find("td", class_="des")
            
            # Verificar se todos os elementos foram encontrados
            if not all([name, period_covered, max_pos, num_entries, region, type_, description]):
                logging.warning(f"Linha incompleta encontrada: {row}")
                continue  # Pular linhas incompletas
            
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

    df_charts = pd.DataFrame(all_data)
    return df_charts
# %%
df_ = get_charts_data()
# %%
df_
# %%
