
# DER — JornadaLog SIG 4.1 People

## 1. Objetivo

Este documento apresenta o Diagrama Entidade-Relacionamento (DER) do banco de dados RH_Jornada, desenvolvido em PostgreSQL 18.

O banco gerencia funcionários, cargos, certificações, disponibilidades, turnos, escalas e registros de jornada.

## 2. Diagrama Entidade-Relacionamento

```mermaid
erDiagram
    CARGOS ||--o{ FUNCIONARIOS : possui
    FUNCIONARIOS ||--o{ FUNCIONARIO_CERTIFICACOES : possui
    CERTIFICACOES ||--o{ FUNCIONARIO_CERTIFICACOES : identifica
    FUNCIONARIOS ||--o{ DISPONIBILIDADES : informa
    TURNOS ||--o{ ESCALAS : define
    ESCALAS ||--o{ ALOCACOES : contem
    FUNCIONARIOS ||--o{ ALOCACOES : recebe
    ALOCACOES ||--o{ REGISTROS_JORNADA : gera

    CARGOS {
        bigint id PK
        varchar nome UK
        text descricao
        boolean ativo
    }

    FUNCIONARIOS {
        bigint id PK
        varchar matricula UK
        varchar nome
        varchar email UK
        bigint cargo_id FK
        date data_admissao
        varchar status
    }

    CERTIFICACOES {
        bigint id PK
        varchar nome UK
        text descricao
        boolean obrigatoria
    }

    FUNCIONARIO_CERTIFICACOES {
        bigint id PK
        bigint funcionario_id FK
        bigint certificacao_id FK
        varchar numero_certificado
        date emitida_em
        date validade_ate
        varchar status
    }

    DISPONIBILIDADES {
        bigint id PK
        bigint funcionario_id FK
        smallint dia_semana
        time hora_inicio
        time hora_fim
        date vigencia_inicio
        date vigencia_fim
    }

    TURNOS {
        bigint id PK
        varchar nome UK
        time hora_inicio
        time hora_fim
        integer intervalo_minutos
        boolean ativo
    }

    ESCALAS {
        bigint id PK
        date data_escala
        bigint turno_id FK
        varchar setor
        varchar status
    }

    ALOCACOES {
        bigint id PK
        bigint escala_id FK
        bigint funcionario_id FK
        time hora_inicio
        time hora_fim
        varchar status
    }

    REGISTROS_JORNADA {
        bigint id PK
        bigint alocacao_id FK
        timestamp entrada_real
        timestamp saida_real
        integer intervalo_minutos
    }

    OUTBOX_EVENTOS {
        bigint id PK
        varchar tipo_evento
        bigint agregado_id
        jsonb payload
        varchar status
        timestamp criado_em
    }
```

## 3. Descrição dos relacionamentos

- Cargos e Funcionários: um cargo pode estar associado a vários funcionários.
- Funcionários e Certificações: relacionamento intermediado pela tabela funcionario_certificacoes.
- Funcionários e Disponibilidades: um funcionário pode possuir várias disponibilidades.
- Turnos e Escalas: um turno pode ser utilizado em várias escalas.
- Escalas e Alocações: uma escala pode conter várias alocações.
- Funcionários e Alocações: um funcionário pode possuir várias alocações.
- Alocações e Registros de Jornada: uma alocação pode possuir vários registros de jornada.

## 4. Tabela de eventos

A tabela outbox_eventos armazena eventos que serão enviados futuramente ao RabbitMQ. O campo agregado_id identifica o registro relacionado ao evento, sem possuir uma chave estrangeira direta.

## 5. SGBD

- Sistema gerenciador: PostgreSQL
- Versão: 18
- Banco de dados: RH_Jornada
