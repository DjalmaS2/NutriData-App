"""Abre cada página do app (sem navegador) e confere que nenhuma dá erro.

Roda duas vezes: com o banco vazio (primeiro acesso) e com dados de exemplo.
"""
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import db

PAGINAS = ['paginas/dia.py', 'paginas/historico.py', 'paginas/pratos.py',
           'paginas/exercicios.py', 'paginas/jejum.py', 'paginas/perfil.py', 'paginas/backup.py']


def preencher_dados_de_exemplo():
    hoje = date.today()
    db.salvar_perfil('Masculino', 30, 80, 180, 'Moderado (exercício 3-5x por semana)', 'Perder peso', peso_meta=75)
    db.salvar_consumo('Almoço', 'Arroz, tipo 1, cozido', 150, {'calorias': 192, 'carboidratos': 42})
    db.salvar_consumo('1', 'Registro antigo', 10, {'calorias': 54})  # refeição fora da lista
    db.salvar_prato('Marmita', 250, {'calorias': 383})
    db.registrar_agua(hoje, 500)
    db.registrar_peso(hoje, 80)
    db.registrar_atividade(hoje, 'Corrida (10 km/h)', 30, 392)
    db.registrar_serie(hoje, 'Supino reto', 'Peito', 10, 40)
    db.iniciar_jejum('16:8', 16, datetime.now() - timedelta(hours=20))
    db.encerrar_jejum(1, datetime.now() - timedelta(hours=3))
    db.iniciar_jejum('16:8', 16, datetime.now() - timedelta(hours=2))  # em andamento


def abrir_app():
    # O caminho é absoluto porque o AppTest procura arquivos relativos à pasta tests/
    principal = Path(__file__).parent.parent / 'dashboard.py'
    return AppTest.from_file(str(principal), default_timeout=60).run()


@pytest.mark.parametrize('com_dados', [False, True], ids=['banco vazio', 'com dados'])
@pytest.mark.parametrize('pagina', PAGINAS)
def test_pagina_abre_sem_erro(pagina, com_dados):
    if com_dados:
        preencher_dados_de_exemplo()
    app = abrir_app()
    app.switch_page(pagina).run()
    assert not app.exception, [e.value for e in app.exception]


def test_salvar_alimento_pela_barra_lateral_aparece_no_dia():
    app = abrir_app()
    app.sidebar.text_input[0].set_value('banana prata').run()
    app.sidebar.button(key='btn_taco').click().run()
    assert not app.exception
    assert db.carregar_historico()['nome_alimento'].tolist() == ['Banana, prata, crua']
