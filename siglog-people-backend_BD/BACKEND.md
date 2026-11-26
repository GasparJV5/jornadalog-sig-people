# Backend Flask — SIG-Log People (Squad 05)

Referência técnica do backend (regras de negócio, casos de uso, API, persistência e testes).
Não substitui o `README.md` do repositório, que fica com a equipe de documentação.

Camadas (DDD): `src/domain` → `src/application` → `src/infrastructure` → `src/api`.

## Como rodar
    pip install -r requirements.txt
    python -m src.api.app                                   # memória (padrão) — http://127.0.0.1:5005/health
    PERSISTENCE=postgres python -m src.api.app              # PostgreSQL (veja abaixo)
    python -m unittest discover -s tests -t .               # ou: pytest

PowerShell: `$env:PERSISTENCE="postgres"; python -m src.api.app`.
No PyCharm: Run → Edit Configurations → Environment variables → `PERSISTENCE=postgres`.

## Persistência: PostgreSQL
Variáveis (as mesmas dos scripts `executar_migrations.py`/`executar_seeds.py`; lidas do ambiente ou do `.env`):
`POSTGRES_HOST` (localhost), `POSTGRES_PORT` (5432), `POSTGRES_DB` (RH_Jornada), `POSTGRES_USER` (rh_admin), `POSTGRES_PASSWORD` (obrigatória).

Pré-requisitos no banco: migrations 000–003 + seeds (cargos *Motorista* e *Operador* são obrigatórios).
Tudo está em `database/` e é aplicado por scripts (a 003 ainda deve ser revisada pela infraestrutura):

    cp .env.example .env                       # defina POSTGRES_PASSWORD
    docker compose up -d                       # PostgreSQL 18 local (opcional)
    python database/scripts/executar_migrations.py   # 000–003, registradas em controle_migrations
    python database/scripts/executar_seeds.py        # cargos, certificações e turnos iniciais (idempotente)
    PERSISTENCE=postgres python -m src.api.app

Relay da outbox → RabbitMQ (processo separado): `RABBITMQ_URL=amqp://... python -m src.infrastructure.outbox_relay`
(entrega *at-least-once*: consumidores devem deduplicar por `event_id`).

Como funciona
* Uma transação por requisição: commit se HTTP < 400; rollback se erro. Exceção: **422 de alocação negada** faz
  commit, para registrar o evento `ConflitoDeJornadaDetectado` (nada mais é gravado nesse caso).
* Eventos vão para `outbox_eventos` (status PENDENTE) **na mesma transação** da operação. `payload` guarda o envelope
  `{event_id, event, occurred_at, payload}`. O relay (`src/infrastructure/outbox_relay.py`) lê a outbox e publica no RabbitMQ.
* IDs são BIGINT no banco e texto na API.

Mapeamento domínio ↔ banco
| Domínio | Banco |
|---|---|
| Tipo MOTORISTA/OPERADOR | cargo *Motorista* / demais cargos |
| CPF, categoria da CNH | `funcionarios.cpf`, `.cnh_categoria` (003) |
| Matrícula, admissão | gerados: `MAT<cpf>`, data de hoje |
| Certificação (tipo, validade, ativa) | `funcionario_certificacoes` + catálogo `certificacoes` (criado se não existir); `SUSPENSA` = inativa |
| Disponibilidade (janela data/hora) | `disponibilidades` semanal: 1 linha por dia, vigência de 1 dia; linhas recorrentes do banco também valem na validação |
| Alocação | `alocacoes` (+ `veiculo_id`, `viagem_id` da 003); período = data da escala + horários |
| Jornada | `registros_jornada` (entrada_real/saida_real), sempre ligada a uma alocação |
| Veículo: CNH e certificações exigidas | `veiculos.cnh_exigida`, `veiculo_certificacoes_exigidas` (003) |

Convenção de `dia_semana`: 0 = domingo … 6 = sábado. Janela até meia-noite é gravada com `hora_fim = 23:59:59.999999`.

