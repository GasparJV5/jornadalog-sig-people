// Motor de dados locais (Fallback automático quando a API Flask estiver offline)
const mockDB = {
  roles: [
    { id: 1, code: 'MOT-CAR', name: 'Motorista Carreteiro (Bitrem/Rodotrem)', cbo: '7825-10', req_cert: 'CNH E + MOPP + Direção Defensiva', min_rest_h: 11, active_count: 14 },
    { id: 2, code: 'MOT-URB', name: 'Motorista de Distribuição Urbana (VUC/Toco)', cbo: '7825-05', req_cert: 'CNH C/D + Direção Defensiva', min_rest_h: 11, active_count: 22 },
    { id: 3, code: 'OP-EMP', name: 'Operador de Empilhadeira e Movimentação', cbo: '7822-20', req_cert: 'NR-11 (Movimentação de Cargas)', min_rest_h: 11, active_count: 18 },
    { id: 4, code: 'OP-LOG', name: 'Operador Logístico de Docas / Conferência', cbo: '4141-05', req_cert: 'NR-35 (Trabalho em Altura - Opcional)', min_rest_h: 11, active_count: 30 }
  ],
  employees: [
    { id: 1, name: 'Carlos Eduardo Silva', registration: 'MAT-1042', profile: 'MOTORISTA', role_name: 'Motorista Carreteiro', unit: 'CD Recife - BR-101', active: true, available: true, cert_ok: true, rest_hours: 14 },
    { id: 2, name: 'Mariana Souza Costa', registration: 'MAT-1089', profile: 'OPERADOR', role_name: 'Operador de Empilhadeira', unit: 'CD Recife - BR-101', active: true, available: true, cert_ok: true, rest_hours: 12 },
    { id: 3, name: 'Roberto Alves Pereira', registration: 'MAT-1104', profile: 'MOTORISTA', role_name: 'Motorista Carreteiro', unit: 'Hub Jaboatão', active: true, available: true, cert_ok: false, rest_hours: 15, block_reason: 'Certificação MOPP vencida há 5 dias' },
    { id: 4, name: 'Fernanda Lima Santos', registration: 'MAT-1120', profile: 'MOTORISTA', role_name: 'Motorista Distribuição Urbana', unit: 'CD Recife - BR-101', active: true, available: true, cert_ok: true, rest_hours: 7, block_reason: 'Descanso interjornada insuficiente (7h cumpridas de 11h obrigatórias)' },
    { id: 5, name: 'Thiago Mendes Rocha', registration: 'MAT-1155', profile: 'OPERADOR', role_name: 'Operador Logístico de Docas', unit: 'Hub Suape', active: true, available: false, cert_ok: true, rest_hours: 24, block_reason: 'Profissional em período de folga/indisponibilidade programada' }
  ],
  certifications: [
    { employee_name: 'Carlos Eduardo Silva', type: 'MOPP - Cargas Perigosas', code: 'DETRAN-PE-9981', expires_at: '2027-08-15', status: 'VALIDA' },
    { employee_name: 'Mariana Souza Costa', type: 'NR-11 Empilhadeira', code: 'SENAI-4410', expires_at: '2027-03-10', status: 'VALIDA' },
    { employee_name: 'Roberto Alves Pereira', type: 'MOPP - Cargas Perigosas', code: 'DETRAN-PE-7721', expires_at: '2026-11-17', status: 'VENCIDA' },
    { employee_name: 'Fernanda Lima Santos', type: 'Direção Defensiva', code: 'SEST-SENAT-302', expires_at: '2026-12-05', status: 'A VENCER' }
  ],
  availabilities: [
    { employee_name: 'Carlos Eduardo Silva', start_at: '2026-11-23T06:00:00', end_at: '2026-11-23T18:00:00', kind: 'DISPONIVEL' },
    { employee_name: 'Mariana Souza Costa', start_at: '2026-11-23T06:00:00', end_at: '2026-11-23T14:20:00', kind: 'DISPONIVEL' },
    { employee_name: 'Thiago Mendes Rocha', start_at: '2026-11-22T00:00:00', end_at: '2026-11-24T23:59:00', kind: 'INDISPONIVEL (FOLGA)' }
  ],
  shifts: [
    { id: 1, code: 'TRN-A', name: 'Turno A · Manhã Logística', unit: 'CD Recife - BR-101', start_time: '06:00', end_time: '14:20', required_count: 6, status: 'ATIVO' },
    { id: 2, code: 'TRN-B', name: 'Turno B · Tarde Expedição', unit: 'CD Recife - BR-101', start_time: '14:00', end_time: '22:20', required_count: 6, status: 'ATIVO' },
    { id: 3, code: 'TRN-C', name: 'Turno C · Madrugada Transferência', unit: 'Hub Suape', start_time: '22:00', end_time: '06:00', required_count: 4, status: 'ATIVO' }
  ],
  schedules: [
    { id: 1, schedule_date: '2026-11-23', shift_name: 'Turno A · Manhã Logística', start_time: '06:00', end_time: '14:20', required_count: 6, allocated_count: 6, status: 'COBERTA' },
    { id: 2, schedule_date: '2026-11-23', shift_name: 'Turno B · Tarde Expedição', start_time: '14:00', end_time: '22:20', required_count: 6, allocated_count: 4, status: 'PENDENTE (2 VAGAS)' },
    { id: 3, schedule_date: '2026-11-24', shift_name: 'Turno C · Madrugada Transferência', start_time: '22:00', end_time: '06:00', required_count: 4, allocated_count: 3, status: 'PENDENTE (1 VAGA)' }
  ],
  conflicts: [
    { severity: 'CRITICA', type: 'CERTIFICACAO_VENCIDA', employee_name: 'Roberto Alves Pereira', description: 'MOPP vencido bloqueia escalonamento em transporte de carga.', status: 'BLOQUEADO' },
    { severity: 'ALTA', type: 'DESCANSO_INSUFICIENTE', employee_name: 'Fernanda Lima Santos', description: 'Apenas 7h de interjornada cumpridas (mínimo legal: 11h).', status: 'EM DESCANSO' },
    { severity: 'ALTA', type: 'COBERTURA_INCOMPLETA', employee_name: 'Turno B · Tarde', description: 'Faltam 2 motoristas aptos para fechar a escala de 23/11.', status: 'ABERTO' }
  ]
};

