# Atividades físicas e cálculo de calorias gastas
from datetime import timedelta

# MET = quantas vezes a atividade gasta mais energia que o repouso.
# Valores do Compêndio de Atividades Físicas (Ainsworth et al.).
ATIVIDADES_MET = {
    "Musculação (moderada)": 3.5,
    "Musculação (intensa)": 6.0,
    "Caminhada (5 km/h)": 3.5,
    "Caminhada rápida (6,5 km/h)": 5.0,
    "Corrida (8 km/h)": 8.3,
    "Corrida (10 km/h)": 9.8,
    "Bicicleta (moderada)": 7.0,
    "Bicicleta ergométrica (moderada)": 6.8,
    "Elíptico (moderado)": 5.0,
    "Natação (moderada)": 5.8,
    "Futebol (recreativo)": 7.0,
    "Dança": 5.0,
    "Funcional / HIIT": 8.0,
    "Pular corda": 11.8,
    "Pilates": 3.0,
    "Yoga": 2.5,
}


def calcular_kcal(atividade, minutos, peso_kg):
    """Calorias gastas = MET x peso (kg) x tempo (horas)."""
    return ATIVIDADES_MET[atividade] * peso_kg * minutos / 60


def sequencia_dias(dias, hoje):
    """Quantos dias seguidos têm registro, contando de hoje para trás.

    Se hoje ainda não tem registro, a sequência de ontem continua valendo
    (o dia ainda não acabou), então a contagem começa de ontem.
    """
    dia = hoje if hoje in dias else hoje - timedelta(days=1)
    contagem = 0
    while dia in dias:
        contagem += 1
        dia -= timedelta(days=1)
    return contagem
