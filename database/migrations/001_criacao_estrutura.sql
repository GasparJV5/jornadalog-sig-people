
-- =====================================================
-- JORNADALOG SIG 4.1 PEOPLE
-- MIGRATION 001 - CRIACAO DA ESTRUTURA INICIAL
-- SGBD: PostgreSQL 18
-- =====================================================

-- 1. CARGOS
CREATE TABLE cargos (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome VARCHAR(100) NOT NULL UNIQUE,
    descricao TEXT,
    ativo BOOLEAN NOT NULL DEFAULT TRUE
);

-- 2. FUNCIONARIOS
CREATE TABLE funcionarios (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    matricula VARCHAR(30) NOT NULL UNIQUE,
    nome VARCHAR(150) NOT NULL,
    email VARCHAR(150) UNIQUE,
    telefone VARCHAR(20),
    cargo_id BIGINT NOT NULL REFERENCES cargos(id),
    data_admissao DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ATIVO'
        CHECK (status IN ('ATIVO', 'INATIVO', 'AFASTADO')),
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 3. CERTIFICACOES
CREATE TABLE certificacoes (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome VARCHAR(120) NOT NULL UNIQUE,
    descricao TEXT,
    obrigatoria BOOLEAN NOT NULL DEFAULT FALSE
);

-- 4. CERTIFICACOES DOS FUNCIONARIOS
CREATE TABLE funcionario_certificacoes (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    funcionario_id BIGINT NOT NULL
        REFERENCES funcionarios(id) ON DELETE CASCADE,
    certificacao_id BIGINT NOT NULL
        REFERENCES certificacoes(id),
    numero_certificado VARCHAR(80),
    emitida_em DATE,
    validade_ate DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'VALIDA'
        CHECK (status IN ('VALIDA', 'VENCIDA', 'SUSPENSA')),
    UNIQUE (funcionario_id, certificacao_id, numero_certificado),
    CHECK (
        validade_ate IS NULL OR emitida_em IS NULL
        OR validade_ate >= emitida_em
    )
);

-- 5. DISPONIBILIDADES
CREATE TABLE disponibilidades (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    funcionario_id BIGINT NOT NULL
        REFERENCES funcionarios(id) ON DELETE CASCADE,
    dia_semana SMALLINT NOT NULL
        CHECK (dia_semana BETWEEN 0 AND 6),
    hora_inicio TIME NOT NULL,
    hora_fim TIME NOT NULL,
    vigencia_inicio DATE NOT NULL,
    vigencia_fim DATE,
    disponivel BOOLEAN NOT NULL DEFAULT TRUE,
    CHECK (hora_fim > hora_inicio),
    CHECK (
        vigencia_fim IS NULL OR vigencia_fim >= vigencia_inicio
    )
);

-- 6. TURNOS
CREATE TABLE turnos (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome VARCHAR(80) NOT NULL UNIQUE,
    hora_inicio TIME NOT NULL,
    hora_fim TIME NOT NULL,
    intervalo_minutos INTEGER NOT NULL DEFAULT 0
        CHECK (intervalo_minutos >= 0),
    descricao TEXT,
    ativo BOOLEAN NOT NULL DEFAULT TRUE
);

-- 7. ESCALAS
CREATE TABLE escalas (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    data_escala DATE NOT NULL,
    turno_id BIGINT NOT NULL REFERENCES turnos(id),
    setor VARCHAR(100),
    local_trabalho VARCHAR(150),
    status VARCHAR(20) NOT NULL DEFAULT 'RASCUNHO'
        CHECK (status IN (
            'RASCUNHO', 'PUBLICADA', 'CANCELADA', 'CONCLUIDA'
        )),
    observacoes TEXT,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 8. ALOCACOES
CREATE TABLE alocacoes (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    escala_id BIGINT NOT NULL
        REFERENCES escalas(id) ON DELETE CASCADE,
    funcionario_id BIGINT NOT NULL
        REFERENCES funcionarios(id),
    funcao_exercida VARCHAR(100),
    hora_inicio TIME,
    hora_fim TIME,
    status VARCHAR(20) NOT NULL DEFAULT 'PLANEJADA'
        CHECK (status IN (
            'PLANEJADA', 'CONFIRMADA', 'CANCELADA', 'CONCLUIDA'
        )),
    observacoes TEXT,
    UNIQUE (escala_id, funcionario_id),
    CHECK (
        hora_inicio IS NULL OR hora_fim IS NULL
        OR hora_inicio <> hora_fim
    )
);

-- 9. REGISTROS DE JORNADA
CREATE TABLE registros_jornada (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    alocacao_id BIGINT NOT NULL
        REFERENCES alocacoes(id) ON DELETE CASCADE,
    entrada_real TIMESTAMP,
    saida_real TIMESTAMP,
    intervalo_minutos INTEGER NOT NULL DEFAULT 0
        CHECK (intervalo_minutos >= 0),
    observacoes TEXT,
    CHECK (
        entrada_real IS NULL OR saida_real IS NULL
        OR saida_real > entrada_real
    )
);

-- 10. OUTBOX DE EVENTOS
CREATE TABLE outbox_eventos (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tipo_evento VARCHAR(120) NOT NULL,
    agregado_id BIGINT NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDENTE'
        CHECK (status IN ('PENDENTE', 'PROCESSADO', 'ERRO')),
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processado_em TIMESTAMP,
    tentativas INTEGER NOT NULL DEFAULT 0
        CHECK (tentativas >= 0),
    erro TEXT
);

-- INDICES
CREATE INDEX idx_funcionarios_cargo
    ON funcionarios(cargo_id);

CREATE INDEX idx_cert_funcionario
    ON funcionario_certificacoes(funcionario_id);

CREATE INDEX idx_disp_funcionario_dia
    ON disponibilidades(funcionario_id, dia_semana);

CREATE INDEX idx_escalas_data
    ON escalas(data_escala);

CREATE INDEX idx_alocacoes_funcionario
    ON alocacoes(funcionario_id);

CREATE INDEX idx_jornada_alocacao
    ON registros_jornada(alocacao_id);

CREATE INDEX idx_outbox_pendentes
    ON outbox_eventos(status, criado_em);
