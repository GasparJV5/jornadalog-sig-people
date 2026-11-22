import { api, isDemoMode } from './api.js';

const $ = s => document.querySelector(s);
let state = { page: 'dashboard', role: 'GESTOR_OPERACOES', data: {} };

const menu = [
  ['dashboard', '▦', 'Visão Geral', []],
  ['people', '♙', 'Pessoas', [
    ['people', 'Profissionais'],
    ['roles', 'Cargos e Perfis'],
    ['certifications', 'Certificações'],
    ['documents', 'Documentos e currículos']
  ]],
  ['planning', '◇', 'Planejamento', [
    ['availabilities', 'Disponibilidades'],
    ['shifts', 'Turnos'],
    ['schedules', 'Escalas']
  ]],
  ['operation', '◷', 'Operação', [
    ['allocations', 'Alocações'],
    ['journeys', 'Jornadas'],
    ['rests', 'Descansos']
  ]],
  ['control', '⚠', 'Controle', [
    ['conflicts', 'Conflitos e alertas'],
    ['vehicles', 'Veículos'],
    ['history', 'Histórico']
  ]],
  ['intelligence', '▤', 'Inteligência', [
    ['indicators', 'Indicadores'],
    ['reports', 'Relatórios'],
    ['audit', 'Auditoria']
  ]],
  ['settings', '⚙', 'Configurações', [
    ['parameters', 'Parâmetros'],
    ['users', 'Usuários e permissões'],
    ['about', 'Sobre o sistema']
  ]]
];

const roleAllowed = {
  PROFISSIONAL: ['dashboard', 'availabilities', 'certifications', 'schedules', 'journeys', 'rests', 'documents'],
  OPERADOR: ['dashboard', 'schedules', 'allocations', 'journeys', 'conflicts'],
  GESTOR_RH: ['dashboard', 'people', 'roles', 'certifications', 'documents', 'availabilities', 'indicators', 'reports'],
  GESTOR_OPERACOES: ['dashboard', 'people', 'roles', 'availabilities', 'shifts', 'schedules', 'allocations', 'journeys', 'rests', 'conflicts', 'vehicles', 'indicators', 'reports'],
  ADMIN: ['dashboard', 'people', 'roles', 'certifications', 'documents', 'availabilities', 'shifts', 'schedules', 'allocations', 'journeys', 'rests', 'conflicts', 'vehicles', 'history', 'indicators', 'reports', 'audit', 'parameters', 'users', 'about']
};

function allowed(p) { return roleAllowed[state.role].includes(p); }

function renderNav() {
  nav.innerHTML = menu.map(([id, ic, label, subs]) => {
    if (!subs.length) return `<div class="nav-group"><button class="nav-title ${state.page === id ? 'active' : ''}" data-page="${id}"><span>${ic} ${label}</span></button></div>`;
    const visible = subs.filter(x => allowed(x[0]));
    if (!visible.length) return '';
    return `<div class="nav-group ${visible.some(x => x[0] === state.page) ? 'open' : ''}">
      <button class="nav-title"><span>${ic} ${label}</span><span>⌄</span></button>
      <div class="subnav">${visible.map(([p, l]) => `<button class="${state.page === p ? 'active' : ''}" data-page="${p}">${l}${p === 'conflicts' ? '<span class="badge">!</span>' : ''}</button>`).join('')}</div>
    </div>`;
  }).join('');
  nav.querySelectorAll('.nav-title:not([data-page])').forEach(b => b.onclick = () => b.parentElement.classList.toggle('open'));
  nav.querySelectorAll('[data-page]').forEach(b => b.onclick = () => go(b.dataset.page));
}

function go(page) {
  if (!allowed(page)) {
    toast('Heurística de Prevenção: O perfil atual não possui permissão para esta área.');
    return;
  }
  state.page = page;
  renderNav();
  render();
  sidebar.classList.remove('open');
}

