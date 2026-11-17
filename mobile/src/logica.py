# Pequenas regras do app mobile que não dependem do Flet (por isso dá para testar no pytest)
from formatos import REFEICOES


def ler_gramas(texto):
    """'150' ou '150,5' -> número; None se não for um peso válido."""
    try:
        valor = float(str(texto).strip().replace(',', '.'))
    except ValueError:
        return None
    return valor if valor > 0 else None


def refeicao_pelo_horario(hora):
    """Refeição mais provável para a hora do dia (0 a 23)."""
    if hora < 10:
        return REFEICOES[0]  # Café da Manhã
    if hora < 15:
        return REFEICOES[1]  # Almoço
    if hora < 18:
        return REFEICOES[2]  # Lanche
    return REFEICOES[3]      # Jantar


def prato_como_produto(prato, nutrientes):
    """Converte um prato salvo (valores do prato inteiro) para valores por 100 g.

    Assim o prato entra no mesmo cálculo dos alimentos (api.calcular_porcao).
    prato: dict/linha com nome_alimento, porcao_g e os nutrientes; nutrientes: db.NUTRIENTES.
    """
    fator = 100 / prato['porcao_g'] if prato['porcao_g'] else 0
    produto = {'nome': prato['nome_alimento']}
    for nutriente in nutrientes:
        produto[f'{nutriente}_100g'] = float(prato[nutriente] or 0) * fator
    return produto


def somar_ingredientes(ingredientes, nutrientes):
    """Soma os nutrientes de uma lista de ingredientes (cada um com os valores já da porção)."""
    return {n: sum(float(i.get(n, 0)) for i in ingredientes) for n in nutrientes}
