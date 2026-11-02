# Cálculo da meta calórica diária a partir do perfil do usuário
import pandas as pd


# Multiplicador do gasto calórico conforme o nível de atividade física
FATORES_ATIVIDADE = {
    "Sedentário (pouco ou nenhum exercício)": 1.2,
    "Leve (exercício 1-3x por semana)": 1.375,
    "Moderado (exercício 3-5x por semana)": 1.55,
    "Intenso (exercício 6-7x por semana)": 1.725,
    "Muito intenso (atleta ou trabalho físico pesado)": 1.9,
}

# Quanto somar ou tirar do gasto diário para cada objetivo (kcal)
AJUSTE_OBJETIVO = {
    "Perder peso": -500,
    "Manter peso": 0,
    "Ganhar massa": 300,
}

# Abaixo disso a dieta deve ser acompanhada por um profissional
META_MINIMA = 1200


def calcular_tmb(peso_kg, altura_cm, idade, sexo):
    """Taxa Metabólica Basal pela fórmula de Mifflin-St Jeor: o gasto do corpo em repouso."""
    tmb = 10 * peso_kg + 6.25 * altura_cm - 5 * idade
    return tmb + 5 if sexo == "Masculino" else tmb - 161


def calcular_meta(perfil):
    """Recebe o perfil (dict do db.carregar_perfil) e retorna TMB, gasto diário e meta."""
    tmb = calcular_tmb(perfil['peso_kg'], perfil['altura_cm'], perfil['idade'], perfil['sexo'])
    gasto = tmb * FATORES_ATIVIDADE[perfil['atividade']]
    meta = max(gasto + AJUSTE_OBJETIVO[perfil['objetivo']], META_MINIMA)
    return {'tmb': tmb, 'gasto': gasto, 'meta': meta}


# Proteína em gramas por kg de peso; 1,6 g/kg ajuda a preservar músculo ao perder peso
PROTEINA_G_POR_KG = 1.6
# Fatia das calorias que vem de gordura
PERCENTUAL_GORDURA = 0.25


def calcular_macros(meta_kcal, peso_kg=None):
    """Divide a meta calórica em gramas de proteína, gordura e carboidrato.

    Cada grama de proteína ou carboidrato tem 4 kcal e cada grama de gordura, 9 kcal.
    """
    if peso_kg:
        # Limite de 35% das calorias, para pessoas pesadas não ficarem com proteína demais
        proteinas = min(PROTEINA_G_POR_KG * peso_kg, meta_kcal * 0.35 / 4)
    else:
        proteinas = meta_kcal * 0.20 / 4
    gorduras = meta_kcal * PERCENTUAL_GORDURA / 9
    # O carboidrato completa o que sobra das calorias
    carboidratos = max(meta_kcal - proteinas * 4 - gorduras * 9, 0) / 4
    return {'proteinas': proteinas, 'gorduras': gorduras, 'carboidratos': carboidratos}


def meta_agua_ml(peso_kg=None):
    """Recomendação comum: 35 ml por kg de peso; sem perfil, 2 litros."""
    return 35 * peso_kg if peso_kg else 2000


# Valores Diários de Referência para adultos da ANVISA (IN 75/2020, a mesma base dos rótulos).
# Para fibras, cálcio, ferro e vitamina C é uma meta; para o potássio, uma referência de consumo.
VALORES_DIARIOS = {
    'fibras': {'nome': 'Fibras', 'icone': '🌾', 'valor': 25, 'unidade': 'g'},
    'calcio': {'nome': 'Cálcio', 'icone': '🦴', 'valor': 1000, 'unidade': 'mg'},
    'ferro': {'nome': 'Ferro', 'icone': '🩸', 'valor': 14, 'unidade': 'mg'},
    'vitamina_c': {'nome': 'Vitamina C', 'icone': '🍊', 'valor': 100, 'unidade': 'mg'},
    'potassio': {'nome': 'Potássio', 'icone': '🍌', 'valor': 3500, 'unidade': 'mg'},
}


# --- Meta de peso ---
# Aproximação usada em nutrição: perder ou ganhar 1 kg de peso corporal ~ 7700 kcal
KCAL_POR_KG = 7700


def semanas_pelo_plano(peso_atual, peso_meta, ajuste_kcal_dia):
    """Semanas até a meta seguindo o déficit (ou superávit) diário do objetivo.

    Retorna None quando o plano não leva à meta: objetivo "manter" (ajuste 0) ou
    objetivo no sentido contrário (ex.: meta abaixo do peso atual, mas objetivo ganhar massa).
    """
    diferenca = peso_meta - peso_atual
    if diferenca == 0:
        return 0
    if ajuste_kcal_dia == 0 or (diferenca > 0) != (ajuste_kcal_dia > 0):
        return None
    return abs(diferenca) * KCAL_POR_KG / abs(ajuste_kcal_dia) / 7


def ritmo_real_kg_semana(pesos):
    """Tendência das pesagens em kg por semana (reta que melhor passa pelos pontos).

    pesos: DataFrame com colunas 'data' (date) e 'peso_kg'. Precisa de pelo menos
    2 pesagens com 7 dias ou mais entre a primeira e a última; senão retorna None.
    """
    if len(pesos) < 2:
        return None
    dias = pd.Series([(d - pesos['data'].iloc[0]).days for d in pesos['data']], dtype=float)
    if dias.iloc[-1] - dias.iloc[0] < 7:
        return None
    # Inclinação da reta de mínimos quadrados: kg por dia
    inclinacao = ((dias - dias.mean()) * (pesos['peso_kg'] - pesos['peso_kg'].mean())).sum() \
        / ((dias - dias.mean()) ** 2).sum()
    return inclinacao * 7


def semanas_pelo_ritmo(peso_atual, peso_meta, kg_por_semana):
    """Semanas até a meta mantendo o ritmo atual; None se o ritmo não leva até lá."""
    diferenca = peso_meta - peso_atual
    if diferenca == 0:
        return 0
    if not kg_por_semana or (diferenca > 0) != (kg_por_semana > 0):
        return None
    return diferenca / kg_por_semana
