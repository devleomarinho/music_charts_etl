# Pipeline ETL - Engenharia e Análise de Dados musicais

## 📊 Sobre o Projeto
Projeto de Engenharia de Dados que consiste em criar um pipeline de ETL, desenvolvido para coletar e processar dados históricos das paradas musicais mundiais desde 1950. O projeto realiza web scraping do site The World's Music Charts, processando informações de mais de 500 mil entradas de charts musicais de 22 países diferentes.

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

## 🛠️ Tecnologias Utilizadas

- **Docker**: Containerização do ambiente
- **Apache Airflow**: Orquestração das tasks
- **MinIO**: Armazenamento de arquivos
- **MariaDB**: Banco de dados relacional
- **Python**: Linguagem principal para ETL
- **DBeaver**: Interface para gestão do banco de dados

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

## Melhorias futuras

Este projeto está em desenvolvimento, portanto ainda irei adicionar um outra camada, a GOLD, com novas transformações e preparando-a para criação de análises usando ferramentas de visualização como Apache Superset, Metabase ou Power BI.
