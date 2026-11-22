
-- =====================================================
-- JORNADALOG SIG 4.1 PEOPLE
-- MIGRATION 000 - CONTROLE DE VERSOES
-- =====================================================

CREATE TABLE controle_migrations (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    versao VARCHAR(50) NOT NULL UNIQUE,
    nome_arquivo VARCHAR(255) NOT NULL,
    aplicado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
