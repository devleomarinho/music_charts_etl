FROM apache/superset

# Instalar todas as dependências necessárias para o mysqlclient
USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev \
    pkg-config \
    build-essential \
    python3-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Instalar os drivers Python para o MySQL
USER superset
RUN pip install pymysql
RUN pip install mysqlclient

ENV SUPERSET_HOME=/app/superset_home

USER superset
ENTRYPOINT ["/bin/bash", "-c"]

CMD ["\
  superset db upgrade && \
  superset fab create-admin \
    --username ${ADMIN_USERNAME} \
    --firstname ${ADMIN_FIRSTNAME} \
    --lastname ${ADMIN_LASTNAME} \
    --email ${ADMIN_EMAIL} \
    --password ${ADMIN_PASSWORD} && \
  superset init && \
  superset run -h 0.0.0.0 -p 8088 --with-threads --reload --debugger\
"]