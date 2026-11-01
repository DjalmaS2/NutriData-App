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
