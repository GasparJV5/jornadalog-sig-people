# Ambiente Local — JornadaLog SIG 4.1 People

## 1. Objetivo

Este documento apresenta as instruções para configurar e executar localmente o ambiente de banco de dados e infraestrutura do módulo People.

## 2. Pré-requisitos

- Docker Desktop em execução.
- Docker Compose.
- Python 3.
- Git.

## 3. Configuração do ambiente

Na raiz do projeto, crie o arquivo `.env` a partir do exemplo:

```bash
cp .env.example .env
```

Edite o arquivo `.env` e configure os valores das variáveis:

- `POSTGRES_PASSWORD`: senha do PostgreSQL.
- `RABBITMQ_DEFAULT_USER`: usuário do RabbitMQ.
- `RABBITMQ_DEFAULT_PASS`: senha do RabbitMQ.

O arquivo `.env` contém credenciais locais e não deve ser enviado ao Git.

## 4. Subindo a infraestrutura

Na raiz do projeto, execute:

```bash
docker compose up -d
```

Para verificar os containers:

```bash
docker compose ps
```

## 5. Banco de dados

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

As migrations criam e atualizam a estrutura do banco. Os seeds inserem os dados iniciais necessários ao ambiente.

## 6. Serviços disponíveis

| Serviço | Endereço |
|---|---|
| PostgreSQL | localhost:5432 |
| PostgreSQL Exporter | postgres-exporter:9187 (rede Docker) |
| RabbitMQ | localhost:5672 |
| Painel RabbitMQ | http://localhost:15672 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 |
| Jaeger | http://localhost:16686 |
| OpenTelemetry OTLP gRPC | localhost:4317 |
| OpenTelemetry OTLP HTTP | localhost:4318 |

As credenciais do RabbitMQ são definidas pelas variáveis do arquivo `.env`.

## 7. Monitoramento e observabilidade

- Prometheus coleta métricas dos alvos configurados.
- PostgreSQL Exporter disponibiliza métricas do banco PostgreSQL.
- RabbitMQ disponibiliza métricas por meio do plugin Prometheus.
- Grafana utiliza Prometheus e Jaeger como fontes de dados.
- O dashboard principal do Grafana apresenta indicadores de monitoramento da infraestrutura.
- OpenTelemetry Collector recebe dados pelos protocolos OTLP e encaminha traces ao Jaeger.
- Jaeger permite visualizar traces distribuídos enviados pela aplicação.
