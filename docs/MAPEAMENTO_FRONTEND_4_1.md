# Mapeamento do frontend 4.1

## Diretriz
Reaproveitar a identidade gerencial do JornadaLog: menu lateral azul-marinho, barra superior, banner decisório, cartões de KPI, ciclo operacional e fila de decisões. O menu foi reduzido para funções reais do SIG-Log People.

## Menu
1. Visão Geral
2. Pessoas: profissionais, certificações, documentos e currículos
3. Planejamento: disponibilidades, turnos e escalas
4. Operação: alocações, jornadas e descansos
5. Controle: conflitos, veículos e histórico
6. Inteligência: indicadores, relatórios e auditoria
7. Configurações: parâmetros, usuários e sobre

## Perfis
- Administrador: acesso integral.
- Gestor de RH: pessoas, documentos, certificações, disponibilidades e relatórios.
- Gestor de Operações: escalas, alocações, jornadas, conflitos, veículos e indicadores.
- Operador: escalas, alocações, jornadas e conflitos.
- Profissional: próprio contexto de disponibilidade, certificações, escalas e jornadas.

O frontend oculta opções por perfil, porém o backend deve aplicar RBAC antes da produção.

## Fluxo demonstrável
Dashboard -> profissional -> certificação -> disponibilidade -> turno -> escala -> validar alocação -> confirmar -> registrar MotoristaEscalado -> conflito.

## Estados obrigatórios
Carregando, vazio, sucesso, erro, API indisponível e permissão insuficiente.

## Prioridade MVP
As telas de dashboard, profissionais, certificações, disponibilidades, turnos, escalas, alocação e conflitos possuem leitura funcional. Áreas secundárias permanecem preparadas para evolução e não devem ser apresentadas como concluídas.
