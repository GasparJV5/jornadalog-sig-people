
-- =====================================================
-- JORNADALOG SIG 4.1 PEOPLE
-- DADOS INICIAIS DO BANCO RH_Jornada
-- =====================================================

-- 1. CARGOS

INSERT INTO cargos (nome, descricao) VALUES
('Motorista', 'Responsavel pela conducao dos veiculos'),
('Operador', 'Responsavel pelas operacoes logisticas'),
('Supervisor', 'Responsavel pela supervisao da equipe'),
('Auxiliar', 'Apoio nas atividades operacionais')
ON CONFLICT (nome) DO NOTHING;


-- 2. CERTIFICACOES

INSERT INTO certificacoes (nome, descricao, obrigatoria) VALUES
('CNH', 'Carteira Nacional de Habilitacao', TRUE),
('Curso de Direcao Defensiva', 'Capacitacao em direcao defensiva', FALSE),
('Operacao de Equipamentos', 'Capacitacao para operacao de equipamentos', FALSE)
ON CONFLICT (nome) DO NOTHING;


-- 3. TURNOS

INSERT INTO turnos (
    nome,
    hora_inicio,
    hora_fim,
    intervalo_minutos
) VALUES
('Manha', '06:00', '14:00', 60),
('Tarde', '14:00', '22:00', 60),
('Noite', '22:00', '06:00', 60)
ON CONFLICT (nome) DO NOTHING;
