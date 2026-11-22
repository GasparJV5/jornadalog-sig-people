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