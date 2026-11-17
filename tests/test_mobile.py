"""Regras do app Android (mobile/src/logica.py), que não dependem do Flet."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'mobile' / 'src'))

import api  # noqa: E402
import db  # noqa: E402
import logica  # noqa: E402


@pytest.mark.parametrize('texto, esperado', [
    ('150', 150), ('150,5', 150.5), (' 80.5 ', 80.5), ('0', None), ('-3', None), ('abc', None), ('', None),
])
def test_ler_gramas(texto, esperado):
    assert logica.ler_gramas(texto) == esperado


@pytest.mark.parametrize('hora, refeicao', [
    (6, 'Café da Manhã'), (9, 'Café da Manhã'), (10, 'Almoço'), (14, 'Almoço'),
    (15, 'Lanche'), (17, 'Lanche'), (18, 'Jantar'), (23, 'Jantar'),
])
def test_refeicao_pelo_horario(hora, refeicao):
    assert logica.refeicao_pelo_horario(hora) == refeicao


def test_prato_como_produto_registra_proporcional():
    # Prato inteiro de 400 g com 600 kcal: 200 g devem dar 300 kcal
    prato = {'nome_alimento': 'Marmita', 'porcao_g': 400,
             **{n: 0 for n in db.NUTRIENTES}, 'calorias': 600, 'proteinas': 40}
    produto = logica.prato_como_produto(prato, db.NUTRIENTES)
    assert produto['nome'] == 'Marmita'
    assert produto['calorias_100g'] == pytest.approx(150)
    porcao = api.calcular_porcao(produto, 200)
    assert porcao['calorias'] == pytest.approx(300)
    assert porcao['proteinas'] == pytest.approx(20)


def test_somar_ingredientes():
    ingredientes = [{'calorias': 192, 'proteinas': 3.8}, {'calorias': 76, 'proteinas': 4.8, 'fibras': 8.5}]
    total = logica.somar_ingredientes(ingredientes, db.NUTRIENTES)
    assert total['calorias'] == pytest.approx(268)
    assert total['proteinas'] == pytest.approx(8.6)
    assert total['fibras'] == pytest.approx(8.5)
    assert total['ferro'] == 0


def test_meta_do_dia_sem_perfil_usa_padrao():
    assert logica.meta_do_dia(None) == 2000


def test_validar_perfil_aceita_virgula_e_meta_vazia():
    valores, erros = logica.validar_perfil({'idade': '30', 'peso_kg': '80,5', 'altura_cm': '180', 'peso_meta': ''})
    assert erros == {}
    assert valores == {'idade': 30, 'peso_kg': 80.5, 'altura_cm': 180, 'peso_meta': None}


def test_validar_perfil_aponta_campos_fora_do_limite():
    _, erros = logica.validar_perfil({'idade': '5', 'peso_kg': 'abc', 'altura_cm': '180', 'peso_meta': '20'})
    assert set(erros) == {'idade', 'peso_kg', 'peso_meta'}


def test_calorias_por_dia_preenche_dias_vazios_e_resume():
    from datetime import date
    hoje = date(2026, 11, 17)
    db.salvar_consumo('Almoço', 'Arroz', 100, {'calorias': 500})
    historico = db.carregar_historico()
    historico['data_apenas'] = hoje  # o registro acima entra como sendo de "hoje"
    linhas = [historico, historico.assign(data_apenas=date(2026, 11, 15), calorias=2500)]
    import pandas as pd
    por_dia = logica.calorias_por_dia(pd.concat(linhas), hoje, 7)
    assert len(por_dia) == 7
    assert por_dia[0][0] == date(2026, 11, 11) and por_dia[-1] == (hoje, 500)
    assert dict(por_dia)[date(2026, 11, 16)] == 0
    resumo = logica.resumo_periodo(por_dia, meta=2000)
    assert resumo == {'media': 1500, 'dias_registrados': 2, 'dentro_da_meta': 1}


def test_texto_previsao():
    from datetime import date
    assert logica.texto_previsao(2, date(2026, 11, 17)) == 'cerca de 2 semanas (por volta de 01/12/2026)'
    assert logica.texto_previsao(0.5, date(2026, 11, 17)).startswith('menos de 1 semana')


def test_resumo_semana_ignora_treinos_antigos():
    from datetime import date
    hoje = date(2026, 11, 17)
    db.registrar_atividade(hoje, 'Yoga', 30, 100)
    db.registrar_atividade(date(2026, 11, 12), 'Pilates', 40, 120)
    db.registrar_atividade(date(2026, 11, 1), 'Dança', 60, 300)  # fora dos 7 dias
    assert logica.resumo_semana(db.carregar_atividades(), hoje) == {'dias': 2, 'minutos': 70, 'kcal': 220}


def test_inicio_pela_hora_usa_ontem_quando_a_hora_ainda_nao_chegou():
    from datetime import datetime, time
    agora = datetime(2026, 11, 17, 8, 30)
    assert logica.inicio_pela_hora(time(21, 0), agora) == datetime(2026, 11, 16, 21, 0)
    assert logica.inicio_pela_hora(time(7, 15), agora) == datetime(2026, 11, 17, 7, 15)
    assert logica.inicio_pela_hora(time(8, 30), agora) == agora


def test_resumo_jejuns():
    from datetime import datetime
    assert logica.resumo_jejuns(db.carregar_jejuns()) == {'total': 0, 'cumpridos': 0, 'media_horas': 0}
    db.iniciar_jejum('16:8', 16, datetime(2026, 11, 15, 20, 0))
    db.encerrar_jejum(1, datetime(2026, 11, 16, 14, 0))  # 18 h: cumpriu
    db.iniciar_jejum('16:8', 16, datetime(2026, 11, 16, 20, 0))
    db.encerrar_jejum(2, datetime(2026, 11, 17, 8, 0))  # 12 h: não cumpriu
    assert logica.resumo_jejuns(db.carregar_jejuns()) == {'total': 2, 'cumpridos': 1, 'media_horas': 15}
