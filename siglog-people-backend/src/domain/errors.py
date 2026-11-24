class DomainError(Exception):
    """Erro de regra de negócio (mapeado para HTTP 422)."""


class NotFoundError(DomainError):
    """Entidade não encontrada (HTTP 404)."""


class ValidationError(DomainError):
    """Dados de entrada inválidos (HTTP 400)."""


class ConflictError(DomainError):
    """Conflito de estado, ex.: CPF duplicado ou alocação sobreposta (HTTP 409)."""
