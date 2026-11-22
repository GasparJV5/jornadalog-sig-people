# Mapeamento de Frontend, UX e Heurísticas — SIG-Log People (Squad 05)

Documentação das telas, fluxos de experiência do usuário (UX) e critérios de integração Frontend ↔ Backend Flask para consolidação do produto **SIG-Log People**.

---

## 1. Telas Implementadas e Responsabilidades (Frente Frontend)

| Módulo / Menu | Tela | Casos de Uso | Funcionalidades Principais |
| :--- | :--- | :--- | :--- |
| **Visão Geral** | Dashboard Gerencial | `UC01`–`UC10` | Cards de indicadores em tempo real, cobertura de turnos, fila de decisões críticas e atalhos rápidos. |
| **Pessoas** | Profissionais | `UC01` | Listagem, busca por nome/matrícula/unidade, filtro por perfil (`MOTORISTA`/`OPERADOR`), status de aptidão operacional e modal de cadastro. |
| **Pessoas** | Cargos e Perfis | `UC01`, `UC02` | Matriz de cargos operacionais com CBO, certificações exigidas, descanso mínimo obrigatório e modal de criação de cargo. |
| **Pessoas** | Certificações | `UC02` | Controle de validade de MOPP, NR-11, CNH e Direção Defensiva com alerta visual para documentos vencidos ou a vencer. |
| **Planejamento** | Disponibilidades | `UC03` | Registro de janelas livres e períodos de folga/indisponibilidade (com precedência sobre disponibilidade). |
| **Planejamento** | Turnos | `UC04` | Cadastro de turnos operacionais (`Turno A`, `Turno B`, `Turno C`), horários (incluindo virada de meia-noite) e necessidade de vagas. |
| **Planejamento** | Escalas | `UC05` | Grade de escalas por data e turno, indicador de cobertura de vagas e modal para publicação de novas escalas. |
| **Operação** | Validar Alocação | `UC06`, `UC07`, `UC08` | Motor de validação preventiva que cruza disponibilidade, certificação e descanso antes de emitir o evento `MotoristaEscalado`. |
| **Controle** | Conflitos e Alertas | `UC09` | Fila auditável de bloqueios preventivos (`CERTIFICACAO_VENCIDA`, `DESCANSO_INSUFICIENTE`, `COBERTURA_INCOMPLETA`). |

---

## 2. Heurísticas de Usabilidade de Nielsen Aplicadas

1. **Visibilidade do Status do Sistema (Heurística #1):**
   * Indicador dinâmico no cabeçalho (`● API Online` vs. `● Modo Demo (Local)`), garantindo que a interface nunca trave em tela vazia caso o servidor Flask esteja offline.
   * Badges semânticos em todas as tabelas (`APTO PARA ESCALA`, `COBERTA`, `PENDENTE`, `BLOQUEADO`).
2. **Correspondência entre o Sistema e o Mundo Real (Heurística #2):**
   * Terminologia alinhada à operação logística multimodal (CBO, MOPP, NR-11, interjornada legal de 11h, turnos e unidades operacionais)[cite: 4, 7].
3. **Controle e Liberdade do Usuário (Heurística #3):**
   * Modais de cadastro rápido com botão explícito de cancelamento e feedback imediato via notificações (*toast*) e gaveta de alertas (`🔔`).
4. **Prevenção de Erros (Heurística #5):**
   * Na tela de **Alocações**, ao selecionar um profissional com restrição (ex.: certificação vencida ou descanso inferior a 11h), o sistema exibe um **Alerta Preventivo** antes mesmo da submissão, explicando o motivo exato do bloqueio[cite: 7].
   * Controle de acesso por perfil (`roleSelect`), bloqueando rotas não autorizadas conforme o papel selecionado (`Gestor de Operações`, `Gestor de RH`, `Operador`, `Profissional`, `Administrador`).

---

## 3. Contrato de Endpoints Esperados do Backend (Integração com Aughusto)

Para substituir o fallback local (`static/js/api.js`) pelos dados reais do PostgreSQL, o backend Flask deve responder em JSON nos seguintes endpoints:

* `GET /health` — Status da API
* `GET /api/dashboard` — Contadores gerenciais (`profissionaisAtivos`, `disponiveisAgora`, `jornadasAtivas`, `escalasDoDia`, `conflitosPendentes`, `certificacoesAVencer`)
* `GET / POST /api/employees` — Listagem e cadastro de profissionais (`UC01`)[cite: 2, 7]
* `GET / POST /api/roles` — Listagem e cadastro de cargos e requisitos de certificação[cite: 2]
* `GET /api/certifications` — Listagem de certificações e validades (`UC02`)[cite: 2, 7]
* `GET /api/availabilities` — Janelas de disponibilidade (`UC03`)[cite: 2, 7]
* `GET / POST /api/shifts` — Turnos operacionais (`UC04`)[cite: 2, 7]
* `GET / POST /api/schedules` — Escalas planejadas (`UC05`)[cite: 2, 7]
* `POST /api/allocations/validate` — Validação das regras (`UC06`, `UC07`, `UC09`)[cite: 7]
* `POST /api/allocations` — Confirmação da escala e disparo do evento `MotoristaEscalado` (`UC08`)[cite: 7]
* `GET /api/conflicts` — Lista de conflitos e alertas ativos (`UC09`)[cite: 2, 7]