export let isDemoMode = false;

function handleMock(url, options = {}) {
  const method = (options.method || 'GET').toUpperCase();
  const body = options.body ? JSON.parse(options.body) : {};

  if (url === '/api/dashboard') {
    return {
      profissionaisAtivos: mockDB.employees.filter(e => e.active).length,
      disponiveisAgora: mockDB.employees.filter(e => e.available && e.cert_ok && e.rest_hours >= 11).length,
      jornadasAtivas: 3,
      escalasDoDia: mockDB.schedules.length,
      conflitosPendentes: mockDB.conflicts.length,
      certificacoesAVencer: mockDB.certifications.filter(c => c.status !== 'VALIDA').length
    };
  }
  if (url === '/api/roles') {
    if (method === 'POST') {
      const novo = { id: Date.now(), ...body, active_count: 0 };
      mockDB.roles.push(novo);
      return novo;
    }
    return mockDB.roles;
  }
  if (url === '/api/employees') {
    if (method === 'POST') {
      const novo = { id: Date.now(), ...body, active: true, available: true, cert_ok: true, rest_hours: 12 };
      mockDB.employees.push(novo);
      return novo;
    }
    return mockDB.employees;
  }
  if (url === '/api/certifications') return mockDB.certifications;
  if (url === '/api/availabilities') return mockDB.availabilities;
  if (url === '/api/shifts') {
    if (method === 'POST') {
      const novo = { id: Date.now(), ...body, status: 'ATIVO' };
      mockDB.shifts.push(novo);
      return novo;
    }
    return mockDB.shifts;
  }
  if (url === '/api/schedules') {
    if (method === 'POST') {
      const novo = { id: Date.now(), ...body, allocated_count: 0, status: `PENDENTE (${body.required_count} VAGAS)` };
      mockDB.schedules.push(novo);
      return novo;
    }
    return mockDB.schedules;
  }
  if (url === '/api/conflicts' || url === '/api/notifications') return mockDB.conflicts;
  if (url === '/api/allocations/validate') {
    const emp = mockDB.employees.find(e => e.id === Number(body.employeeId)) || mockDB.employees[0];
    const validacoes = [
      { regra: 'UC03 · Disponibilidade no período', status: emp.available ? 'APROVADO' : 'REPROVADO', motivo: emp.available ? 'Profissional disponível na janela.' : 'Profissional marcado como indisponível/folga.' },
      { regra: 'UC02 · Certificação e habilitação válida', status: emp.cert_ok ? 'APROVADO' : 'REPROVADO', motivo: emp.cert_ok ? 'Certificações obrigatórias em dia.' : emp.block_reason },
      { regra: 'UC07 · Descanso mínimo interjornada (11h)', status: emp.rest_hours >= 11 ? 'APROVADO' : 'REPROVADO', motivo: emp.rest_hours >= 11 ? `${emp.rest_hours}h de descanso cumpridas.` : `Apenas ${emp.rest_hours}h cumpridas (mínimo 11h).` }
    ];
    const apto = validacoes.every(v => v.status === 'APROVADO');
    return { resultado: apto ? 'APTO' : 'BLOQUEADO', validacoes };
  }
  if (url === '/api/allocations') return { ok: true };
  return [];
}

export async function api(url, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 1800);
  try {
    const response = await fetch(url, {
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      ...options
    });
    const contentType = response.headers.get('content-type') || '';
    if (!contentType.includes('application/json')) throw new Error('Servidor estático sem API');
    const data = await response.json();
    if (!response.ok) throw new Error(data.erro || 'Não foi possível concluir a operação.');
    isDemoMode = false;
    return data;
  } catch (err) {
    isDemoMode = true;
    return handleMock(url, options);
  } finally {
    clearTimeout(timer);
  }
}