const titleEl = $('#title'), eyebrow = $('#eyebrow');
function title(t, e = 'SIG-LOG PEOPLE') { titleEl.textContent = t; eyebrow.textContent = e; }

function toast(msg) {
  const d = document.createElement('div');
  d.className = 'toast';
  d.textContent = msg;
  $('#toast').append(d);
  setTimeout(() => d.remove(), 3800);
}

function loading() {
  content.innerHTML = '<section class="panel empty">Sincronizando dados operacionais...</section>';
}

async function render() {
  loading();
  const pages = {
    dashboard, people, roles, certifications, availabilities, shifts, schedules, allocations, conflicts, about
  };
  if (pages[state.page]) return pages[state.page]();
  generic(state.page);
}

async function dashboard() {
  title('Visão Geral', 'NÍVEL GERENCIAL');
  const d = await api('/api/dashboard');
  content.innerHTML = `
    <section class="hero">
      <div>
        <small>CICLO INTEGRADO DO PROFISSIONAL</small>
        <h2>Jornada, disponibilidade e escalonamento em um só fluxo</h2>
        <p>O SIG-Log People transforma cadastros, cargos, certificações e escalas em decisões operacionais rastreáveis e seguras.</p>
        <div class="hero-actions">
          <button class="secondary" data-go="schedules">＋ Criar escala</button>
          <button class="secondary" data-go="allocations">✓ Validar alocação</button>
          <button class="secondary" data-go="roles">⚙ Gerir cargos</button>
        </div>
      </div>
      <aside class="alert-panel">
        <small>ALERTA GERENCIAL · PREVENÇÃO DE RISCO</small>
        <h3>Turno B sem cobertura completa</h3>
        <p>Existem posições pendentes e 2 profissionais com bloqueio preventivo (MOPP vencido / Descanso &lt; 11h).</p>
        <button class="secondary" data-go="conflicts">Analisar conflitos</button>
      </aside>
    </section>
    <section class="cards">
      ${card('Profissionais ativos', d.profissionaisAtivos, 'people')}
      ${card('Aptos e disponíveis', d.disponiveisAgora, 'availabilities')}
      ${card('Jornadas ativas', d.jornadasAtivas, 'journeys')}
      ${card('Escalas do dia', d.escalasDoDia, 'schedules')}
      ${card('Conflitos pendentes', d.conflitosPendentes, 'conflicts')}
      ${card('Certificações em alerta', d.certificacoesAVencer, 'certifications')}
    </section>
    <section class="panel">
      <h2>Ciclo operacional do JornadaLog (UC01 a UC10)</h2>
      <div class="steps">
        ${[
          ['people', '1. Cadastrar', 'Pessoa e cargo'],
          ['certifications', '2. Qualificar', 'Certificações'],
          ['availabilities', '3. Disponibilizar', 'Janelas livres'],
          ['schedules', '4. Planejar', 'Turnos e escalas'],
          ['allocations', '5. Operar', 'Validar alocação'],
          ['conflicts', '6. Controlar', 'Descanso e alertas']
        ].map(x => `<button class="step" data-go="${x[0]}"><b>${x[1]}</b><small>${x[2]}</small></button>`).join('')}
      </div>
    </section>
    <section class="grid2">
      <div class="panel">
        <h2>Cobertura das escalas</h2>
        ${bar('Turno A · Manhã', 100)}
        ${bar('Turno B · Tarde', 67)}
        ${bar('Turno C · Madrugada', 75)}
        ${bar('Operação especial', 90)}
      </div>
      <div class="panel">
        <h2>Fila de decisões rápidas</h2>
        <div class="queue-item"><span class="pill red">BLOQUEIO PREVENTIVO</span><b> Roberto Alves · MOPP Vencido</b><p>Sistema impede escalonamento automático até renovação.</p></div>
        <div class="queue-item"><span class="pill amber">DESCANSO LEGAL</span><b> Fernanda Lima · 7h de 11h cumpridas</b><p>Liberação prevista após completar interjornada mínima.</p></div>
      </div>
    </section>`;
  bindGo();
}

