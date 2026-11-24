"""Composição das dependências (injeção manual)."""
from types import SimpleNamespace
from typing import Optional

from src.application import use_cases as uc
from src.application.ports import EventPublisher
from src.config.settings import Settings
from src.infrastructure import memory_repositories as mr
from src.infrastructure.publishers import InMemoryEventPublisher, RabbitMQEventPublisher


def build_container(settings: Optional[Settings] = None,
                    publisher: Optional[EventPublisher] = None) -> SimpleNamespace:
    settings = settings or Settings()
    if publisher is None:
        publisher = (InMemoryEventPublisher() if settings.rabbitmq_url.startswith("memory://")
                     else RabbitMQEventPublisher(settings.rabbitmq_url))
    repos = uc.Repos(
        funcionarios=mr.FuncionarioRepository(), veiculos=mr.VeiculoRepository(),
        turnos=mr.TurnoRepository(), escalas=mr.EscalaRepository(),
        disponibilidades=mr.DisponibilidadeRepository(), jornadas=mr.JornadaRepository(),
        descansos=mr.DescansoRepository(), alocacoes=mr.AlocacaoRepository())
    make = lambda cls: cls(repos, publisher, settings)
    return SimpleNamespace(
        settings=settings, publisher=publisher, repos=repos,
        cadastrar_funcionario=make(uc.CadastrarFuncionario),
        registrar_certificacao=make(uc.RegistrarCertificacao),
        registrar_disponibilidade=make(uc.RegistrarDisponibilidade),
        consultar_disponibilidade=make(uc.ConsultarDisponibilidade),
        criar_turno=make(uc.CriarTurno), criar_escala=make(uc.CriarEscala),
        validar_jornada=make(uc.ValidarJornada),
        iniciar_jornada=make(uc.IniciarJornada), finalizar_jornada=make(uc.FinalizarJornada),
        validar_descanso=make(uc.ValidarDescanso), registrar_descanso=make(uc.RegistrarDescanso),
        validar_alocacao=make(uc.ValidarAlocacao), alocar_motorista=make(uc.AlocarMotorista),
        detectar_conflito=make(uc.DetectarConflito),
        detectar_conflitos_escala=make(uc.DetectarConflitosDaEscala),
        consultar_escala=make(uc.ConsultarEscala), consultar_motoristas=make(uc.ConsultarMotoristas),
        cadastrar_veiculo=make(uc.CadastrarVeiculo))
