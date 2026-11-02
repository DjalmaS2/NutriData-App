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

    def valor(campo, multiplicador=1):
        # "or 0" cobre campos ausentes e campos que vêm como None
        return float(nutrientes.get(campo) or 0) * multiplicador

    # A API manda minerais e vitaminas em gramas; aqui viram mg (x 1000)
    return {
        'nome': produto.get('product_name') or 'Nome Desconhecido',
        'calorias_100g': valor('energy-kcal_100g'),
        'carboidratos_100g': valor('carbohydrates_100g'),
        'proteinas_100g': valor('proteins_100g'),
        'gorduras_100g': valor('fat_100g'),
        'sodio_100g': valor('sodium_100g'),  # em gramas
        'fibras_100g': valor('fiber_100g'),
        'calcio_100g': valor('calcium_100g', 1000),
        'ferro_100g': valor('iron_100g', 1000),
        'vitamina_c_100g': valor('vitamin-c_100g', 1000),
        'potassio_100g': valor('potassium_100g', 1000),
    }


def calcular_porcao(produto, peso):
    """Converte os valores por 100g para o peso realmente consumido.

    Funciona para qualquer chave terminada em "_100g": 'calorias_100g' vira 'calorias'.
    """
    fator = float(peso) / 100
    return {chave.removesuffix('_100g'): valor * fator
            for chave, valor in produto.items() if chave.endswith('_100g')}