function card(l, v, p) { return `<article class="card" data-go="${p}"><small>${l}</small><strong>${v}</strong><em>Abrir módulo →</em></article>`; }
function bar(l, v) { return `<div class="bar-row"><span>${l}</span><div class="bar"><span style="width:${v}%"></span></div><b>${v}%</b></div>`; }
function bindGo() { content.querySelectorAll('[data-go]').forEach(x => x.onclick = () => go(x.dataset.go)); }

async function people() {
  title('Profissionais', 'PESSOAS · UC01');
  const data = await api('/api/employees');
  content.innerHTML = `
    <section class="panel">
      <div class="toolbar">
        <div>
          <input id="filter" placeholder="Pesquisar nome, matrícula ou unidade">
          <select id="profileFilter">
            <option value="">Todos os perfis</option>
            <option value="MOTORISTA">MOTORISTA</option>
            <option value="OPERADOR">OPERADOR</option>
          </select>
        </div>
        <button class="primary" id="newEmployee">＋ Cadastrar profissional</button>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Nome</th><th>Matrícula</th><th>Perfil / Cargo</th><th>Unidade</th><th>Aptidão Operacional</th><th>Situação</th></tr></thead>
          <tbody id="peopleRows">${peopleRows(data)}</tbody>
        </table>
      </div>
    </section>`;
  const peopleRowsEl = $('#peopleRows');
  const apply = () => {
    const q = filter.value.toLowerCase(), p = profileFilter.value;
    peopleRowsEl.innerHTML = peopleRows(data.filter(x =>
      (x.name.toLowerCase().includes(q) || x.registration.toLowerCase().includes(q) || (x.unit || '').toLowerCase().includes(q)) &&
      (!p || x.profile === p)
    ));
  };
  filter.oninput = apply;
  profileFilter.onchange = apply;
  newEmployee.onclick = employeeModal;
}

function peopleRows(data) {
  return data.length ? data.map(x => {
    const apto = x.available !== false && x.cert_ok !== false && (x.rest_hours ?? 12) >= 11;
    const statusBadge = apto
      ? '<span class="pill green">✓ APTO PARA ESCALA</span>'
      : `<span class="pill amber" title="${x.block_reason || 'Verificar pendência'}">⚠ ${x.block_reason || 'RESTRIÇÃO ATIVA'}</span>`;
    return `<tr>
      <td><b>${x.name}</b></td>
      <td>${x.registration}</td>
      <td><b>${x.profile}</b><br><small style="color:var(--muted)">${x.role_name || 'Operação Geral'}</small></td>
      <td>${x.unit || 'Matriz'}</td>
      <td>${statusBadge}</td>
      <td><span class="pill ${x.active ? 'green' : 'red'}">${x.active ? 'ATIVO' : 'INATIVO'}</span></td>
    </tr>`;
  }).join('') : '<tr><td colspan="6" class="empty">Nenhum profissional encontrado para o filtro aplicado.</td></tr>';
}

async function roles() {
  title('Cargos e Perfis', 'PESSOAS · ESTRUTURA DE CARGOS');
  const data = await api('/api/roles');
  content.innerHTML = `
    <section class="panel">
      <div class="toolbar">
        <div>
          <h2>Matriz de Cargos Operacionais</h2>
          <small>Define CBO, certificações obrigatórias e tempo mínimo de descanso interjornada por função.</small>
        </div>
        <button class="primary" id="newRoleBtn">＋ Novo cargo</button>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Código</th><th>Cargo</th><th>CBO</th><th>Certificação Exigida</th><th>Descanso Mínimo</th><th>Colaboradores</th></tr></thead>
          <tbody>
            ${data.map(r => `<tr>
              <td><b>${r.code}</b></td>
              <td>${r.name}</td>
              <td>${r.cbo}</td>
              <td><span class="pill amber">${r.req_cert}</span></td>
              <td>${r.min_rest_h}h obrigatórias</td>
              <td><b>${r.active_count}</b> ativo(s)</td>
            </tr>`).join('')}
          </tbody>
        </table>
      </div>
    </section>`;
  $('#newRoleBtn').onclick = roleModal;
}

