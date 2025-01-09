import requests
from bs4 import BeautifulSoup
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import warnings


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


print("Arquivo salvo como albums.parquet")
