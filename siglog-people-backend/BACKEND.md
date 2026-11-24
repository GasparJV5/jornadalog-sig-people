# Backend Flask — SIG-Log People (Squad 05)

Referência técnica do backend (regras de negócio, casos de uso, API e testes).
Não substitui o `README.md` do repositório, que fica com a equipe de documentação.

Arquitetura em camadas (DDD): `src/domain` → `src/application` → `src/infrastructure` → `src/api`.

## Como rodar
    pip install -r requirements.txt
    python -m src.api.app                         # http://127.0.0.1:5005/health
    python -m unittest discover -s tests -t .     # ou: pytest

## Regras de negócio (src/domain/rules.py)
| Código | Regra |
|---|---|
| MOTORISTA_INATIVO / MOTORISTA_INDISPONIVEL | motorista ativo, com janela de disponibilidade cobrindo todo o período e sem bloqueio sobreposto |
| CNH_INCOMPATIVEL | categoria da CNH ≥ exigida pelo veículo (E cobre D, C, B; A é exclusiva) |
| CERTIFICACAO_AUSENTE / CERTIFICACAO_VENCIDA | certificações exigidas pelo veículo presentes e vigentes até o fim do período |
| DESCANSO_INSUFICIENTE | mínimo de 11h entre jornadas, antes e depois do período (`DESCANSO_MINIMO_HORAS`) |
| JORNADA_EXCEDIDA | período de no máximo 10h (`JORNADA_MAX_HORAS`) |
| CONFLITO_MOTORISTA / CONFLITO_VEICULO | sem sobreposição com alocações existentes |

Fluxo do Kit (A.5): se qualquer regra for violada, a alocação é negada; se tudo for válido, é permitida.
Premissa: cada alocação equivale a uma jornada de trabalho.

## Casos de uso
| Código | Caso de uso | Endpoint |
|---|---|---|
| UC01 | Cadastrar funcionário | POST /drivers |
| UC02 | Registrar certificação | POST /drivers/{id}/certifications |
| UC03 | Registrar disponibilidade | POST /drivers/{id}/availability |
| UC04 | Criar turno | POST /shifts |
| UC05 | Criar escala | POST /schedules |
| UC06 | Validar jornada | POST /journeys/validate |
| UC07 | Validar descanso | POST /rest-periods/validate |
| UC08 | Alocar motorista | POST /allocations |
| UC09 | Detectar conflito | GET /schedules/{id}/conflicts |
| UC10 | Consultar escala | GET /schedules/{id} |

Apoio: GET /drivers, GET /drivers/{id}, GET /drivers/{id}/availability, POST /vehicles,
POST /allocations/validate, POST /journeys/start, POST /journeys/{id}/finish, POST /rest-periods, GET /health.
Contrato completo em `openapi.yaml`.

## Erros
Formato único: `{"error": {"code": "...", "message": "...", "violacoes": [...]}}`
400 validação · 404 não encontrado · 409 conflito de estado · 422 regra de negócio.

## Catálogo de eventos publicados
Envelope: `{"event_id", "event", "occurred_at", "payload"}`. Exchange sugerida: `siglog.events` (topic), routing key = nome do evento.

| Evento | Quando | Campos do payload |
|---|---|---|
| MotoristaEscalado | alocação aceita (consumido pelo Fleet) | alocacao_id, motorista_id, veiculo_id, inicio, fim, escala_id, viagem_id |
| JornadaIniciada | início de jornada | jornada_id, funcionario_id, inicio |
| JornadaFinalizada | fim de jornada | jornada_id, funcionario_id, inicio, fim, horas, excedeu_limite |
| DescansoRegistrado | descanso válido registrado | descanso_id, funcionario_id, inicio, fim, horas |
| CertificacaoAtualizada | certificação criada ou renovada | funcionario_id, tipo, validade |
| ConflitoDeJornadaDetectado | tentativa de alocação com conflito | funcionario_id, veiculo_id, inicio, fim, conflitos[{codigo, mensagem}] |

Datas em ISO-8601. `escala_id` e `viagem_id` podem ser nulos em `MotoristaEscalado`.

## Persistência (ponto de integração com o banco)
Hoje os repositórios são em memória (`src/infrastructure/memory_repositories.py`).
Para PostgreSQL, implemente as mesmas operações (add, get, list e as consultas específicas) com SQLAlchemy;
casos de uso e regras não mudam. IDs atuais são UUID em texto.

## Pendências
Repositórios PostgreSQL, métricas Prometheus/OpenTelemetry, autenticação/autorização,
teste de carga (K6), definir com o Fleet o contrato final de `MotoristaEscalado`.
