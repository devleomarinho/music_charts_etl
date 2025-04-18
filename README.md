# Pipeline ETL - Engenharia e Análise de Dados musicais

## 📊 Sobre o Projeto
Projeto de Engenharia de Dados que consiste em criar um pipeline de ETL, desenvolvido para coletar e processar dados históricos das paradas musicais mundiais desde 1950. O projeto realiza web scraping do site The World's Music Charts, processando informações de mais de 500 mil entradas de charts musicais de 22 países diferentes.


![diagrama2](https://github.com/user-attachments/assets/07e6eefd-d6ca-46f7-9e2c-a1bedf255cf7)



## 🏗️ Arquitetura

O projeto está estruturado em duas camadas principais:

### Layer Bronze
- Web scraping do The World's Music Charts
- Armazenamento dos dados brutos em formato Parquet no MinIO
- Persistência em tabela 'albums_bronze' no MariaDB

### Layer Silver
- Processamento dos dados da camada Bronze
- Normalização da estrutura (separação das entradas nas paradas em registros individuais)
- Armazenamento em formato Parquet no MinIO
- Persistência na tabela 'albums_silver' no MariaDB

### Layer Gold
- Criação das tabelas dimensão;
- Criação da tabela fato relacionada às entradas nas paradas de sucesso;
- Enriquecimento com um novo scraping para criação da tabela dimensão com informações sobre cada parada;
  
## 🛠️ Tecnologias Utilizadas

- **Docker**: Containerização do ambiente
- **Apache Airflow**: Orquestração das tasks
- **MinIO**: Armazenamento de arquivos
- **MariaDB**: Banco de dados relacional
- **Python**: Linguagem principal para ETL
- **DBeaver**: Interface para gestão do banco de dados
- **Apache Superset**: Ferramenta de data viz utilizada para gerar dashboards a partir da camada gold

## 📈 Dataset

O projeto utiliza dados do The World's Music Charts, que inclui:
- 529.468 entradas individuais em paradas musicais
- 238 charts diferentes de 22 países
- 154.916 músicas e 89.258 álbuns
- Dados de mais de 40.000 artistas

## 🚀 Como Executar

1. Clone o repositório
```bash
git clone https://github.com/devleomarinho/music_charts_etl.git

```

2. Configure o ambiente Docker
```bash
docker-compose up -d
```

3. Acesse a interface do Airflow
```bash
http://localhost:8080
```

4. Acesse a interface do MinIO:
```bash
http://localhost:9001/
```

5. Acesse a interface do Apache Superset:
```bash
http://localhost:8088/
```

## Melhorias futuras

Este projeto está funcionando, todas as imagens estão sendo criadas corretamente no docker compose, o script de webscraping está funcionando e as tasks do airflow estão rodando, as camadas bronze, silver e gold estão sendo criadas também. Está faltando apenas a criação dos dashboards no Apache Superset, então fique à vontade para criar as suas próprias análises!
