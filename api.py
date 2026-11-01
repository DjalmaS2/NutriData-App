import requests

URL_PRODUTO = "https://world.openfoodfacts.org/api/v2/product/{codigo}.json"
CAMPOS = "product_name,nutriments"
# O Open Food Facts pede que cada app se identifique
HEADERS = {"User-Agent": "NutriData/1.0 (app de estudo)"}


class ErroAPI(Exception):
    """Falha de rede ou resposta inesperada da API (diferente de 'produto não existe')."""


def buscar_produto(codigo_barras):
    """Retorna um dict com nome e nutrientes por 100g, ou None se o produto não existir."""
    codigo = str(codigo_barras).strip()
    if not codigo.isdigit():
        return None

    try:
        resposta = requests.get(
            URL_PRODUTO.format(codigo=codigo),
            params={"fields": CAMPOS},
            headers=HEADERS,
            timeout=10,
        )
    except requests.RequestException as erro:
        raise ErroAPI("Não foi possível conectar ao Open Food Facts.") from erro

    # Na v2, produto inexistente volta como 404 com status 0
    if resposta.status_code == 404:
        return None
    if resposta.status_code != 200:
        raise ErroAPI(f"A API respondeu com erro HTTP {resposta.status_code}.")

    dados = resposta.json()
    if dados.get('status') != 1:
        return None

    produto = dados['product']
    nutrientes = produto.get('nutriments', {})
    return {
        'nome': produto.get('product_name') or 'Nome Desconhecido',
        # "or 0" cobre campos ausentes e campos que vêm como None
        'calorias_100g': nutrientes.get('energy-kcal_100g') or 0,
        'carboidratos_100g': nutrientes.get('carbohydrates_100g') or 0,
        'proteinas_100g': nutrientes.get('proteins_100g') or 0,
        'gorduras_100g': nutrientes.get('fat_100g') or 0,
        'sodio_100g': nutrientes.get('sodium_100g') or 0,  # em gramas
    }


def calcular_porcao(produto, peso):
    """Converte os valores por 100g para o peso realmente consumido."""
    fator = float(peso) / 100
    return {
        'calorias': produto['calorias_100g'] * fator,
        'carboidratos': produto['carboidratos_100g'] * fator,
        'proteinas': produto['proteinas_100g'] * fator,
        'gorduras': produto['gorduras_100g'] * fator,
        'sodio': produto['sodio_100g'] * fator,
    }
