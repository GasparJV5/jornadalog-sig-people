-- =====================================================
-- JORNADALOG SIG 4.1 PEOPLE
-- MIGRATION 003 - REQUISITOS DE ALOCACAO (PROPOSTA DO BACKEND)
-- SGBD: PostgreSQL 18
--
-- Apenas ADICIONA colunas/tabelas; nao altera nem remove nada das migrations 001 e 002.
-- Para aplicar: copiar para database/migrations/ e rodar executar_migrations.py.
-- =====================================================

-- 1. ALOCACOES: veiculo e viagem (necessarios para o evento MotoristaEscalado, consumido pelo Fleet)
ALTER TABLE alocacoes
    ADD COLUMN veiculo_id BIGINT REFERENCES veiculos(id),
    ADD COLUMN viagem_id VARCHAR(50);

CREATE INDEX idx_alocacoes_veiculo
    ON alocacoes(veiculo_id);

-- 2. VEICULOS: categoria de CNH exigida para conduzir
ALTER TABLE veiculos
    ADD COLUMN cnh_exigida CHAR(1) NOT NULL DEFAULT 'C'
        CONSTRAINT veiculos_cnh_exigida_check
        CHECK (cnh_exigida IN ('A', 'B', 'C', 'D', 'E'));

-- 3. VEICULOS x CERTIFICACOES EXIGIDAS (ex.: MOPP para produtos perigosos)
CREATE TABLE veiculo_certificacoes_exigidas (
    veiculo_id BIGINT NOT NULL
        REFERENCES veiculos(id) ON DELETE CASCADE,
    certificacao_id BIGINT NOT NULL
        REFERENCES certificacoes(id),
    PRIMARY KEY (veiculo_id, certificacao_id)
);

-- 4. FUNCIONARIOS: CPF e categoria da CNH (o tipo motorista/operador vem do cargo)
ALTER TABLE funcionarios
    ADD COLUMN cpf VARCHAR(11) UNIQUE,
    ADD COLUMN cnh_categoria CHAR(1)
        CONSTRAINT funcionarios_cnh_categoria_check
        CHECK (cnh_categoria IS NULL OR cnh_categoria IN ('A', 'B', 'C', 'D', 'E'));
