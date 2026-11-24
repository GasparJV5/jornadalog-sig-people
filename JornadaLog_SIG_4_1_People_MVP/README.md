# JornadaLog SIG 4.1 People - MVP academico

Evolucao do JornadaLog SIG 3.2 para o modulo de RH, Jornada e Escalonamento da plataforma SIG-Log.

## Novidades do frontend 4.1
- Interface gerencial inspirada na versão anterior do JornadaLog.
- Menu lateral objetivo e responsivo.
- Menu e permissões demonstrativas por perfil.
- Barra superior com busca, ação rápida, API e notificações.
- Dashboard com KPIs, ciclo operacional, cobertura e fila de decisões.
- Telas funcionais para profissionais, certificações, disponibilidades, turnos, escalas, alocação e conflitos.
- Modal de cadastro e motor visual de validação.

## O que funciona neste pacote
- Inicializacao local com Flask e SQLite.
- Dashboard basico.
- Cadastro e listagem de profissionais.
- Endpoints iniciais de certificacao, disponibilidade, turno e escala.
- Validacao de cadastro, disponibilidade, certificacao e descanso.
- Confirmacao de alocacao com registro Outbox `MotoristaEscalado`.
- Docker Compose com app, PostgreSQL, RabbitMQ, Prometheus e Grafana como andaime.
- OpenAPI inicial, CI e testes unitarios do motor.

## Limite honesto do MVP
PostgreSQL, publicacao real no RabbitMQ, tracing Jaeger/OpenTelemetry, SonarQube, Trivy, K6 e telas completas estao estruturados como proximas evolucoes. O modo executavel atual usa SQLite. Nao marque esses itens como concluidos sem implementar e testar.

## Executar no Windows
1. Instale Python 3.12.
2. Extraia o ZIP.
3. Execute `INICIAR_WINDOWS.bat`.
4. Abra `http://localhost:5000`.

## Executar manualmente
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python app.py
```

## Testar
```powershell
pytest -v
```

## Docker
```powershell
copy .env.example .env
docker compose up --build -d
docker compose ps
```

## Endpoints iniciais
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

## Trabalho em equipe
Leia `docs/ATRIBUICOES_E_GITFLOW.md` antes de alterar o projeto.
