import difflib
import re
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


def _palavras(texto):
    """'Feijão, carioca, cozido' -> ['feijao', 'carioca', 'cozido']"""
    return re.findall(r'[a-z0-9]+', _normalizar(texto))


def buscar(termo, limite=30):
    """Retorna os alimentos cujo nome contém todas as palavras digitadas."""
    palavras = _palavras(termo)
    df = carregar_tabela()
    if not palavras:
        return df.iloc[0:0]
    filtro = pd.Series(True, index=df.index)
    for palavra in palavras:
        filtro &= df['busca'].str.contains(palavra, regex=False)
    encontrados = df[filtro]
    # Primeiro os nomes que começam com a 1ª palavra ("Feijão, carioca" antes de "Baião de dois, ... feijão")
    comeca = ~encontrados['busca'].str.startswith(palavras[0])
    return encontrados.assign(_ordem=comeca).sort_values('_ordem', kind='stable').drop(columns='_ordem').head(limite)


@lru_cache(maxsize=1)
def _vocabulario():
    """Todas as palavras dos nomes da TACO: sem acento -> como aparece no nome (com acento)."""
    vocabulario = {}
    for nome in carregar_tabela()['nome']:
        for original in re.findall(r'\w+', nome.lower()):
            vocabulario.setdefault(_normalizar(original), original)
    return vocabulario


def corrigir_termo(termo):
    """Troca as palavras com erro de digitação pela palavra mais parecida da TACO.

    'feisao carioca' -> 'feijão carioca'. Palavras que já aparecem em algum nome
    (inteiras ou como começo/pedaço, ex.: 'fei') ficam como estão. Retorna None
    quando não há nada para corrigir.
    """
    vocabulario = _vocabulario()
    corrigidas, mudou = [], False
    for palavra in _palavras(termo):
        if any(palavra in conhecida for conhecida in vocabulario):
            corrigidas.append(palavra)
            continue
        # cutoff 0.7: parecida o bastante para ser erro de digitação, não outra palavra
        parecidas = difflib.get_close_matches(palavra, vocabulario, n=1, cutoff=0.7)
        if not parecidas:
            return None
        corrigidas.append(vocabulario[parecidas[0]])
        mudou = True
    return ' '.join(corrigidas) if mudou else None


def buscar_aproximado(termo, limite=30):
    """Busca normal; se não achar nada, tenta corrigir erros de digitação.

    Retorna (resultados, termo_corrigido). termo_corrigido é None quando a busca
    normal funcionou ou quando não foi possível corrigir.
    """
    resultados = buscar(termo, limite)
    if not resultados.empty:
        return resultados, None
    correcao = corrigir_termo(termo)
    if correcao is None:
        return resultados, None
    return buscar(correcao, limite), correcao


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
