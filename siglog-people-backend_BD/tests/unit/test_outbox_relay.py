"""Relay da outbox com banco e broker falsos (sem PostgreSQL/RabbitMQ)."""
import unittest

from src.infrastructure import outbox_relay as relay


class _Res:
    def __init__(self, rows): self.rows = rows
    def fetchall(self): return self.rows


class _Conn:
    def __init__(self, eventos): self.eventos, self.updates = eventos, []
    def execute(self, sql, params=()):
        if sql == relay.SELECIONAR:
            return _Res([e for e in self.eventos if e["status"] == "PENDENTE"][:params[0]])
        ev = next(e for e in self.eventos if e["id"] == params[-1])
        if sql == relay.MARCAR_OK:
            ev["status"] = "PROCESSADO"; ev["tentativas"] += 1
        elif sql == relay.MARCAR_FALHA:
            ev["erro"], ev["status"] = params[0], params[1]; ev["tentativas"] += 1
        return _Res([])


class _Db:
    def __init__(self, eventos): self.conn, self.commits, self.rollbacks, self.closed = _Conn(eventos), 0, 0, 0
    def commit(self): self.commits += 1
    def rollback(self): self.rollbacks += 1
    def close(self): self.closed += 1


class _Pub:
    def __init__(self, falha_em=()): self.falha_em, self.enviados = set(falha_em), []
    def publish_envelope(self, nome, envelope):
        if envelope["event_id"] in self.falha_em:
            raise RuntimeError("broker fora do ar")
        self.enviados.append((nome, envelope["event_id"]))


def _ev(i, tentativas=0):
    return {"id": i, "tipo_evento": "MotoristaEscalado", "tentativas": tentativas, "status": "PENDENTE",
            "payload": {"event_id": f"e{i}", "event": "MotoristaEscalado", "payload": {}}}


class OutboxRelayTest(unittest.TestCase):
    def test_publica_em_ordem_e_marca_processado(self):
        db, pub = _Db([_ev(1), _ev(2)]), _Pub()
        self.assertEqual(relay.processar_lote(db, pub), 2)
        self.assertEqual(pub.enviados, [("MotoristaEscalado", "e1"), ("MotoristaEscalado", "e2")])
        self.assertTrue(all(e["status"] == "PROCESSADO" for e in db.conn.eventos))
        self.assertEqual((db.commits, db.closed), (1, 1))

    def test_falha_mantem_pendente_e_interrompe_o_lote(self):
        db, pub = _Db([_ev(1), _ev(2)]), _Pub(falha_em={"e1"})
        self.assertEqual(relay.processar_lote(db, pub), 0)
        e1, e2 = db.conn.eventos
        self.assertEqual((e1["status"], e1["tentativas"], e1["erro"]), ("PENDENTE", 1, "broker fora do ar"))
        self.assertEqual((e2["status"], e2["tentativas"]), ("PENDENTE", 0))   # ordem preservada

    def test_esgotar_tentativas_vira_erro_e_nao_trava_a_fila(self):
        db, pub = _Db([_ev(1, tentativas=4), _ev(2)]), _Pub(falha_em={"e1"})
        self.assertEqual(relay.processar_lote(db, pub, max_tentativas=5), 1)
        e1, e2 = db.conn.eventos
        self.assertEqual(e1["status"], "ERRO")
        self.assertEqual(e2["status"], "PROCESSADO")

    def test_erro_de_banco_faz_rollback(self):
        db = _Db([_ev(1)])
        db.conn.execute = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("db caiu"))
        with self.assertRaises(RuntimeError):
            relay.processar_lote(db, _Pub())
        self.assertEqual((db.rollbacks, db.closed), (1, 1))


if __name__ == "__main__":
    unittest.main()
