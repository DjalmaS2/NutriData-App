# Cores, fontes e peças visuais repetidas do app (identidade visual do NutriData)
import flet as ft

# --- Cores ---
VERDE = '#2F9E6A'          # verde-folha: consumido, dentro da meta
VERDE_ESCURO = '#23794F'   # botões e textos em verde (mais contraste)
VERDE_CLARO = '#E6F3EC'    # fundo dos botões redondos de "+"
FUNDO = '#FAF8F3'          # creme
CARTAO = '#FFFFFF'
BORDA = '#E2DCCF'
TRILHO = '#EFEBE1'         # parte "vazia" das barras e do anel
TEXTO = '#1F2A24'
TEXTO_SUAVE = '#5E6B63'
EXCEDIDO = '#E4572E'       # tomate: acima da meta
CARBOIDRATOS = '#E9A23B'
PROTEINAS = '#C8507A'
GORDURAS = '#3A8FB7'
AGUA_FUNDO = '#E3F0F6'
AGUA_TEXTO = '#2C6F8F'
SEQUENCIA_FUNDO = '#FCEBD3'
SEQUENCIA_TEXTO = '#8A4B0B'

# --- Fontes (arquivos em src/assets/fonts) ---
# O Flet registra um arquivo por nome de fonte, então cada peso tem o seu nome
FONTES = {
    'DM Sans': 'fonts/DMSans-Regular.ttf',
    'DM Sans Medium': 'fonts/DMSans-Medium.ttf',
    'DM Sans Bold': 'fonts/DMSans-Bold.ttf',
    'Fraunces': 'fonts/Fraunces-Bold.ttf',
    'Fraunces SemiBold': 'fonts/Fraunces-SemiBold.ttf',
}


def aplicar(page: ft.Page):
    """Configura fontes, cores e tema claro da página."""
    page.fonts = FONTES
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = FUNDO
    page.theme = ft.Theme(
        color_scheme_seed=VERDE,
        font_family='DM Sans',
        color_scheme=ft.ColorScheme(primary=VERDE_ESCURO, surface=FUNDO, on_surface=TEXTO),
        scaffold_bgcolor=FUNDO,
    )


def texto(valor, tamanho=14, peso='normal', cor=TEXTO, **extras):
    """Texto em DM Sans. peso: 'normal', 'medio' ou 'negrito'."""
    familia = {'normal': 'DM Sans', 'medio': 'DM Sans Medium', 'negrito': 'DM Sans Bold'}[peso]
    return ft.Text(valor, size=tamanho, font_family=familia, color=cor, **extras)


def titulo(valor, tamanho=30, semi=False, color=TEXTO, **extras):
    """Títulos em Fraunces (a fonte serifada da marca)."""
    familia = 'Fraunces SemiBold' if semi else 'Fraunces'
    return ft.Text(valor, size=tamanho, font_family=familia, color=color, **extras)


def cartao(conteudo, raio=20, padding=16):
    """Caixa branca com borda clara e cantos arredondados."""
    return ft.Container(
        content=conteudo,
        bgcolor=CARTAO,
        border=ft.Border.all(1, BORDA),
        border_radius=raio,
        padding=padding,
    )


def barra(fracao, cor, altura=6):
    """Barra de progresso fina (fracao de 0 a 1; acima de 1 fica cheia)."""
    return ft.ProgressBar(value=max(0.0, min(fracao, 1.0)), color=cor, bgcolor=TRILHO,
                          bar_height=altura, border_radius=999)
