FROM postgis/postgis:15-3.5
COPY Infra/initdb/ /docker-entrypoint-initdb.d/
