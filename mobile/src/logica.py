# Pequenas regras do app mobile que não dependem do Flet (por isso dá para testar no pytest)
from datetime import datetime, timedelta

import metas
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


# --- Metas e perfil ---
META_PADRAO = 2000  # kcal por dia quando o perfil ainda não foi preenchido

# Limites aceitos no formulário do perfil (os mesmos do app web)
LIMITES_PERFIL = {'idade': (14, 100), 'peso_kg': (30, 300), 'altura_cm': (100, 230)}
NOMES_CAMPOS = {'idade': 'Idade', 'peso_kg': 'Peso', 'altura_cm': 'Altura', 'peso_meta': 'Meta de peso'}


def meta_do_dia(perfil):
    """Meta calórica (sem exercícios) pelo perfil, ou a padrão."""
    return round(metas.calcular_meta(perfil)['meta']) if perfil else META_PADRAO


def validar_perfil(textos):
    """Converte os campos digitados do perfil (texto) em números.

    textos: dict com idade, peso_kg, altura_cm e peso_meta (este pode ficar vazio).
    Retorna (valores, erros): erros é um dict campo -> mensagem (vazio se deu tudo certo).
    """
    valores, erros = {}, {}
    for campo in ['idade', 'peso_kg', 'altura_cm', 'peso_meta']:
        texto = str(textos.get(campo) or '').strip()
        if campo == 'peso_meta' and not texto:
            valores[campo] = None  # meta de peso é opcional
            continue
        numero = ler_gramas(texto)  # mesmo formato: aceita vírgula, precisa ser maior que zero
        minimo, maximo = LIMITES_PERFIL.get(campo, LIMITES_PERFIL['peso_kg'])
        if numero is None or not minimo <= numero <= maximo:
            erros[campo] = f'De {minimo} a {maximo}'
            continue
        valores[campo] = int(round(numero)) if campo == 'idade' else numero
    return valores, erros


# --- Histórico ---
def calorias_por_dia(historico, hoje, dias):
    """Lista de (data, kcal) dos últimos `dias` dias até hoje; dias sem registro entram com 0."""
    somas = historico.groupby('data_apenas')['calorias'].sum().to_dict() if not historico.empty else {}
    periodo = [hoje - timedelta(days=n) for n in range(dias - 1, -1, -1)]
    return [(dia, float(somas.get(dia, 0))) for dia in periodo]


def resumo_periodo(por_dia, meta):
    """Média (só dos dias com registro), dias registrados e dias dentro da meta."""
    registrados = [kcal for _, kcal in por_dia if kcal > 0]
    return {
        'media': sum(registrados) / len(registrados) if registrados else 0,
        'dias_registrados': len(registrados),
        'dentro_da_meta': sum(1 for kcal in registrados if kcal <= meta),
    }


def texto_previsao(semanas, hoje):
    """'cerca de 12 semanas (por volta de 25/01/2027)'"""
    data = hoje + timedelta(weeks=semanas)
    quanto = 'menos de 1 semana' if semanas < 1 else f'cerca de {semanas:.0f} semanas'
    return f'{quanto} (por volta de {data:%d/%m/%Y})'


# --- Treino ---
def resumo_semana(atividades, hoje):
    """Dias com treino, minutos e kcal dos últimos 7 dias (atividades: DataFrame do db)."""
    inicio = hoje - timedelta(days=6)
    semana = atividades[(atividades['data'] >= inicio) & (atividades['data'] <= hoje)]
    return {'dias': int(semana['data'].nunique()), 'minutos': float(semana['minutos'].sum()),
            'kcal': float(semana['kcal'].sum())}


# --- Jejum ---
def inicio_pela_hora(hora, agora):
    """Início do jejum a partir só da hora (datetime.time) da última refeição.

    Se a hora ainda não chegou hoje, a refeição foi ontem (ex.: às 8h, '21:00' é ontem às 21h).
    """
    inicio = datetime.combine(agora.date(), hora)
    return inicio - timedelta(days=1) if inicio > agora else inicio


def resumo_jejuns(jejuns):
    """Total de jejuns concluídos, quantos cumpriram a meta e a duração média (horas)."""
    if jejuns.empty:
        return {'total': 0, 'cumpridos': 0, 'media_horas': 0}
    return {'total': len(jejuns), 'cumpridos': int((jejuns['horas'] >= jejuns['meta_horas']).sum()),
            'media_horas': float(jejuns['horas'].mean())}
