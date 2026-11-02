from datetime import datetime
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import db
import jejum

INICIO = datetime(2026, 11, 1, 20, 0)


def test_duracao_e_previsao():
    agora = datetime(2026, 11, 2, 10, 30)
    assert jejum.horas_decorridas(INICIO, agora) == pytest.approx(14.5)
    assert jejum.previsao_fim(INICIO, 16) == datetime(2026, 11, 2, 12, 0)
    assert jejum.formatar_duracao(14.5) == "14h30"
    assert jejum.formatar_duracao(0.05) == "0h03"


def test_iniciar_e_encerrar_jejum():
    assert db.jejum_ativo() is None
    db.iniciar_jejum('16:8', 16, INICIO)
    ativo = db.jejum_ativo()
    assert ativo['protocolo'] == '16:8'
    assert ativo['inicio'] == INICIO

    db.encerrar_jejum(ativo['id'], datetime(2026, 11, 2, 13, 0))
    assert db.jejum_ativo() is None
    historico = db.carregar_jejuns()
    assert historico['horas'].tolist() == [pytest.approx(17)]


def test_jejum_em_andamento_nao_entra_no_historico():
    db.iniciar_jejum('18:6', 18, INICIO)
    assert db.carregar_jejuns().empty


def test_jejum_entra_no_backup():
    db.iniciar_jejum('16:8', 16, INICIO)
    assert db.contar_registros()['Jejuns'] == 1


def test_comecar_e_encerrar_pela_pagina():
    app = AppTest.from_file(str(Path(__file__).parent.parent / 'dashboard.py'), default_timeout=60).run()
    app.switch_page('paginas/jejum.py').run()
    app.button[[b.label for b in app.button].index('▶️ Começar jejum')].click().run()
    assert db.jejum_ativo() is not None
    assert not app.exception

    app.button[[b.label for b in app.button].index('⏹️ Encerrar jejum')].click().run()
    assert db.jejum_ativo() is None
    assert len(db.carregar_jejuns()) == 1
    assert not app.exception
