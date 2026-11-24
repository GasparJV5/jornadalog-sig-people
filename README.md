# JornadaLog SIG 4.1 People

Módulo de RH, Jornada e Escalonamento da plataforma JornadaLog SIG 4.1.

Este projeto evolui o JornadaLog SIG 3.2, reunindo funcionalidades de gestão de profissionais, certificações, disponibilidade, turnos, escalas e alocação.

## 1. Funcionalidades do MVP

- Interface gerencial com menu lateral e navegação por perfil.
- Dashboard com indicadores operacionais.
- Cadastro e listagem de profissionais.
- Gestão de certificações e disponibilidades.
- Gestão de turnos e escalas.
- Validação de disponibilidade, certificação e descanso.
- Validação e confirmação de alocações.
- Registro de eventos Outbox, incluindo `MotoristaEscalado`.
- Endpoints iniciais para as funcionalidades do módulo.

## 2. Tecnologias

### Aplicação
- Python
- Flask
- SQLite no MVP inicial
- PostgreSQL para a infraestrutura de banco de dados
- OpenAPI
- Pytest

### Banco de dados e infraestrutura
- PostgreSQL 18
- Docker e Docker Compose
- RabbitMQ 4
- Prometheus
- Grafana
- PostgreSQL Exporter
- OpenTelemetry Collector
- Jaeger
- Python e Psycopg 3

## 3. Banco de dados

A infraestrutura de banco de dados utiliza PostgreSQL e possui migrations SQL versionadas.

As tabelas implementadas são:

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

A estrutura contempla o controle de migrations e o registro de eventos Outbox.

## 4. Migrations e Seeds

Scripts disponíveis:

- `database/scripts/executar_migrations.py`
- `database/scripts/executar_seeds.py`

As migrations criam e atualizam a estrutura do banco. Os seeds inserem os dados iniciais necessários para o ambiente.

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

**Importante:** não envie o arquivo `.env` para o Git. Utilize o `.env.example` como referência.

### Inicialização da infraestrutura

```bash
docker compose up -d
```

Verifique os serviços:

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

| Serviço | Endereço |
|---|---|
| PostgreSQL | `localhost:5432` |
| RabbitMQ | `localhost:5672` |
| RabbitMQ Management | `http://localhost:15672` |
| Prometheus | `http://localhost:9090` |
| Grafana | `http://localhost:3000` |
| Jaeger | `http://localhost:16686` |
| OpenTelemetry OTLP gRPC | `localhost:4317` |
| OpenTelemetry OTLP HTTP | `localhost:4318` |

O PostgreSQL Exporter e o OpenTelemetry Collector também fazem parte do ambiente Docker.

## 7. Monitoramento e observabilidade

A infraestrutura possui:

- Prometheus configurado para coletar métricas do PostgreSQL, RabbitMQ, OpenTelemetry Collector e do próprio Prometheus.
- Grafana configurado com fontes de dados Prometheus e Jaeger.
- Dashboard de monitoramento da infraestrutura.
- PostgreSQL Exporter para exposição de métricas do banco.
- OpenTelemetry Collector preparado para receber telemetria via OTLP.
- Jaeger configurado para visualização de traces distribuídos.

**Observação:** a infraestrutura de observabilidade está configurada. A geração de traces e métricas da aplicação depende da instrumentação e integração do backend.

## 8. Executar o MVP no Windows

Para executar a aplicação inicial:

1. Instale Python 3.12.
2. Prepare o ambiente virtual.
3. Instale as dependências.
4. Configure o arquivo `.env`.
5. Execute a aplicação conforme as instruções do projeto.

Execução manual:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python app.py
```

A aplicação inicial utiliza o endereço:

`http://localhost:5000`

A execução da aplicação MVP e a inicialização da infraestrutura PostgreSQL são procedimentos distintos até a integração do backend com o novo banco.

## 9. Testes

Para executar os testes disponíveis:

```bash
pytest -v
```

## 10. Endpoints iniciais do MVP

- `GET /health`
- `GET /api/dashboard`
- `GET|POST /api/employees`
- `POST /api/certifications`
- `POST /api/availabilities`
- `POST /api/shifts`
- `GET|POST /api/schedules`
- `POST /api/allocations/validate`
- `POST /api/allocations`
- `GET /api/conflicts`

## 11. Documentação complementar

- [Atribuições e GitFlow](docs/ATRIBUICOES_E_GITFLOW.md)
- [Ambiente Local](docs/infra/AMBIENTE_LOCAL.md)
- [Diagrama Entidade-Relacionamento](docs/infra/DER.md)

## 12. Trabalho em equipe

Antes de realizar alterações no projeto, consulte `docs/ATRIBUICOES_E_GITFLOW.md` para conhecer as responsabilidades e o fluxo de trabalho da equipe.