# Gráficos simples desenhados com peças do próprio Flet (sem pacote extra no APK)
import flet as ft
import flet.canvas as cv

import tema
from formatos import num


def estatistica(rotulo, valor, detalhe=None):
    """Quadradinho com um número em destaque (ex.: Média diária: 1.850 kcal)."""
    partes = [tema.texto(rotulo, 12, cor=tema.TEXTO_SUAVE, max_lines=2), tema.texto(valor, 18, 'negrito')]
    if detalhe:
        partes.append(tema.texto(detalhe, 11, cor=tema.TEXTO_SUAVE))
    return ft.Container(ft.Column(partes, spacing=2), expand=True, border_radius=16,
                        padding=ft.Padding.symmetric(vertical=12, horizontal=10),
                        bgcolor=tema.CARTAO, border=ft.Border.all(1, tema.BORDA))


def barras(itens, meta=None, altura=150, rotulo_meta='Meta', datas=None, unidade='kcal'):
    """Gráfico de barras: itens = [(rótulo embaixo de cada barra, valor, cor)].

    meta desenha uma linha horizontal na altura do valor. Com muitas barras (finas demais
    para um rótulo cada), passe rótulos vazios e `datas`: textos espalhados embaixo do gráfico.
    """
    maior = max([valor for _, valor, _ in itens] + [meta or 0]) or 1
    topo = maior * 1.12  # folga em cima para a barra mais alta não encostar
    colunas = []
    for rotulo, valor, cor in itens:
        barra = ft.Container(height=max(altura * valor / topo, 2 if valor else 0), bgcolor=cor,
                             border_radius=ft.BorderRadius.only(top_left=4, top_right=4),
                             tooltip=f'{num(valor, 0)} {unidade}' if valor else None)
        colunas.append(ft.Column(
            [ft.Container(barra, height=altura, alignment=ft.Alignment.BOTTOM_CENTER),
             tema.texto(rotulo, 10, cor=tema.TEXTO_SUAVE, text_align=ft.TextAlign.CENTER, no_wrap=True)],
            spacing=4, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        ))
    camadas = [ft.Row(colunas, spacing=3 if len(itens) > 14 else 8, vertical_alignment=ft.CrossAxisAlignment.END)]
    if meta:
        y = altura * (1 - meta / topo)
        camadas.append(ft.Container(
            content=ft.Row([ft.Container(height=1.5, expand=True, bgcolor=tema.TEXTO_SUAVE, opacity=0.6),
                            tema.texto(f'{rotulo_meta} {num(meta, 0)}', 10, cor=tema.TEXTO_SUAVE)], spacing=4),
            top=y - 7, left=0, right=0,
        ))
    grafico = ft.Stack(camadas, height=altura + 20)
    if not datas:
        return grafico
    return ft.Column([grafico, ft.Row([tema.texto(d, 10, cor=tema.TEXTO_SUAVE) for d in datas],
                                      alignment=ft.MainAxisAlignment.SPACE_BETWEEN)], spacing=0)


class GraficoLinha:
    """Linha dos pesos ao longo do tempo, com a meta tracejada. Redesenha ao mudar de tamanho."""

    ALTURA = 150
    MARGEM = 12

    def __init__(self, pontos, meta=None, cor=tema.VERDE):
        self.pontos = pontos  # lista de valores na ordem do tempo
        self.meta = meta
        self.cor = cor
        self.canvas = cv.Canvas(height=self.ALTURA, expand=True, on_resize=self._redimensionar)
        self.raiz = ft.Container(self.canvas, height=self.ALTURA)

    def _redimensionar(self, e):
        self._desenhar(e.width)
        self.canvas.update()

    def _desenhar(self, largura):
        valores = self.pontos + ([self.meta] if self.meta else [])
        menor, maior = min(valores), max(valores)
        if maior - menor < 1:  # evita uma linha "achatada" quando o peso quase não muda
            menor, maior = menor - 0.5, maior + 0.5
        util_x, util_y = largura - 2 * self.MARGEM, self.ALTURA - 2 * self.MARGEM

        def xy(indice, valor):
            x = self.MARGEM + (util_x * indice / (len(self.pontos) - 1) if len(self.pontos) > 1 else util_x / 2)
            y = self.MARGEM + util_y * (maior - valor) / (maior - menor)
            return x, y

        formas = []
        if self.meta:
            _, y = xy(0, self.meta)
            formas.append(cv.Line(self.MARGEM, y, largura - self.MARGEM, y,
                                  paint=ft.Paint(color=tema.TEXTO_SUAVE, stroke_width=1.5,
                                                 stroke_dash_pattern=[6, 5])))
            formas.append(cv.Text(self.MARGEM, y - 16, f'Meta {num(self.meta, enxuto=True)} kg',
                                  style=ft.TextStyle(size=10, color=tema.TEXTO_SUAVE, font_family='DM Sans')))
        caminho = [cv.Path.MoveTo(*xy(0, self.pontos[0]))] + \
            [cv.Path.LineTo(*xy(i, v)) for i, v in enumerate(self.pontos) if i > 0]
        formas.append(cv.Path(caminho, paint=ft.Paint(color=self.cor, stroke_width=3,
                                                      style=ft.PaintingStyle.STROKE,
                                                      stroke_join=ft.StrokeJoin.ROUND)))
        for i, v in enumerate(self.pontos):
            x, y = xy(i, v)
            formas.append(cv.Circle(x, y, 4, paint=ft.Paint(color=self.cor)))
        self.canvas.shapes = formas
