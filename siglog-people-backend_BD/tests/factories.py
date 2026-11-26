from datetime import date, datetime, time

from src.config.container import build_container
from src.config.settings import Settings

CPF_OK = "529.982.247-25"
CPF_OK_2 = "111.444.777-35"


def dt(dia: int, hora: int, mes: int = 3) -> datetime:
    return datetime(2026, mes, dia, hora, 0)


def novo_container():
    # Persistência SEMPRE em memória nos testes, mesmo que o .env aponte para o banco.
    return build_container(Settings(persistence="memory"))


def escala_para(c, dia: int, ini_h: int, fim_h: int, mes: int = 3):
    """Escala (criando o turno se preciso) para o dia, com o horário informado."""
    nome = f"T{ini_h:02d}-{fim_h:02d}"
    turno = c.repos.turnos.get_by_nome(nome) or c.criar_turno.execute(nome, time(ini_h), time(fim_h))
    d = date(2026, mes, dia)
    return c.repos.escalas.get_by_data_turno(d, turno.id) or c.criar_escala.execute(d, turno.id)


def alocar(c, motorista, veiculo, dia: int, ini_h: int, fim_h: int, **kw):
    e = escala_para(c, dia, ini_h, fim_h)
    return c.alocar_motorista.execute(motorista.id, veiculo.id, escala_id=e.id, **kw)


def cenario_basico(c):
    """Motorista C com MOPP vigente + disponível 01/03→05/03, veículo que exige C+MOPP."""
    m = c.cadastrar_funcionario.execute("Ana Souza", CPF_OK, "MOTORISTA", "C")
    c.registrar_certificacao.execute(m.id, "MOPP", date(2027, 1, 1))
    c.registrar_disponibilidade.execute(m.id, dt(1, 0), dt(5, 23), True)
    v = c.cadastrar_veiculo.execute("ABC1D23", "C", ["MOPP"])
    return m, v
