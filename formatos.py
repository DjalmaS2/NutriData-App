# Partes sem Streamlit usadas pelo app web (comum.py) e pelo app Android (mobile/)
REFEICOES = ["Café da Manhã", "Almoço", "Lanche", "Jantar"]
ICONES_REFEICOES = {"Café da Manhã": "☀️", "Almoço": "🍛", "Lanche": "🍎", "Jantar": "🌙"}


def num(valor, casas=1, sinal=False, enxuto=False):
    """Número no formato brasileiro: 1234.5 -> '1.234,5'.

    sinal=True mostra + ou - (variações). enxuto=True tira o ',0' de números
    inteiros (75.0 -> '75', 75.5 -> '75,5').
    """
    texto = f"{valor:{'+' if sinal else ''},.{casas}f}"
    # Troca os separadores do padrão americano (1,234.5) pelos brasileiros (1.234,5)
    texto = texto.replace(',', '_').replace('.', ',').replace('_', '.')
    if enxuto and casas > 0:
        texto = texto.rstrip('0').rstrip(',')
    return texto
