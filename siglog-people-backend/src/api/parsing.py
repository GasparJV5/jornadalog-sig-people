from datetime import date, datetime, time, timezone

from src.domain.errors import ValidationError


def require(body: dict, *fields):
    if not isinstance(body, dict):
        raise ValidationError("Corpo da requisição deve ser um objeto JSON.")
    missing = [f for f in fields if body.get(f) in (None, "")]
    if missing:
        raise ValidationError(f"Campos obrigatórios ausentes: {', '.join(missing)}.")


def parse_dt(value, field="data/hora"):
    """ISO-8601 -> datetime ingênuo em UTC (evita mistura de naive/aware)."""
    try:
        d = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        raise ValidationError(f"{field} inválido (use ISO-8601).")
    if d.tzinfo:
        d = d.astimezone(timezone.utc).replace(tzinfo=None)
    return d


def parse_date(value, field="data"):
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise ValidationError(f"{field} inválida (use YYYY-MM-DD).")


def parse_time(value, field="hora"):
    try:
        return time.fromisoformat(str(value))
    except ValueError:
        raise ValidationError(f"{field} inválida (use HH:MM).")