function roleModal() {
  openModal('Cadastrar novo cargo', `
    <form id="roleForm" class="form-grid">
      <label>Código do Cargo<input name="code" placeholder="Ex: MOT-BIT" required></label>
      <label>Código CBO<input name="cbo" placeholder="Ex: 7825-10" required></label>
      <label class="full">Nome do Cargo<input name="name" placeholder="Ex: Motorista Bitrem Sênior" required></label>
      <label>Certificação Obrigatória<input name="req_cert" placeholder="Ex: CNH E + MOPP" required></label>
      <label>Descanso Mínimo (Horas)<input name="min_rest_h" type="number" value="11" min="8" max="24" required></label>
      <div class="form-actions">
        <button type="button" class="secondary" data-close>Cancelar</button>
        <button class="primary">Salvar cargo</button>
      </div>
    </form>`);
  $('#roleForm').onsubmit = async e => {
    e.preventDefault();
    await api('/api/roles', { method: 'POST', body: JSON.stringify(Object.fromEntries(new FormData(e.target))) });
    closeOverlays();
    toast('Cargo cadastrado e vinculado à matriz de qualificação.');
    roles();
  };
  document.querySelectorAll('[data-close]').forEach(x => x.onclick = closeOverlays);
}

async function schedules() {
  title('Escalas', 'PLANEJAMENTO · UC05');
  const data = await api('/api/schedules');
  content.innerHTML = `
    <section class="panel">
      <div class="toolbar">
        <div>
          <h2>Escalas Planejadas</h2>
          <small>Acompanhe a cobertura de vagas por turno e valide a alocação dos motoristas.</small>
        </div>
        <div style="display:flex;gap:8px">
          <button class="secondary" id="goValidateBtn">✓ Validar alocação</button>
          <button class="primary" id="newScheduleBtn">＋ Nova escala</button>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Data</th><th>Turno</th><th>Horário</th><th>Cobertura</th><th>Situação</th></tr></thead>
          <tbody>
            ${data.map(x => {
              const ok = x.status.includes('COBERTA');
              return `<tr>
                <td><b>${x.schedule_date}</b></td>
                <td>${x.shift_name}</td>
                <td>${x.start_time} – ${x.end_time}</td>
                <td>${x.allocated_count ?? x.required_count} / ${x.required_count} vaga(s)</td>
                <td><span class="pill ${ok ? 'green' : 'amber'}">${x.status}</span></td>
              </tr>`;
            }).join('')}
          </tbody>
        </table>
      </div>
    </section>`;
  $('#goValidateBtn').onclick = () => go('allocations');
  $('#newScheduleBtn').onclick = scheduleModal;
}

async function scheduleModal() {
  const shiftList = await api('/api/shifts');
  openModal('Criar nova escala operacional', `
    <form id="scheduleForm" class="form-grid">
      <label>Data da Escala<input name="schedule_date" type="date" value="2026-11-25" required></label>
      <label>Turno Operacional
        <select name="shift_name">
          ${shiftList.map(s => `<option value="${s.name}">${s.name} (${s.start_time}–${s.end_time})</option>`).join('')}
        </select>
      </label>
      <label>Horário Início<input name="start_time" type="time" value="06:00" required></label>
      <label>Horário Fim<input name="end_time" type="time" value="14:20" required></label>
      <label class="full">Quantidade de Vagas Necessárias<input name="required_count" type="number" value="4" min="1" required></label>
      <div class="form-actions">
        <button type="button" class="secondary" data-close>Cancelar</button>
        <button class="primary">Publicar escala</button>
      </div>
    </form>`);
  $('#scheduleForm').onsubmit = async e => {
    e.preventDefault();
    await api('/api/schedules', { method: 'POST', body: JSON.stringify(Object.fromEntries(new FormData(e.target))) });
    closeOverlays();
    toast('Escala criada! Agora você pode alocar os profissionais.');
    schedules();
  };
  document.querySelectorAll('[data-close]').forEach(x => x.onclick = closeOverlays);
}

