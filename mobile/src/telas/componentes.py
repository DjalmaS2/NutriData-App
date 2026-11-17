# Peças usadas em mais de uma tela: busca na TACO, porção com prévia e botões de escolha
import flet as ft

import api
import taco
import tema
from formatos import num
from logica import ler_gramas


def item_alimento(nome, detalhe, kcal, ao_tocar, marcado=False, final=None):
    """Cartão clicável de um alimento: nome, detalhe (macros) e kcal à direita."""
    direita = [tema.texto(kcal, 15, 'negrito', no_wrap=True)]
    if final is not None:
        direita.append(final)
    return ft.Container(
        content=ft.Row(
            [ft.Column([tema.texto(nome, 15, 'negrito', max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                        tema.texto(detalhe, 12, cor=tema.TEXTO_SUAVE)], spacing=2, expand=True),
             ft.Row(direita, spacing=4, tight=True)],
            spacing=12,
        ),
        padding=ft.Padding.symmetric(vertical=12, horizontal=16),
        border_radius=16,
        border=ft.Border.all(1.5, tema.VERDE if marcado else tema.BORDA),
        bgcolor=tema.CARTAO,
        ink=True,
        on_click=ao_tocar,
    )


def macros_por_100g(produto):
    return (f"C {num(produto['carboidratos_100g'])} g · P {num(produto['proteinas_100g'])} g · "
            f"G {num(produto['gorduras_100g'])} g")


def pilulas(opcoes, escolhida, ao_escolher):
    """Botões arredondados lado a lado; o escolhido fica verde (ex.: as refeições)."""
    botoes = []
    for opcao in opcoes:
        ativo = opcao == escolhida
        botoes.append(ft.Container(
            content=tema.texto(opcao, 14, 'negrito', ft.Colors.WHITE if ativo else tema.TEXTO),
            padding=ft.Padding.symmetric(vertical=12, horizontal=16),
            border_radius=999, bgcolor=tema.VERDE_ESCURO if ativo else tema.CARTAO,
            border=ft.Border.all(1, tema.VERDE_ESCURO if ativo else tema.BORDA),
            ink=True, on_click=lambda e, o=opcao: ao_escolher(o),
        ))
    return ft.Row(botoes, spacing=8, wrap=True, run_spacing=8)


def segmentos(opcoes, escolhida, ao_escolher):
    """Seletor de abas em formato de pílula (Buscar | Código de barras | Meus pratos)."""
    partes = []
    for opcao in opcoes:
        ativo = opcao == escolhida
        partes.append(ft.Container(
            content=tema.texto(opcao, 13, 'negrito' if ativo else 'medio',
                               tema.TEXTO if ativo else tema.TEXTO_SUAVE, text_align=ft.TextAlign.CENTER),
            height=40, expand=True, alignment=ft.Alignment.CENTER, border_radius=999,
            bgcolor=tema.CARTAO if ativo else None,
            ink=True, on_click=lambda e, o=opcao: ao_escolher(o),
        ))
    return ft.Container(ft.Row(partes, spacing=4), padding=4, border_radius=999, bgcolor='#F0ECE2')


def campo(rotulo, **extras):
    """Campo de texto no estilo do app (fundo branco, borda arredondada)."""
    return ft.TextField(label=rotulo, bgcolor=tema.CARTAO, border=tema.borda_campo(), text_size=16, **extras)


class BuscaTaco:
    """Campo de busca na Tabela TACO + lista de resultados (com correção de erros de digitação).

    ao_escolher(produto) é chamado quando a pessoa toca num resultado; produto vem no
    mesmo formato de api.buscar_produto (valores por 100 g).
    """

    def __init__(self, ao_escolher, rotulo='Buscar na Tabela TACO'):
        self.ao_escolher = ao_escolher
        self.id_marcado = None
        self.resultados = None
        self.campo = campo(rotulo, prefix_icon=ft.Icons.SEARCH, hint_text='ex: arroz cozido, feijão',
                           on_change=self._buscar, on_submit=self._buscar)
        self.aviso = tema.texto('', 13, cor=tema.TEXTO_SUAVE, visible=False)
        self.lista = ft.Column(spacing=10)
        # Depois de escolher, a lista mostra só o escolhido (o painel da porção fica logo abaixo)
        self.recolhida = False
        self.botao_outros = ft.TextButton('Ver os outros resultados', icon=ft.Icons.EXPAND_MORE,
                                          on_click=self._expandir, visible=False)
        self.raiz = ft.Column([self.campo, self.aviso, self.lista, self.botao_outros], spacing=12,
                              horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    def _buscar(self, e=None):
        termo = self.campo.value or ''
        self.id_marcado = None
        self.recolhida = False
        if len(termo.strip()) < 2:
            self.resultados = None
            self.aviso.visible = False
            self.lista.controls = []
            return
        resultados, correcao = taco.buscar_aproximado(termo)
        self.resultados = resultados
        self.aviso.visible = True
        if resultados.empty:
            self.aviso.value = 'Nenhum alimento encontrado. Tente outra palavra.'
        else:
            quantos = f"{len(resultados)} {'resultado' if len(resultados) == 1 else 'resultados'}"
            self.aviso.value = (f'Mostrando resultados para "{correcao}" · ' if correcao else '') + \
                f'{quantos} · valores por 100 g'
        self._desenhar()

    def _desenhar(self):
        self.lista.controls = []
        self.botao_outros.visible = self.recolhida and self.resultados is not None and len(self.resultados) > 1
        if self.resultados is None:
            return
        for linha in self.resultados.itertuples():
            if self.recolhida and linha.id != self.id_marcado:
                continue
            produto = taco.como_produto(linha._asdict())
            self.lista.controls.append(item_alimento(
                linha.nome, macros_por_100g(produto), f'{num(linha.calorias_100g, 0)} kcal',
                ao_tocar=lambda e, l=linha, p=produto: self._escolher(l.id, p),
                marcado=linha.id == self.id_marcado,
            ))

    def _escolher(self, id_linha, produto):
        self.id_marcado = id_linha
        self.recolhida = True
        self._desenhar()
        self.ao_escolher(produto)

    def _expandir(self, e=None):
        self.recolhida = False
        self._desenhar()

    def limpar(self):
        self.campo.value = ''
        self._buscar()


class PainelPorcao:
    """'Quanto você comeu?': gramas com − e + e a prévia de kcal e macros."""

    PASSO = 10

    def __init__(self, titulo='Quanto você comeu?', ao_mudar=None):
        self.produto = None
        self.ao_mudar = ao_mudar
        self.nome = tema.texto('', 15, 'negrito')
        self.campo_gramas = ft.TextField(
            value='100', width=120, text_align=ft.TextAlign.CENTER, keyboard_type=ft.KeyboardType.NUMBER,
            suffix='g', border=ft.UnderlineInputBorder(),
            text_style=ft.TextStyle(size=30, font_family='Fraunces', color=tema.TEXTO),
            on_change=lambda e: self._atualizar(),
        )
        self.valores = {chave: tema.texto('0', 18, 'negrito', cor)
                        for chave, cor in [('calorias', tema.TEXTO), ('carboidratos', '#9A5B0E'),
                                           ('proteinas', '#A33B62'), ('gorduras', tema.AGUA_TEXTO)]}
        rotulos = {'calorias': 'kcal', 'carboidratos': 'carb (g)', 'proteinas': 'prot (g)', 'gorduras': 'gord (g)'}

        def botao(simbolo, delta, descricao):
            return ft.IconButton(simbolo, on_click=lambda e: self._somar(delta), tooltip=descricao,
                                 icon_color=tema.TEXTO, bgcolor=tema.FUNDO, width=48, height=48,
                                 style=ft.ButtonStyle(side=ft.BorderSide(1, tema.BORDA)))

        self.raiz = tema.cartao(ft.Column([
            tema.texto(titulo, 13, cor=tema.TEXTO_SUAVE),
            self.nome,
            ft.Row([botao(ft.Icons.REMOVE, -self.PASSO, 'Diminuir 10 gramas'), self.campo_gramas,
                    botao(ft.Icons.ADD, self.PASSO, 'Aumentar 10 gramas')],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([ft.Column([self.valores[c], tema.texto(rotulos[c], 11, cor=tema.TEXTO_SUAVE)],
                              spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True)
                    for c in self.valores]),
        ], spacing=12))
        self.raiz.visible = False
        self.raiz.key = ft.ScrollKey('porcao')  # para a tela conseguir rolar até aqui

    @property
    def gramas(self):
        return ler_gramas(self.campo_gramas.value)

    def mostrar(self, produto, gramas=100):
        self.produto = produto
        self.nome.value = produto['nome']
        self.campo_gramas.value = num(gramas, 1, enxuto=True).replace('.', '')
        self.raiz.visible = True
        self._atualizar()

    def esconder(self):
        self.produto = None
        self.raiz.visible = False

    def porcao(self):
        """Nutrientes da porção escolhida (None se o peso for inválido)."""
        if self.produto is None or not self.gramas:
            return None
        return api.calcular_porcao(self.produto, self.gramas)

    def _somar(self, delta):
        novo = max((self.gramas or 0) + delta, self.PASSO)
        self.campo_gramas.value = num(novo, 1, enxuto=True).replace('.', '')
        self._atualizar()

    def _atualizar(self):
        porcao = self.porcao()
        self.campo_gramas.error = None if porcao or self.produto is None else 'Peso inválido'
        for chave, controle in self.valores.items():
            if porcao is None:
                controle.value = '–'
            else:
                controle.value = num(porcao[chave], 0 if chave == 'calorias' else 1, enxuto=True)
        if self.ao_mudar:
            self.ao_mudar()
