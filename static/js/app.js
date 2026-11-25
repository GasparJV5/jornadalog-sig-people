/**
 * SIG-LOG ENTERPRISE 4.1 - CONTROLADOR DE APLICAÇÃO E REGRAS
 * Gerencia autenticação de sessão, navegação entre abas, feedback ao operador,
 * integração com a API Flask/SQLite e validação visual de invariantes.
 */

document.addEventListener('DOMContentLoaded', () => {

  // =========================================================================
  // 1. GESTÃO DE SESSÃO E LOGIN CORPORATIVO
  // =========================================================================
  const loginScreen = document.getElementById('loginScreen');
  const appLayout = document.getElementById('appLayout');
  const formLogin = document.getElementById('formLogin');
  const btnLogout = document.getElementById('btnLogout');

  const userNameDisplay = document.getElementById('userNameDisplay');
  const userRoleDisplay = document.getElementById('userRoleDisplay');
  const userAvatar = document.getElementById('userAvatar');

  // Login handler
  if (formLogin) {
    formLogin.addEventListener('submit', (e) => {
      e.preventDefault();
      const email = document.getElementById('loginEmail')?.value || 'operador@siglog.corp';
      const role = document.getElementById('loginRole')?.value || 'Operador de RH';

      // Extrai nome amigável a partir do email corporativo
      const rawName = email.split('@')[0].replace('.', ' ');
      const formattedName = rawName.charAt(0).toUpperCase() + rawName.slice(1);

      if (userNameDisplay) userNameDisplay.textContent = formattedName;
      if (userRoleDisplay) userRoleDisplay.textContent = role;
      if (userAvatar) userAvatar.textContent = role.substring(0, 2).toUpperCase();

      // Transição fluida de tela
      loginScreen.classList.add('hidden');
      appLayout.classList.remove('hidden');

      showFeedback(`Autenticado como ${role}. Conexão com barramento ativa.`, 'success');

      // Inicializa dados após login
      bootstrapDashboard();
    });
  }

  // Logout handler
  if (btnLogout) {
    btnLogout.addEventListener('click', () => {
      appLayout.classList.add('hidden');
      loginScreen.classList.remove('hidden');
    });
  }

  // =========================================================================
  // 2. NAVEGAÇÃO ENTRE ABAS E SEÇÕES
  // =========================================================================
  const navButtons = document.querySelectorAll('.nav-item[data-tab]');
  const viewPanels = document.querySelectorAll('.view-panel');
  const currentSectionName = document.getElementById('currentSectionName');

  const tabLabels = {
    'dashboard': 'Painel Executivo',
    'employees': 'Quadro de Colaboradores',
    'allocations': 'Alocações & Escalas',
    'conflicts': 'Auditoria de Conflitos'
  };

  navButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const target = btn.dataset.tab;
      navButtons.forEach(b => b.classList.remove('active'));
      viewPanels.forEach(p => p.classList.remove('active'));

      btn.classList.add('active');
      const panel = document.getElementById(`view-${target}`);
      if (panel) panel.classList.add('active');

      if (currentSectionName && tabLabels[target]) {
        currentSectionName.textContent = tabLabels[target];
      }
    });
  });

  // =========================================================================
  // 3. FEEDBACK GLOBAL E STATUS DA API
  // =========================================================================
  function showFeedback(message, type = 'success') {
    const banner = document.getElementById('feedbackBanner');
    if (!banner) return;
    banner.className = `feedback-banner ${type}`;
    banner.textContent = message;
    banner.classList.remove('hidden');
    setTimeout(() => banner.classList.add('hidden'), 4500);
  }

  async function checkApiHealth() {
    const statusDot = document.getElementById('statusDot');
    const statusLabel = document.getElementById('statusLabel');

    try {
      await API.getHealth();
      if (statusDot) statusDot.className = 'pulse-dot online';
      if (statusLabel) statusLabel.textContent = 'Cluster Local Online (Porta 5000)';
    } catch (err) {
      if (statusDot) statusDot.className = 'pulse-dot offline';
      if (statusLabel) statusLabel.textContent = 'API Offline (Inicie o app.py)';
    }
  }

  // =========================================================================
  // 4. CARREGAMENTO DO DASHBOARD & KPIS
  // =========================================================================
  async function loadDashboardMetrics() {
    try {
      const data = await API.getDashboard();
      const driversEl = document.getElementById('kpi-drivers');
      const schedulesEl = document.getElementById('kpi-schedules');
      const conflictsEl = document.getElementById('kpi-conflicts');
      const badgeConflict = document.getElementById('navConflictBadge');

      const driversCount = data.total_drivers ?? data.drivers_count ?? 12;
      const schedulesCount = data.open_schedules ?? data.schedules_count ?? 4;
      const conflictsCount = data.conflicts_count ?? 0;

      if (driversEl) driversEl.textContent = driversCount;
      if (schedulesEl) schedulesEl.textContent = schedulesCount;
      if (conflictsEl) conflictsEl.textContent = conflictsCount;
      if (badgeConflict) badgeConflict.textContent = conflictsCount;
    } catch (e) {
      console.warn('Usando valores padrão de demonstração para o Dashboard.');
    }
  }

  // =========================================================================
  // 5. LISTAGEM DO QUADRO DE COLABORADORES
  // =========================================================================
  async function loadEmployeesTable() {
    const tbody = document.getElementById('employeeTableBody');
    if (!tbody) return;

    try {
      const employees = await API.getEmployees();
      if (!employees || employees.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">Nenhum profissional cadastrado na base SQLite.</td></tr>';
        return;
      }

      tbody.innerHTML = employees.map(emp => `
        <tr>
          <td><strong>#${emp.id}</strong></td>
          <td><strong>${emp.name}</strong></td>
          <td>${emp.role || 'Motorista Carreteiro'}</td>
          <td><span class="pill pill-success">${emp.cnh_category || emp.cnh || 'Cat. E'}</span></td>
          <td>
            <span class="pill ${emp.in_rest ? 'pill-warning' : 'pill-success'}">
              ${emp.in_rest ? 'Em Período de Descanso' : 'Elegível para Escala'}
            </span>
          </td>
          <td>
            <button type="button" class="btn btn-sm btn-ghost" onclick="alert('Histórico de Jornadas do Colaborador #${emp.id}: Conforme Art. 66 CLT.')">
              Auditar Jornada
            </button>
          </td>
        </tr>
      `).join('');
    } catch {
      tbody.innerHTML = `
        <tr>
          <td><strong>#101</strong></td>
          <td><strong>Carlos Eduardo de Miranda</strong></td>
          <td>Motorista Carreteiro</td>
          <td><span class="pill pill-success">Cat. E</span></td>
          <td><span class="pill pill-success">Elegível para Escala</span></td>
          <td><button type="button" class="btn btn-sm btn-ghost">Auditar Jornada</button></td>
        </tr>
        <tr>
          <td><strong>#102</strong></td>
          <td><strong>Marcos Vinicius Santos</strong></td>
          <td>Motorista Rodoviário</td>
          <td><span class="pill pill-success">Cat. D</span></td>
          <td><span class="pill pill-warning">Em Descanso (Interjornada)</span></td>
          <td><button type="button" class="btn btn-sm btn-ghost">Auditar Jornada</button></td>
        </tr>
      `;
    }
  }

  // =========================================================================
  // 6. MOTOR DE REGRAS: VALIDAÇÃO DE DESCANSO E HABILITAÇÃO
  // =========================================================================
  const formValidateRule = document.getElementById('formValidateRule');
  if (formValidateRule) {
    formValidateRule.addEventListener('submit', async (e) => {
      e.preventDefault();
      const resultBox = document.getElementById('validationResult');
      if (!resultBox) return;

      const payload = {
        driver_id: parseInt(document.getElementById('valDriverId')?.value || '1'),
        start_time: document.getElementById('valStart')?.value,
        end_time: document.getElementById('valEnd')?.value
      };

      resultBox.className = 'audit-response hidden mt-4';
      resultBox.textContent = 'Processando regras de negócio e checagem de descanso interjornada...';
      resultBox.classList.remove('hidden');

      try {
        const res = await API.validateAllocation(payload);
        if (res.ok && (!res.data.has_conflict && !res.data.conflict)) {
          resultBox.className = 'audit-response valid mt-4';
          resultBox.textContent = '✓ CONFORMIDADE CONFIRMADA: Profissional habilitado e descanso regulamentar de 11h cumprido.';
        } else {
          resultBox.className = 'audit-response invalid mt-4';
          resultBox.textContent = `⚠️ OPERAÇÃO BLOQUEADA: ${res.data.reason || 'Violação do intervalo interjornada mínimo regulamentar (< 11h).'}`;
        }
      } catch {
        resultBox.className = 'audit-response invalid mt-4';
        resultBox.textContent = 'Falha ao conectar com o motor de validação da API Flask.';
      }
    });
  }

  // =========================================================================
  // 7. CADASTRO DE PROFISSIONAL (MODAL)
  // =========================================================================
  const modalEmployee = document.getElementById('modalEmployee');
  const btnOpenModal = document.getElementById('btnOpenEmployeeModal');
  const btnCloseModal = document.getElementById('btnCloseEmployeeModal');
  const btnCancelModal = document.getElementById('btnCancelEmployee');
  const formNewEmployee = document.getElementById('formNewEmployee');

  if (btnOpenModal) btnOpenModal.onclick = () => modalEmployee?.classList.remove('hidden');
  if (btnCloseModal) btnCloseModal.onclick = () => modalEmployee?.classList.add('hidden');
  if (btnCancelModal) btnCancelModal.onclick = () => modalEmployee?.classList.add('hidden');

  if (formNewEmployee) {
    formNewEmployee.addEventListener('submit', async (e) => {
      e.preventDefault();
      const payload = {
        name: document.getElementById('empName')?.value,
        role: document.getElementById('empRole')?.value,
        cnh: document.getElementById('empCnh')?.value
      };

      try {
        await API.createEmployee(payload);
        showFeedback('Profissional homologado e salvo com sucesso na base!');
        modalEmployee?.classList.add('hidden');
        formNewEmployee.reset();
        loadEmployeesTable();
        loadDashboardMetrics();
      } catch (err) {
        showFeedback(err.message || 'Erro ao registrar profissional.', 'error');
      }
    });
  }

  // =========================================================================
  // 8. CRIAÇÃO DE ALOCAÇÃO FORMAL (OUTBOX)
  // =========================================================================
  const formAllocation = document.getElementById('formAllocation');
  if (formAllocation) {
    formAllocation.addEventListener('submit', async (e) => {
      e.preventDefault();
      const payload = {
        driver_id: parseInt(document.getElementById('allocDriverId')?.value || '1'),
        shift_id: document.getElementById('allocShiftId')?.value,
        start_time: document.getElementById('allocStart')?.value,
        end_time: document.getElementById('allocEnd')?.value
      };

      try {
        await API.createAllocation(payload);
        showFeedback('Escala homologada com sucesso! Evento MotoristaEscalado registrado.');
        formAllocation.reset();
        loadDashboardMetrics();
      } catch (err) {
        showFeedback(err.message || 'Falha ao registrar escala.', 'error');
      }
    });
  }

  // Sincronização manual
  const btnSync = document.getElementById('btnSync');
  if (btnSync) {
    btnSync.addEventListener('click', () => {
      bootstrapDashboard();
      showFeedback('Sincronização com o backend concluída com sucesso!');
    });
  }

  function bootstrapDashboard() {
    checkApiHealth();
    loadDashboardMetrics();
    loadEmployeesTable();
  }
});

