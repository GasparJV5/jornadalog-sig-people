/**
 * SIG-LOG ENTERPRISE 4.1 - CLIENTE HTTP DESACOPLADO
 * Comunicação direta com os endpoints Flask/SQLite do backend
 */

const getApiBaseUrl = () => {
  if (typeof window !== 'undefined' && window.location && window.location.origin) {
    if (window.location.origin.includes('5000')) {
      return window.location.origin;
    }
  }
  return 'http://localhost:5000';
};

const API_BASE_URL = getApiBaseUrl();

const API = {
  async getHealth() {
    try {
      const res = await fetch(`${API_BASE_URL}/health`);
      return await res.json().catch(() => ({ status: 'ok' }));
    } catch (e) {
      throw new Error('Serviço /health inacessível');
    }
  },

  async getDashboard() {
    const res = await fetch(`${API_BASE_URL}/api/dashboard`);
    if (!res.ok) throw new Error('Falha ao obter métricas executivas');
    return await res.json().catch(() => ({}));
  },

  async getEmployees() {
    const res = await fetch(`${API_BASE_URL}/api/employees`);
    if (!res.ok) throw new Error('Falha ao consultar quadro de colaboradores');
    return await res.json().catch(() => []);
  },

  async createEmployee(payload) {
    const res = await fetch(`${API_BASE_URL}/api/employees`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.message || 'Erro ao registrar profissional');
    }
    return await res.json().catch(() => ({ success: true }));
  },

  async validateAllocation(payload) {
    const res = await fetch(`${API_BASE_URL}/api/allocations/validate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json().catch(() => ({}));
    return { ok: res.ok, data };
  },

  async createAllocation(payload) {
    const res = await fetch(`${API_BASE_URL}/api/allocations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.message || 'Falha ao consolidar alocação no Outbox');
    }
    return await res.json().catch(() => ({ success: true }));
  },

  async getConflicts() {
    const res = await fetch(`${API_BASE_URL}/api/conflicts`);
    if (!res.ok) throw new Error('Falha ao carregar auditoria de conflitos');
    return await res.json().catch(() => []);
  }
};
