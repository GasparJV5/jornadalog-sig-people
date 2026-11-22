import re

CNH_CATEGORIAS = {"A", "B", "C", "D", "E"}


def cpf_valido(cpf: str) -> bool:
    """Valida CPF (11 dígitos + dígitos verificadores)."""
    nums = re.sub(r"\D", "", cpf or "")
    if len(nums) != 11 or nums == nums[0] * 11:
        return False
    for i in (9, 10):
        soma = sum(int(nums[j]) * (i + 1 - j) for j in range(i))
        dig = (soma * 10 % 11) % 10
        if dig != int(nums[i]):
            return False
    return True


def normaliza_cpf(cpf: str) -> str:
    return re.sub(r"\D", "", cpf or "")


# Hierarquia simplificada do CTB: D cobre B/C; E cobre B/C/D; A é exclusiva (motos).
_RANK = {"B": 1, "C": 2, "D": 3, "E": 4}


def cnh_compativel(categoria_motorista: str, categoria_exigida: str) -> bool:
    m, e = categoria_motorista.upper(), categoria_exigida.upper()
    if m == "A" or e == "A":
        return m == e
    return _RANK.get(m, 0) >= _RANK.get(e, 99)
