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
