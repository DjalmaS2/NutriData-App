from datetime import date, timedelta

import pytest

import exercicios
import metas

PERFIL_EXEMPLO = {
    'sexo': 'Masculino', 'idade': 30, 'peso_kg': 80, 'altura_cm': 180,
    'atividade': 'Moderado (exercício 3-5x por semana)', 'objetivo': 'Perder peso',
}


# --- Meta calórica ---

def test_tmb_masculino():
    # 10 x 80 + 6,25 x 180 - 5 x 30 + 5
    assert metas.calcular_tmb(80, 180, 30, 'Masculino') == 1780


def test_tmb_feminino():
    # 10 x 60 + 6,25 x 165 - 5 x 25 - 161
    assert metas.calcular_tmb(60, 165, 25, 'Feminino') == pytest.approx(1345.25)


def test_meta_perder_peso():
    calculo = metas.calcular_meta(PERFIL_EXEMPLO)
    assert calculo['gasto'] == pytest.approx(1780 * 1.55)
    assert calculo['meta'] == pytest.approx(1780 * 1.55 - 500)


def test_meta_nunca_abaixo_do_minimo():
    perfil = dict(PERFIL_EXEMPLO, sexo='Feminino', peso_kg=40, altura_cm=145, idade=70,
                  atividade='Sedentário (pouco ou nenhum exercício)')
    assert metas.calcular_meta(perfil)['meta'] == metas.META_MINIMA


# --- Macros e água ---

def test_macros_sem_peso_usam_percentuais():
    macros = metas.calcular_macros(2000)
    assert macros['proteinas'] == pytest.approx(100)       # 20% de 2000 / 4
    assert macros['gorduras'] == pytest.approx(2000 * 0.25 / 9)
    assert macros['carboidratos'] == pytest.approx(275)


@pytest.mark.parametrize('meta, peso', [(2259, 80), (1500, 150), (3000, 60)])
def test_macros_somam_a_meta(meta, peso):
    # proteína e carboidrato têm 4 kcal/g; gordura, 9 kcal/g
    m = metas.calcular_macros(meta, peso)
    assert m['proteinas'] * 4 + m['gorduras'] * 9 + m['carboidratos'] * 4 == pytest.approx(meta)


def test_proteina_limitada_a_35_por_cento():
    # 1,6 g/kg daria 240 g, mas o limite é 35% das calorias
    assert metas.calcular_macros(1500, 150)['proteinas'] == pytest.approx(1500 * 0.35 / 4)


def test_meta_de_agua():
    assert metas.meta_agua_ml(80) == 2800
    assert metas.meta_agua_ml(None) == 2000


# --- Exercícios ---

def test_calorias_da_corrida():
    # MET 9,8 x 80 kg x 0,5 h
    assert exercicios.calcular_kcal('Corrida (10 km/h)', 30, 80) == pytest.approx(392)


def test_todo_exercicio_da_biblioteca_tem_grupo():
    todos = [e for lista in exercicios.BIBLIOTECA.values() for e in lista]
    assert len(todos) == len(set(todos)), "exercício repetido em dois grupos"


HOJE = date(2026, 11, 2)


def dias_atras(*quantos):
    return {HOJE - timedelta(days=n) for n in quantos}


@pytest.mark.parametrize('dias, esperado', [
    (dias_atras(0, 1, 2), 3),     # hoje e os dois dias anteriores
    (dias_atras(1, 2), 2),        # hoje ainda sem registro: a sequência de ontem vale
    (dias_atras(0, 2, 3), 1),     # ontem quebrou a sequência
    (dias_atras(2, 3), 0),        # ontem e hoje sem registro
    (set(), 0),
])
def test_sequencia_de_dias(dias, esperado):
    assert exercicios.sequencia_dias(dias, HOJE) == esperado
