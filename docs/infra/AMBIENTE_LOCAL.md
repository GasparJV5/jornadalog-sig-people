
# Ambiente Local — JornadaLog SIG 4.1 People

## 1. Objetivo

Este documento apresenta as instruções para configurar e executar localmente o ambiente de banco de dados e infraestrutura do projeto.

## 2. Pré-requisitos

- Docker Desktop em execução.
- Docker Compose.
- Python 3.
- Git.

## 3. Subindo a infraestrutura

Na raiz do projeto, execute:

```bash
docker compose up -d
```

Para verificar os containers:

```bash
docker compose ps
```

## 4. Banco de dados

Instale as dependências Python:

```bash
pip install -r requirements.txt
```

Execute as migrations:

```bash
python database/scripts/executar_migrations.py
```

Execute os dados iniciais:

```bash
python database/scripts/executar_seeds.py
```

## 5. Serviços disponíveis

- PostgreSQL: localhost:5432
- RabbitMQ: localhost:5672
- Painel RabbitMQ: http://localhost:15672
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000
- Jaeger: http://localhost:16686
- OpenTelemetry OTLP gRPC: localhost:4317
- OpenTelemetry OTLP HTTP: localhost:4318

## 6. Monitoramento e observabilidade

- Prometheus coleta métricas dos alvos configurados.
- Grafana utiliza o Prometheus e o Jaeger como fontes de dados.
- OpenTelemetry Collector recebe dados OTLP e encaminha traces ao Jaeger.
- O Jaeger permite visualizar traces enviados pela aplicação.
- A visualização de traces depende da instrumentação do backend.

## 7. Encerrando a infraestrutura

Para parar os containers, execute:

```bash
docker compose down
```

Os volumes são preservados ao utilizar esse comando.

Evite utilizar `docker compose down -v`, pois esse comando remove os volumes e pode apagar os dados persistidos.

