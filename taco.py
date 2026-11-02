import unicodedata
from functools import lru_cache
from pathlib import Path

import pandas as pd

# Tabela TACO (Unicamp), convertida de github.com/marcelosanto/tabela_taco (MIT).
# Valores por 100g; "traço" e "não analisado" foram gravados como 0.
CAMINHO_TACO = Path(__file__).parent / 'dados' / 'taco.csv'


def _normalizar(texto):
    """Minúsculas e sem acento, para 'feijao' encontrar 'Feijão'."""
    sem_acento = unicodedata.normalize('NFKD', str(texto)).encode('ascii', 'ignore').decode()
    return sem_acento.lower()


@lru_cache(maxsize=1)
def carregar_tabela():
    # lru_cache faz o CSV ser lido só uma vez, mesmo com o Streamlit rodando o script várias vezes
    df = pd.read_csv(CAMINHO_TACO)
    df['busca'] = df['nome'].map(_normalizar)
    return df


def buscar(termo, limite=30):
    """Retorna os alimentos cujo nome contém todas as palavras digitadas."""
    palavras = _normalizar(termo).replace(',', ' ').split()
    df = carregar_tabela()
    if not palavras:
        return df.iloc[0:0]
    filtro = pd.Series(True, index=df.index)
    for palavra in palavras:
        filtro &= df['busca'].str.contains(palavra, regex=False)
    return df[filtro].head(limite)


def como_produto(linha):
    """Converte uma linha da TACO para o mesmo formato de api.buscar_produto."""
    return {
        'nome': linha['nome'],
        'calorias_100g': linha['calorias_100g'],
        'carboidratos_100g': linha['carboidratos_100g'],
        'proteinas_100g': linha['proteinas_100g'],
        'gorduras_100g': linha['gorduras_100g'],
        'sodio_100g': linha['sodio_mg_100g'] / 1000,  # mg -> g, igual à API
        'fibras_100g': linha['fibras_g_100g'],
        'calcio_100g': linha['calcio_mg_100g'],
        'ferro_100g': linha['ferro_mg_100g'],
        'vitamina_c_100g': linha['vitamina_c_mg_100g'],
        'potassio_100g': linha['potassio_mg_100g'],
    }