async function certifications() {
  title('Certificações', 'PESSOAS · UC02');
  const data = await api('/api/certifications');
  tablePage('Certificações profissionais', ['Pessoa', 'Tipo', 'Código', 'Vencimento', 'Situação'],
    data.map(x => [x.employee_name, x.type, x.code || '—', x.expires_at || '—', `<span class="pill ${x.status === 'VALIDA' ? 'green' : (x.status === 'VENCIDA' ? 'red' : 'amber')}">${x.status}</span>`]),
    'Heurística de Prevenção: Certificação obrigatória vencida bloqueia automaticamente a alocação.');
}

async function availabilities() {
  title('Disponibilidades', 'PLANEJAMENTO · UC03');
  const data = await api('/api/availabilities');
  tablePage('Períodos registrados', ['Profissional', 'Início', 'Fim', 'Tipo'],
    data.map(x => [x.employee_name, fmt(x.start_at), fmt(x.end_at), `<span class="pill ${x.kind.includes('INDISPONIVEL') ? 'red' : 'green'}">${x.kind}</span>`]),
    'Indisponibilidade tem precedência sobre disponibilidade.');
}

async function shifts() {
  title('Turnos', 'PLANEJAMENTO · UC04');
  const data = await api('/api/shifts');
  tablePage('Turnos operacionais', ['Código', 'Nome', 'Unidade', 'Horário', 'Necessidade', 'Situação'],
    data.map(x => [x.code, x.name, x.unit, `${x.start_time}–${x.end_time}`, `${x.required_count} prof.`, `<span class="pill green">${x.status}</span>`]),
    'Turnos que atravessam meia-noite terminam no dia seguinte.');
}

async function conflicts() {
  title('Conflitos e alertas', 'CONTROLE · UC09');
  const data = await api('/api/conflicts');
  tablePage('Fila de decisões e bloqueios preventivos', ['Severidade', 'Tipo', 'Profissional', 'Descrição', 'Situação'],
    data.map(x => [`<span class="pill ${x.severity === 'CRITICA' ? 'red' : 'amber'}">${x.severity}</span>`, x.type, x.employee_name || 'Escala', x.description, x.status]),
    'Todo conflito possui origem rastreável e impede escalonamento inseguro.');
}

