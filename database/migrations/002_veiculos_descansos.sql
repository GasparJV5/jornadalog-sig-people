-- =====================================================
-- JORNALOG SIG 4.1 PEOPLE
-- MIGRATION 002 - VEICULOS E DESCANSOS
-- SGBD: PostgreSQL 18
-- =====================================================

-- 1. VEICULOS
CREATE TABLE veiculos (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    placa VARCHAR(10) NOT NULL UNIQUE,
    modelo VARCHAR(100) NOT NULL,
    marca VARCHAR(100),
    ano INTEGER,
    status VARCHAR(20) NOT NULL DEFAULT 'DISPONIVEL',

    CONSTRAINT veiculos_status_check
        CHECK (status IN (
            'DISPONIVEL',
            'EM_USO',
            'MANUTENCAO',
            'INATIVO'
        )),

    CONSTRAINT veiculos_ano_check
        CHECK (ano IS NULL OR ano > 0)
);

-- 2. DESCANSOS
CREATE TABLE descansos (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    funcionario_id BIGINT NOT NULL
        REFERENCES funcionarios(id),

    inicio_descanso TIMESTAMP NOT NULL,
    fim_descanso TIMESTAMP NOT NULL,
    observacoes TEXT,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT descansos_periodo_check
        CHECK (fim_descanso > inicio_descanso)
);

-- Índice para consultas de descanso por funcionário
CREATE INDEX idx_descansos_funcionario
    ON descansos(funcionario_id);