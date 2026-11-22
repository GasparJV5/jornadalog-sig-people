from datetime import date, datetime, time

from src.config.container import build_container

CPF_OK = "529.982.247-25"
CPF_OK_2 = "111.444.777-35"


def dt(dia: int, hora: int, mes: int = 3) -> datetime:
    return datetime(2026, mes, dia, hora, 0)


def novo_container():
    return build_container()


def cenario_basico(c):
    """Motorista C com MOPP vigente + disponível 01/03→05/03, veículo que exige C+MOPP."""
    m = c.cadastrar_funcionario.execute("Ana Souza", CPF_OK, "MOTORISTA", "C")
    c.registrar_certificacao.execute(m.id, "MOPP", date(2027, 1, 1))
    c.registrar_disponibilidade.execute(m.id, dt(1, 0), dt(5, 23), True)
    v = c.cadastrar_veiculo.execute("ABC1D23", "C", ["MOPP"])
    return m, v