## Regras de negócio (src/domain/rules.py)
| Código | Regra |
|---|---|
| MOTORISTA_INATIVO / MOTORISTA_INDISPONIVEL | motorista ativo, com janelas de disponibilidade cobrindo todo o período e sem bloqueio sobreposto |
| CNH_INCOMPATIVEL | categoria da CNH ≥ exigida pelo veículo (E cobre D, C, B; A é exclusiva) |
| CERTIFICACAO_AUSENTE / _VENCIDA / _SUSPENSA | certificações exigidas presentes, ativas e vigentes até o fim do período |
| DESCANSO_INSUFICIENTE | mínimo de 11h entre jornadas, antes e depois do período (`DESCANSO_MINIMO_HORAS`) |
| JORNADA_EXCEDIDA | período de no máximo 10h (`JORNADA_MAX_HORAS`) |
| CONFLITO_MOTORISTA / CONFLITO_VEICULO | sem sobreposição com alocações existentes |

Premissas: cada alocação equivale a uma jornada; o intervalo de almoço do turno (`intervalo_minutos`) não entra no cálculo.

## Casos de uso e endpoints
| Código | Caso de uso | Endpoint |
|---|---|---|
| UC01 | Cadastrar funcionário | POST /drivers |
| UC02 | Registrar certificação | POST /drivers/{id}/certifications |
| UC03 | Registrar disponibilidade | POST /drivers/{id}/availability |
| UC04 | Criar turno | POST /shifts |
| UC05 | Criar escala | POST /schedules |
| UC06 | Validar jornada | POST /journeys/validate |
| UC07 | Validar descanso | POST /rest-periods/validate |
| UC08 | Alocar motorista | POST /allocations (**escala_id obrigatório**) |
| UC09 | Detectar conflito | GET /schedules/{id}/conflicts |
| UC10 | Consultar escala | GET /schedules/{id} |

Apoio: GET /drivers, GET /drivers/{id}, GET /drivers/{id}/availability, POST /vehicles, POST /allocations/validate,
POST /journeys/start (**alocacao_id obrigatório**), POST /journeys/{id}/finish, POST /rest-periods, GET /health.
Contrato completo em `openapi.yaml`.

Violações de constraint do banco viram 409 (UNIQUE), 422 (FK/CHECK) ou 400 (NOT NULL/tamanho).
Erros: `{"error": {"code", "message", "violacoes?"}}` — 400 validação · 404 · 409 conflito de estado · 422 regra de negócio.

## Catálogo de eventos
Envelope: `{"event_id", "event", "occurred_at", "payload"}`. Exchange sugerida: `siglog.events` (topic), routing key = nome do evento.

| Evento | Quando | Campos do payload |
|---|---|---|
| MotoristaEscalado | alocação aceita (consumido pelo Fleet) | alocacao_id, motorista_id, veiculo_id, inicio, fim, escala_id, viagem_id |
| JornadaIniciada | início de jornada | jornada_id, funcionario_id, alocacao_id, inicio |
| JornadaFinalizada | fim de jornada | jornada_id, funcionario_id, inicio, fim, horas, excedeu_limite |
| DescansoRegistrado | descanso válido registrado | descanso_id, funcionario_id, inicio, fim, horas |
| CertificacaoAtualizada | certificação criada ou renovada | funcionario_id, tipo, validade |
| ConflitoDeJornadaDetectado | tentativa de alocação com conflito | funcionario_id, veiculo_id, inicio, fim, conflitos[{codigo, mensagem}] |

`viagem_id` pode ser nulo em `MotoristaEscalado`.

## Testes
`tests/unit` (regras, casos de uso, conversão de disponibilidade, repositórios SQL com banco falso) ·
`tests/integration/test_api.py` (API em memória) · `tests/contract` (eventos, formato das respostas e `openapi.yaml`) ·
`tests/integration/test_postgres.py` (PostgreSQL real; só roda com `POSTGRES_TEST_DB` — instruções no arquivo).

## Pendências
Autenticação/autorização · métricas Prometheus/OpenTelemetry · teste de carga (K6) ·
contrato final de `MotoristaEscalado` com o Fleet · revisão da migration 003 pela infraestrutura · validar o relay contra um RabbitMQ real.