async function allocations() {
  title('Validar alocação', 'OPERAÇÃO · UC06 / UC07 / UC08');
  const peopleList = await api('/api/employees'), scheduleList = await api('/api/schedules');
  content.innerHTML = `
    <section class="panel">
      <h2>Motor de validação preventiva</h2>
      <p style="color:var(--muted);margin-top:-8px">O sistema verifica disponibilidade, certificações obrigatórias e descanso mínimo interjornada antes de confirmar a escala.</p>
      <form id="allocationForm" class="form-grid">
        <label>Escala de Destino
          <select name="scheduleId">${scheduleList.map(x => `<option value="${x.id}">${x.schedule_date} · ${x.shift_name}</option>`)}</select>
        </label>
        <label>Profissional
          <select name="employeeId" id="empSelect">${peopleList.map(x => `<option value="${x.id}">${x.name} · ${x.profile}</option>`)}</select>
        </label>
        <div class="full" id="preventiveBanner"></div>
        <label class="full">Início planejado<input name="startAt" type="datetime-local" value="2026-11-23T06:00" required></label>
        <div class="form-actions"><button class="primary">Executar validação completa</button></div>
      </form>
      <div id="validationResult"></div>
    </section>`;

  const updateBanner = () => {
    const emp = peopleList.find(e => e.id === Number($('#empSelect').value));
    if (!emp) return;
    if (emp.block_reason) {
      $('#preventiveBanner').innerHTML = `<div class="queue-item" style="border-color:var(--red);background:#fff5f5">
        <span class="pill red">⚠ ALERTA PREVENTIVO (HEURÍSTICA #5)</span>
        <b> Bloqueio detectado para ${emp.name}:</b>
        <p style="margin:4px 0 0">${emp.block_reason}. A alocação será recusada pelo motor de regras.</p>
      </div>`;
    } else {
      $('#preventiveBanner').innerHTML = `<div class="queue-item" style="border-color:var(--green);background:#f3fbf7">
        <span class="pill green">✓ PRÉ-CHECK APROVADO</span>
        <b> ${emp.name}</b> possui certificação válida e ${emp.rest_hours}h de descanso cumpridas.
      </div>`;
    }
  };
  $('#empSelect').onchange = updateBanner;
  updateBanner();

  allocationForm.onsubmit = async e => {
    e.preventDefault();
    const d = Object.fromEntries(new FormData(e.target));
    d.employeeId = Number(d.employeeId);
    const r = await api('/api/allocations/validate', { method: 'POST', body: JSON.stringify(d) });
    validationResult.innerHTML = `
      <hr style="border:0;border-top:1px solid var(--line);margin:18px 0">
      <h3>Resultado da Auditoria: <span class="pill ${r.resultado === 'APTO' ? 'green' : 'red'}">${r.resultado}</span></h3>
      ${r.validacoes.map(v => `<div class="queue-item"><b>${v.status === 'APROVADO' ? '✓' : '✕'} ${v.regra}</b><p>${v.motivo || 'Regra atendida.'}</p></div>`).join('')}
      ${r.resultado === 'APTO' ? '<button class="primary" id="confirmAllocation">Confirmar alocação e emitir evento</button>' : ''}`;
    if (r.resultado === 'APTO') {
      confirmAllocation.onclick = async () => {
        await api('/api/allocations', { method: 'POST', body: JSON.stringify({ scheduleId: Number(d.scheduleId), employeeId: d.employeeId }) });
        toast('Alocação confirmada! Evento MotoristaEscalado publicado.');
      };
    }
  };
}

function tablePage(h, heads, rows, note) {
  content.innerHTML = `<section class="panel"><div class="toolbar"><div><h2>${h}</h2><small>${note}</small></div></div><div class="table-wrap"><table><thead><tr>${heads.map(x => `<th>${x}</th>`).join('')}</tr></thead><tbody>${rows.length ? rows.map(r => `<tr>${r.map(c => `<td>${c ?? '—'}</td>`).join('')}</tr>`).join('') : `<tr><td colspan="${heads.length}" class="empty">Nenhum registro encontrado.</td></tr>`}</tbody></table></div></section>`;
}

function generic(page) {
  const labels = { documents: 'Documentos e currículos', journeys: 'Jornadas', rests: 'Descansos', vehicles: 'Veículos', history: 'Histórico', indicators: 'Indicadores', reports: 'Relatórios', audit: 'Auditoria', parameters: 'Parâmetros', users: 'Usuários e permissões' };
  title(labels[page] || 'Módulo', 'SIG-LOG PEOPLE');
  content.innerHTML = `<section class="panel"><h2>${labels[page] || page}</h2><p>Módulo mapeado na arquitetura DDD do Squad 05. Os fluxos principais já estão ativos em <b>Profissionais</b>, <b>Cargos e Perfis</b>, <b>Escalas</b> e <b>Alocações</b>.</p><div class="queue-item"><b>Heurística de Controle e Liberdade</b><p>Nenhuma ação destrutiva é executada sem confirmação explícita e validação de perfil.</p></div></section>`;
}

