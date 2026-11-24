# Diagramas BPM / BPMN — SIG-Log People (Squad 05)

Documentação visual dos processos de negócio de **RH, Jornada & Escalonamento**, alinhada aos Casos de Uso (`UC01` a `UC10`) e ao Motor de Regras do Anexo A.

---

## 1. Processo BPMN: Alocação de Motorista e Validação de Regras (UC06, UC07, UC08, UC09)

```mermaid
flowchart TD
    Start((Início: Solicitação de Escala)) --> SelectDriver[Gestor seleciona Motorista/Operador e Turno]
    SelectDriver --> CheckAvail{Motorista está disponível?<br/>UC03}
    
    CheckAvail -- Não --> ConflictAvail[Registrar Conflito: Indisponível<br/>UC09]
    CheckAvail -- Sim --> CheckCert{Certificação compatível<br/>e válida? UC02}
    
    CheckCert -- Não --> ConflictCert[Registrar Conflito: Certificação Inválida<br/>UC09]
    CheckCert -- Sim --> CheckRest{Descanso mínimo<br/>cumprido? UC07}
    
    CheckRest -- Não --> ConflictRest[Registrar Conflito: Descanso Insuficiente<br/>UC09]
    CheckRest -- Sim --> CheckShift{Jornada dentro do<br/>limite legal? UC06}
    
    CheckShift -- Não --> ConflictShift[Registrar Conflito: Excesso de Jornada<br/>UC09]
    CheckShift -- Sim --> Approve[Confirmar Alocação na Escala<br/>UC08]
    
    ConflictAvail --> EmitConflict([Evento: ConflitoDeJornadaDetectado])
    ConflictCert --> EmitConflict
    ConflictRest --> EmitConflict
    ConflictShift --> EmitConflict
    EmitConflict --> NotifyUI[Exibir Alerta de Bloqueio na UI]
    NotifyUI --> EndBlock((Fim: Alocação Bloqueada))
    
    Approve --> EmitEvent([Evento RabbitMQ: MotoristaEscalado])
    EmitEvent --> NotifyFleet[Squad Fleet consome alocação]
    NotifyFleet --> EndOk((Fim: Escala Confirmada))

    flowchart LR
    subgraph RH [Analista de RH / Gestor]
        A((Início)) --> B[Cadastrar Funcionário<br/>Motorista / Operador - UC01]
        B --> C[Vincular Cargo e Perfil]
        C --> D[Registrar Certificações<br/>e Validades - UC02]
        D --> E[Definir Janelas de<br/>Disponibilidade - UC03]
    end

    subgraph Planejamento [Planejamento Operacional]
        E --> F[Criar Turnos Padrão - UC04]
        F --> G[Montar Grade de Escala - UC05]
        G --> H((Pronto para Alocação))
    end

sequenceDiagram
    actor M as Motorista / Operador
    participant UI as Frontend (SIG-Log People)
    participant API as Backend Flask (Motor de Regras)
    participant MQ as RabbitMQ (Eventos)

    M->>UI: Inicia turno na escala (UC10)
    UI->>API: POST /journeys/start
    API->>MQ: Publica evento JornadaIniciada
    API-->>UI: Status: Em Jornada (Timer ativo)

    M->>UI: Finaliza turno / Registra parada
    UI->>API: POST /journeys/finish
    API->>API: Calcula tempo mínimo de interjornada (UC07)
    API->>MQ: Publica evento JornadaFinalizada + DescansoRegistrado
    API-->>UI: Bloqueia novas alocações até fim do descanso


---

### Passo 2: Referenciar os diagramas no `README.md`
1. Abra o arquivo **`README.md`** na raiz do projeto[cite: 15].
2. Adicione no final dele esta seção (e salve com `Ctrl + S`):

```markdown
## Diagramas de Processos (BPM / BPMN)
Os fluxos de negócio de alocação, validação de jornada/descanso, gestão de escalas e eventos integrados com o ecossistema SIG-Log estão documentados em:
- [Diagramas BPMN — RH, Jornada & Escalonamento](docs/14_diagramas_bpmn.md)