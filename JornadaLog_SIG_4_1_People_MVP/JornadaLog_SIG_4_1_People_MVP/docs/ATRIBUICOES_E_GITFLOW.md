# Atribuicoes, versionamento e integracao do trio

## Objetivo ate segunda-feira
Entregar um MVP executavel que preserve o JornadaLog, demonstre cadastro de profissionais, dashboard, dados persistidos, regras de alocacao, evento de dominio e estrutura academica para evolucao.

## Joao: produto, frontend e consolidacao
- Evoluir `static/` sem quebrar o Fetch.
- Implementar menu, dashboard, pessoas, escalas e conflitos.
- Produzir Project Charter, CSD, personas, BPM/BPMN, README e roteiro da demonstracao.
- Validar `INICIAR_WINDOWS.bat`, acessibilidade e ZIP final.
- Branches: `feature/ui-dashboard`, `feature/ui-pessoas`, `docs/produto`.

## Brenner: dados, Docker e infraestrutura
- Revisar DER, schemas SQLite/PostgreSQL, seeds e migrations.
- Evoluir `src/infrastructure/`, `database/`, `Dockerfile` e `docker-compose.yml`.
- Configurar RabbitMQ/Outbox, Prometheus/Grafana e CI.
- Branches: `feature/database`, `feature/docker`, `feature/observability`.

## Aughusto: dominio, API e testes
- Implementar UC01 a UC10 em `src/domain/`, `src/application/` e `src/api/`.
- Evoluir `openapi.yaml`, motor de alocacao e eventos.
- Criar testes unitarios, integracao e contrato; preparar ADRs e ATAM.
- Branches: `feature/domain`, `feature/api`, `test/allocation-engine`.

## Fluxo Git dos tres
### 1. Dono do repositorio
```powershell
git init
git add .
git commit -m "chore: baseline MVP SIG-Log People"
git branch -M main
git remote add origin URL_DO_REPOSITORIO
git push -u origin main
git checkout -b develop
git push -u origin develop
```
Proteja `main` e exija Pull Request. Convide Brenner e Aughusto em Settings > Collaborators.

### 2. Cada integrante clona
```powershell
git clone URL_DO_REPOSITORIO
cd JornadaLog_SIG_4_0_People_MVP
git checkout develop
git pull origin develop
git checkout -b feature/NOME-DA-TAREFA
```

### 3. Cada integrante envia a sua parte
```powershell
git status
git add .
git commit -m "feat: descricao objetiva da entrega"
git push -u origin feature/NOME-DA-TAREFA
```
No GitHub: Pull requests > New pull request > base `develop` > compare sua branch. Outro integrante revisa e aprova.

### 4. Atualizar antes do merge
```powershell
git checkout develop
git pull origin develop
git checkout feature/NOME-DA-TAREFA
git merge develop
# resolver conflitos, testar e depois:
git add .
git commit -m "merge: sincronizar com develop"
git push
```
Nunca sobrescrever conflitos sem conversar com o responsavel pelo arquivo.

### 5. Integracao final
```powershell
git checkout develop
git pull origin develop
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -v
python app.py
```
Abra `http://localhost:5000` e execute o roteiro de aceite.

### 6. Merge para main e release
Crie PR `develop` -> `main`, revise em conjunto e execute:
```powershell
git checkout main
git pull origin main
git tag -a v1.0.0 -m "MVP academico SIG-Log People"
git push origin v1.0.0
```
No GitHub: Releases > Draft a new release > tag `v1.0.0` > anexar ZIP e resumo.

## Ordem de merge recomendada
1. Brenner: banco e infraestrutura.
2. Aughusto: dominio, API e testes.
3. Joao: interface, Fetch e documentacao.
4. Trio: correcao de integracao, teste e release.

## Geracao da documentacao final
Atualizem os arquivos em `docs/`. Depois gerem inventario e evidencias:
```powershell
python -m compileall app.py src
pytest --cov=src --cov-report=html
node --check staticpp.js
docker compose config
docker compose up --build -d
docker compose ps
```
Incluam no README: problema, arquitetura, instalacao, endpoints, regras, testes, Docker, integrantes, trade-offs e roteiro de demo. Registrem prints do sistema, GitHub Actions, RabbitMQ, Grafana e testes quando estiverem efetivamente funcionando.

## Regra de pronto
Uma tarefa so entra no merge quando tem codigo versionado, PR, revisao por outra pessoa, teste, contrato/documentacao atualizados e nenhuma regressao visivel.
