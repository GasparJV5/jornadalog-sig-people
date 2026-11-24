# JornadaLog SIG 4.1 People — Banco de Dados e Infraestrutura

## 1. Sobre o projeto

Este repositório contém a implementação da parte de banco de dados e infraestrutura do módulo **People** do sistema JornadaLog SIG 4.1.

O objetivo é fornecer uma estrutura de banco de dados e um ambiente local conteinerizado, com serviços de mensageria, monitoramento e observabilidade.

## 2. Tecnologias utilizadas

- **PostgreSQL 18:** banco de dados relacional.
- **Docker e Docker Compose:** conteinerização e gerenciamento dos serviços.
- **RabbitMQ 4:** mensageria.
- **Prometheus:** coleta de métricas.
- **Grafana:** visualização e dashboards.
- **PostgreSQL Exporter:** exposição de métricas do PostgreSQL.
- **OpenTelemetry Collector:** recepção e encaminhamento de telemetria.
- **Jaeger:** visualização de traces distribuídos.
- **Python:** execução automatizada de migrations e seeds.
- **Psycopg 3:** conexão com PostgreSQL.

## 3. Estrutura do banco de dados

O banco utiliza PostgreSQL e possui as seguintes tabelas:

- `funcionarios`
- `cargos`
- `certificacoes`
- `funcionario_certificacoes`
- `turnos`
- `disponibilidades`
- `escalas`
- `registros_jornada`
- `alocacoes`
- `veiculos`
- `descansos`
- `outbox_eventos`
- `controle_migrations`

A estrutura é organizada por migrations SQL versionadas.

## 4. Migrations e Seeds

As migrations criam e atualizam a estrutura do banco de dados.

Os seeds inserem dados iniciais necessários para o ambiente.

Scripts disponíveis:

- `database/scripts/executar_migrations.py`
- `database/scripts/executar_seeds.py`

## 5. Ambiente local

### Pré-requisitos

- Docker Desktop
- Docker Compose
- Python 3
- Git

### Configuração

Crie o arquivo `.env` a partir do exemplo:

```bash
cp .env.example .env
```

Configure as variáveis necessárias no arquivo `.env`.

**Importante:** o arquivo `.env` contém configurações locais e não deve ser enviado ao Git.

### Inicialização

Suba os serviços:

```bash
docker compose up -d
```

Verifique os containers:

```bash
docker compose ps
```

Instale as dependências Python:

```bash
pip install -r requirements.txt
```

Execute as migrations:

```bash
python database/scripts/executar_migrations.py
```

Execute os seeds:

```bash
python database/scripts/executar_seeds.py
```

## 6. Serviços disponíveis

| Serviço | Endereço local |
|---|---|
| PostgreSQL | `localhost:5432` |
| RabbitMQ | `localhost:5672` |
| RabbitMQ Management | `http://localhost:15672` |
| Prometheus | `http://localhost:9090` |
| Grafana | `http://localhost:3000` |
| Jaeger | `http://localhost:16686` |

O PostgreSQL Export
