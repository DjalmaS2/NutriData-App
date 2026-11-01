# Cálculo da meta calórica diária a partir do perfil do usuário

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