function about() {
  title('Sobre o sistema', 'CONFIGURAÇÕES');
  content.innerHTML = '<section class="panel"><h2>JornadaLog SIG 4.1 People</h2><p>Sistema de Informações Gerenciais de RH, Jornada e Escalonamento — Squad 05 (Disciplina de Análise de Sistemas II).</p><p><b>Heurísticas de Usabilidade Aplicadas:</b> Visibilidade do status do sistema, prevenção de erros no escalonamento, controle de acesso por perfil e consistência visual.</p><p><b>Integrantes:</b> João Victor (Frontend/UX/BPMN), Aughusto (Backend/Regras) e Infraestrutura/Banco.</p></section>';
}

function employeeModal() {
  openModal('Cadastrar profissional (UC01)', `
    <form id="employeeForm" class="form-grid">
      <label>Nome completo<input name="name" placeholder="Ex: Lucas Andrade" required></label>
      <label>Matrícula<input name="registration" placeholder="Ex: MAT-1200" required></label>
      <label>Perfil Operacional<select name="profile"><option value="MOTORISTA">MOTORISTA</option><option value="OPERADOR">OPERADOR</option></select></label>
      <label>Cargo Vinculado<select name="role_name"><option>Motorista Carreteiro</option><option>Motorista Distribuição Urbana</option><option>Operador de Empilhadeira</option><option>Operador Logístico de Docas</option></select></label>
      <label class="full">Unidade / CD<input name="unit" value="CD Recife - BR-101"></label>
      <div class="form-actions"><button type="button" class="secondary" data-close>Cancelar</button><button class="primary">Salvar profissional</button></div>
    </form>`);
  $('#employeeForm').onsubmit = async e => {
    e.preventDefault();
    try {
      await api('/api/employees', { method: 'POST', body: JSON.stringify(Object.fromEntries(new FormData(e.target))) });
      closeOverlays();
      toast('Profissional cadastrado com sucesso!');
      people();
    } catch (err) {
      toast(err.message);
    }
  };
  document.querySelectorAll('[data-close]').forEach(x => x.onclick = closeOverlays);
}

function openModal(t, b) { modalTitle.textContent = t; modalBody.innerHTML = b; modal.classList.add('open'); modal.setAttribute('aria-hidden', 'false'); }
function closeOverlays() { modal.classList.remove('open'); drawer.classList.remove('open'); backdrop.classList.remove('show'); }
function fmt(x) { return x ? new Date(x).toLocaleString('pt-BR') : '—'; }

roleSelect.onchange = () => {
  state.role = roleSelect.value;
  if (!allowed(state.page)) state.page = 'dashboard';
  renderNav();
  render();
  toast(`Perfil alterado para ${roleSelect.options[roleSelect.selectedIndex].text}.`);
};

menuBtn.onclick = () => sidebar.classList.toggle('open');
quickBtn.onclick = employeeModal;
notificationBtn.onclick = async () => {
  const d = await api('/api/conflicts');
  drawerContent.innerHTML = d.map(x => `<div class="queue-item"><span class="pill ${x.severity === 'CRITICA' ? 'red' : 'amber'}">${x.severity}</span><b> ${x.type}</b><p>${x.description}</p></div>`).join('') || '<p class="empty">Sem notificações.</p>';
  drawer.classList.add('open');
  backdrop.classList.add('show');
};
backdrop.onclick = closeOverlays;
document.querySelectorAll('[data-close]').forEach(x => x.onclick = closeOverlays);
globalSearch.onkeydown = e => {
  if (e.key === 'Enter') {
    go('people');
    setTimeout(() => {
      const f = $('#filter');
      if (f) { f.value = e.target.value; f.dispatchEvent(new Event('input')); }
    }, 100);
  }
};

(async () => {
  renderNav();
  await render();
  const n = await api('/api/conflicts');
  notificationCount.textContent = n.length;
  if (isDemoMode) {
    apiStatus.textContent = '● Modo Demo (Local)';
    apiStatus.className = 'status good';
    apiStatus.title = 'Exibindo dados simulados enquanto a API Flask está offline';
  } else {
    apiStatus.textContent = '● API Online';
    apiStatus.className = 'status good';
  }
})();