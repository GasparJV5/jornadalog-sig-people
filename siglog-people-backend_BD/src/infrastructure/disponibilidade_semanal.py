"""Conversão entre as janelas da API (data/hora) e a tabela `disponibilidades` do banco,
que é semanal: (dia_semana, hora_inicio, hora_fim, vigencia_inicio, vigencia_fim).

* Gravar: uma janela vira uma linha por dia, com vigência de um único dia.
* Validar: as linhas (inclusive recorrentes, com vigência aberta) são expandidas
  em janelas concretas para as datas do período.

Convenção de dia_semana: 0 = domingo ... 6 = sábado (igual ao EXTRACT(DOW) do PostgreSQL).
Fim de dia: como TIME não aceita 24:00 no driver, uma janela que vai até a meia-noite
é gravada com hora_fim = 23:59:59.999999, tratada aqui como 00:00 do dia seguinte.

Este módulo é puro (sem banco) e tem testes unitários.
"""
from datetime import date, datetime, time, timedelta
from typing import Iterable, List

from src.domain.entities import Disponibilidade, Periodo

FIM_DO_DIA = time(23, 59, 59, 999999)


def dia_semana(d: date) -> int:
    return (d.weekday() + 1) % 7


def _fim(d: date, t: time) -> datetime:
    if t == FIM_DO_DIA:
        return datetime.combine(d, time.min) + timedelta(days=1)
    return datetime.combine(d, t)


def segmentar(periodo: Periodo) -> List[dict]:
    """Quebra uma janela em linhas diárias prontas para INSERT."""
    linhas, cur = [], periodo.inicio
    while cur < periodo.fim:
        meia_noite = datetime.combine(cur.date(), time.min) + timedelta(days=1)
        fim_seg = min(periodo.fim, meia_noite)
        linhas.append({"dia_semana": dia_semana(cur.date()),
                       "hora_inicio": cur.time(),
                       "hora_fim": FIM_DO_DIA if fim_seg == meia_noite else fim_seg.time(),
                       "vigencia": cur.date()})
        cur = fim_seg
    return linhas


def expandir(linhas: Iterable[dict], periodo: Periodo, funcionario_id: str) -> List[Disponibilidade]:
    """Janelas concretas para as datas que o período toca.
    Cada linha: id, dia_semana, hora_inicio, hora_fim, vigencia_inicio, vigencia_fim, disponivel."""
    linhas, saida = list(linhas), []
    d, ultimo = periodo.inicio.date(), periodo.fim.date()
    while d <= ultimo:
        for l in linhas:
            if l["dia_semana"] != dia_semana(d):
                continue
            if l["vigencia_inicio"] > d or (l["vigencia_fim"] and l["vigencia_fim"] < d):
                continue
            saida.append(Disponibilidade(
                funcionario_id, Periodo(datetime.combine(d, l["hora_inicio"]), _fim(d, l["hora_fim"])),
                bool(l["disponivel"]), id=str(l["id"])))
        d += timedelta(days=1)
    return saida


def janela_de_linha_pontual(l: dict, funcionario_id: str) -> Disponibilidade:
    """Linha com vigência de um dia (vigencia_inicio == vigencia_fim) -> janela."""
    d = l["vigencia_inicio"]
    return Disponibilidade(funcionario_id,
                           Periodo(datetime.combine(d, l["hora_inicio"]), _fim(d, l["hora_fim"])),
                           bool(l["disponivel"]), id=str(l["id"]))


def mesclar(janelas: List[Disponibilidade]) -> List[Disponibilidade]:
    """Une janelas contíguas ou sobrepostas com o mesmo valor de `disponivel`."""
    saida: List[Disponibilidade] = []
    for j in sorted(janelas, key=lambda x: x.periodo.inicio):
        if saida and saida[-1].disponivel == j.disponivel and saida[-1].periodo.fim >= j.periodo.inicio:
            ant = saida[-1]
            ant.periodo = Periodo(ant.periodo.inicio, max(ant.periodo.fim, j.periodo.fim))
        else:
            saida.append(j)
    return saida
