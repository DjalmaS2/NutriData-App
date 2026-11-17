# Tela "Adicionar alimento": Tabela TACO, código de barras (Open Food Facts) e Meus pratos
import asyncio

import flet as ft

import api
import db
import horario
import tema
from formatos import REFEICOES, num
from logica import ler_gramas, prato_como_produto, refeicao_pelo_horario, somar_ingredientes
from telas.componentes import BuscaTaco, PainelPorcao, campo, item_alimento, pilulas, segmentos

BUSCAR, CODIGO, PRATOS = 'Buscar', 'Código de barras', 'Meus pratos'


def cabecalho(titulo, ao_voltar):
    return ft.Row([ft.IconButton(ft.Icons.ARROW_BACK_IOS_NEW, icon_color=tema.TEXTO, tooltip='Voltar',
                                 on_click=lambda e: ao_voltar()),
                   tema.titulo(titulo, 24)], spacing=4)


def rodape(botao):
    return ft.Container(botao, padding=ft.Padding.only(left=20, right=20, top=12, bottom=16),
                        bgcolor=tema.CARTAO, border=ft.Border.only(top=ft.BorderSide(1, tema.BORDA)))


def botao_principal(rotulo, ao_clicar, cor=tema.VERDE_ESCURO):
    return ft.Button(
        content=rotulo, on_click=ao_clicar, height=56, expand=True, bgcolor=cor, color=ft.Colors.WHITE,
        style=ft.ButtonStyle(text_style=ft.TextStyle(size=16, font_family='DM Sans Bold')),
    )


class TelaAdicionar:
    def __init__(self, page: ft.Page, ao_voltar, ao_novo_prato):
        self.page = page
        self.ao_voltar = ao_voltar          # volta para a tela Hoje
        self.ao_novo_prato = ao_novo_prato  # abre a tela de montar prato
        self.refeicao = REFEICOES[0]
        self.modo = BUSCAR
        self.produto = None

        self.porcao = PainelPorcao(ao_mudar=self._atualizar_botao)
        self.busca = BuscaTaco(ao_escolher=lambda p: self._escolher(p, 100))
        self.botao = botao_principal('', self._salvar)
        self.area_refeicoes = ft.Container()
        self.area_abas = ft.Container()
        self.area_modo = ft.Container()

        # Código de barras
        self.campo_codigo = campo(
            'Código de barras', hint_text='ex: 7891000100103', keyboard_type=ft.KeyboardType.NUMBER,
            prefix_icon=ft.Icons.QR_CODE_SCANNER, expand=True, on_submit=self._buscar_codigo,
        )
        self.status_codigo = ft.Column(spacing=10)

        self.corpo = ft.ListView(
            [self.area_refeicoes, self.area_abas, self.area_modo, self.porcao.raiz],
            spacing=16, padding=ft.Padding.only(left=20, right=20, top=8, bottom=20), expand=True,
        )
        self.raiz = ft.Column([
            ft.Container(cabecalho('Adicionar alimento', self.ao_voltar),
                         padding=ft.Padding.only(left=8, top=12, right=12)),
            self.corpo,
            rodape(ft.Row([self.botao])),
        ], spacing=0, expand=True)

    def abrir(self, refeicao=None, modo=None):
        """Prepara a tela do zero (chamada sempre que ela é aberta)."""
        self.refeicao = refeicao or refeicao_pelo_horario(horario.agora().hour)
        self.modo = modo or BUSCAR
        self.produto = None
        self.porcao.esconder()
        self.busca.limpar()
        self.campo_codigo.value = ''
        self.status_codigo.controls = []
        self._desenhar()
        return self.raiz

    # --- Desenho ---
    def _desenhar(self):
        self.area_refeicoes.content = pilulas(REFEICOES, self.refeicao, self._trocar_refeicao)
        self.area_abas.content = segmentos([BUSCAR, CODIGO, PRATOS], self.modo, self._trocar_modo)
        if self.modo == BUSCAR:
            self.area_modo.content = self.busca.raiz
        elif self.modo == CODIGO:
            self.area_modo.content = ft.Column([
                ft.Row([self.campo_codigo,
                        ft.IconButton(ft.Icons.SEARCH, on_click=self._buscar_codigo, tooltip='Buscar produto',
                                      bgcolor=tema.VERDE_ESCURO, icon_color=ft.Colors.WHITE, width=52, height=52)],
                       spacing=8),
                tema.texto('Digite os números embaixo do código de barras. A leitura pela câmera vem depois.',
                           12, cor=tema.TEXTO_SUAVE),
                self.status_codigo,
            ], spacing=10)
        else:
            self.area_modo.content = self._lista_pratos()
        self._atualizar_botao()

    def _atualizar_botao(self):
        pronto = self.produto is not None and self.porcao.porcao() is not None
        self.botao.content = f'Adicionar ao {self.refeicao.lower()}'
        self.botao.disabled = not pronto
        self.botao.bgcolor = tema.VERDE_ESCURO if pronto else tema.BORDA

    def _trocar_refeicao(self, refeicao):
        self.refeicao = refeicao
        self._desenhar()

    def _trocar_modo(self, modo):
        self.modo = modo
        self.produto = None
        self.porcao.esconder()
        self._desenhar()

    def _escolher(self, produto, gramas):
        self.produto = produto
        self.porcao.mostrar(produto, gramas)
        self._atualizar_botao()
        self.page.run_task(self._rolar_ate_porcao)

    async def _rolar_ate_porcao(self):
        # Leva a tela até "Quanto você comeu?", que pode ter ficado lá embaixo
        await asyncio.sleep(0.1)
        await self.corpo.scroll_to(scroll_key='porcao', duration=300)

    # --- Código de barras ---
    async def _buscar_codigo(self, e=None):
        codigo = (self.campo_codigo.value or '').strip()
        if not codigo.isdigit():
            self.status_codigo.controls = [tema.texto('Digite só os números do código.', 13, cor=tema.EXCEDIDO)]
            return
        self.produto = None
        self.porcao.esconder()
        self.status_codigo.controls = [ft.Row([ft.ProgressRing(width=18, height=18, stroke_width=2),
                                               tema.texto('Buscando no Open Food Facts...', 13,
                                                          cor=tema.TEXTO_SUAVE)], spacing=10)]
        self._atualizar_botao()
        self.page.update()
        try:
            # A busca usa a internet; roda fora da tela para o app não travar enquanto espera
            produto = await asyncio.to_thread(api.buscar_produto, codigo)
        except api.ErroAPI as erro:
            self.status_codigo.controls = [tema.texto(f'{erro} Confira a internet e tente de novo.', 13,
                                                      cor=tema.EXCEDIDO)]
            return
        if produto is None:
            self.status_codigo.controls = [tema.texto(
                'Produto não encontrado no Open Food Facts. Tente buscar pelo nome na aba Buscar.',
                13, cor=tema.EXCEDIDO)]
            return
        self.status_codigo.controls = [
            tema.texto('Valores por 100 g', 13, cor=tema.TEXTO_SUAVE),
            item_alimento(produto['nome'], f"C {num(produto['carboidratos_100g'])} g · "
                                           f"P {num(produto['proteinas_100g'])} g · "
                                           f"G {num(produto['gorduras_100g'])} g",
                          f"{num(produto['calorias_100g'], 0)} kcal", ao_tocar=None, marcado=True),
        ]
        self._escolher(produto, 100)

    # --- Meus pratos ---
    def _lista_pratos(self):
        pratos = db.carregar_meus_alimentos()
        novo = ft.OutlinedButton('Montar um prato novo', icon=ft.Icons.ADD, on_click=lambda e: self.ao_novo_prato(),
                                 height=44, style=ft.ButtonStyle(color=tema.VERDE_ESCURO,
                                                                 side=ft.BorderSide(1, tema.VERDE_ESCURO)))
        if pratos.empty:
            return ft.Column([tema.texto('Você ainda não tem pratos salvos. Junte os ingredientes de uma '
                                         'receita uma vez e depois registre com um toque.', 14,
                                         cor=tema.TEXTO_SUAVE), novo], spacing=12)
        itens = []
        for prato in pratos.to_dict('records'):
            marcado = self.produto is not None and self.produto.get('id_prato') == prato['id']
            itens.append(item_alimento(
                prato['nome_alimento'],
                f"Prato inteiro: {num(prato['porcao_g'], 0)} g",
                f"{num(prato['calorias'], 0)} kcal",
                ao_tocar=lambda e, p=prato: self._escolher_prato(p),
                marcado=marcado,
                final=ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=tema.TEXTO_SUAVE, icon_size=20,
                                    tooltip='Apagar prato', on_click=lambda e, p=prato: self._apagar_prato(p)),
            ))
        return ft.Column([*itens, novo], spacing=10)

    def _escolher_prato(self, prato):
        produto = prato_como_produto(prato, db.NUTRIENTES)
        produto['id_prato'] = prato['id']  # só para marcar o prato escolhido na lista
        self._escolher(produto, prato['porcao_g'])
        self.area_modo.content = self._lista_pratos()

    def _apagar_prato(self, prato):
        def apagar(e):
            db.deletar_prato(int(prato['id']))
            self.page.pop_dialog()
            if self.produto is not None and self.produto.get('id_prato') == prato['id']:
                self.produto = None
                self.porcao.esconder()
            self._desenhar()

        self.page.show_dialog(ft.AlertDialog(
            title=tema.titulo('Apagar prato?', 20, semi=True),
            content=tema.texto(f"{prato['nome_alimento']} sai da lista de pratos. "
                               'O que já foi registrado no diário continua lá.'),
            actions=[ft.TextButton('Cancelar', on_click=lambda e: self.page.pop_dialog()),
                     ft.Button('Apagar', on_click=apagar, bgcolor=tema.EXCEDIDO, color=ft.Colors.WHITE)],
            bgcolor=tema.FUNDO,
        ))

    # --- Salvar ---
    def _salvar(self, e=None):
        porcao = self.porcao.porcao()
        if self.produto is None or porcao is None:
            return
        gramas = self.porcao.gramas
        db.salvar_consumo(self.refeicao, self.produto['nome'], gramas, porcao)
        self.page.show_dialog(ft.SnackBar(ft.Text(
            f"{self.produto['nome']} ({num(gramas, 0)} g) adicionado ao {self.refeicao.lower()}.")))
        self.ao_voltar()


class TelaNovoPrato:
    """Monta um prato com ingredientes da TACO e salva em Meus pratos."""

    def __init__(self, page: ft.Page, ao_voltar):
        self.page = page
        self.ao_voltar = ao_voltar  # volta para Adicionar, na aba Meus pratos
        self.ingredientes = []
        self.peso_mudado = False

        self.campo_nome = campo('Nome do prato', hint_text='ex: Marmita de frango',
                                capitalization=ft.TextCapitalization.SENTENCES)
        self.porcao = PainelPorcao(titulo='Quanto vai na receita?', ao_mudar=self._atualizar)
        self.busca = BuscaTaco(ao_escolher=lambda p: self.porcao.mostrar(p, 100), rotulo='Ingrediente (Tabela TACO)')
        self.botao_ingrediente = ft.Button('Adicionar ingrediente', icon=ft.Icons.ADD, on_click=self._adicionar,
                                           bgcolor=tema.VERDE_CLARO, color=tema.VERDE_ESCURO, height=44)
        self.lista = ft.Column(spacing=8)
        self.campo_peso = campo(
            'Peso do prato pronto (g)', keyboard_type=ft.KeyboardType.NUMBER, suffix='g',
            helper='Cozinhar muda o peso. Se não pesou, deixe a soma.', on_change=self._peso_digitado,
        )
        self.botao_salvar = botao_principal('Salvar prato', self._salvar)
        self.corpo = ft.ListView(
            [self.campo_nome, self.busca.raiz, self.porcao.raiz, ft.Row([self.botao_ingrediente]),
             self.lista, self.campo_peso],
            spacing=16, padding=ft.Padding.only(left=20, right=20, top=8, bottom=20), expand=True,
        )
        self.raiz = ft.Column([
            ft.Container(cabecalho('Novo prato', self.ao_voltar), padding=ft.Padding.only(left=8, top=12, right=12)),
            self.corpo,
            rodape(ft.Row([self.botao_salvar])),
        ], spacing=0, expand=True)

    def abrir(self):
        self.ingredientes = []
        self.peso_mudado = False
        self.campo_nome.value = ''
        self.campo_nome.error = None
        self.campo_peso.value = ''
        self.busca.limpar()
        self.porcao.esconder()
        self._atualizar()
        return self.raiz

    def _peso_digitado(self, e):
        self.peso_mudado = True

    def _adicionar(self, e=None):
        porcao = self.porcao.porcao()
        if porcao is None:
            return
        self.ingredientes.append({'nome': self.porcao.produto['nome'], 'gramas': self.porcao.gramas, **porcao})
        self.porcao.esconder()
        self.busca.limpar()
        self._atualizar()

    def _remover(self, indice):
        self.ingredientes.pop(indice)
        self._atualizar()

    def _atualizar(self):
        self.botao_ingrediente.visible = self.porcao.produto is not None
        self.botao_ingrediente.disabled = self.porcao.porcao() is None
        soma_gramas = sum(i['gramas'] for i in self.ingredientes)
        soma_kcal = sum(i['calorias'] for i in self.ingredientes)
        if not self.peso_mudado:
            self.campo_peso.value = num(soma_gramas, 0).replace('.', '') if self.ingredientes else ''
        if not self.ingredientes:
            self.lista.controls = [tema.texto('Busque os ingredientes acima e adicione um por um.', 13,
                                              cor=tema.TEXTO_SUAVE)]
        else:
            linhas = [ft.Row([tema.texto(f"{i['nome']} · {num(i['gramas'], 0)} g", 14, expand=True),
                              tema.texto(f"{num(i['calorias'], 0)} kcal", 14),
                              ft.IconButton(ft.Icons.CLOSE, icon_size=18, icon_color=tema.TEXTO_SUAVE,
                                            tooltip='Tirar ingrediente', on_click=lambda e, n=n: self._remover(n))],
                             spacing=6)
                      for n, i in enumerate(self.ingredientes)]
            total = tema.texto(f'Total: {num(soma_gramas, 0)} g · {num(soma_kcal, 0)} kcal', 14, 'negrito')
            self.lista.controls = [tema.cartao(ft.Column([*linhas, ft.Divider(color=tema.BORDA), total], spacing=2))]
        self.botao_salvar.disabled = not self.ingredientes
        self.botao_salvar.bgcolor = tema.VERDE_ESCURO if self.ingredientes else tema.BORDA

    def _salvar(self, e=None):
        nome = (self.campo_nome.value or '').strip()
        peso = ler_gramas(self.campo_peso.value or '')
        self.campo_nome.error = None if nome else 'Dê um nome ao prato'
        self.campo_peso.error = None if peso else 'Digite o peso do prato pronto'
        if not nome or not peso or not self.ingredientes:
            return
        db.salvar_prato(nome, peso, somar_ingredientes(self.ingredientes, db.NUTRIENTES))
        self.page.show_dialog(ft.SnackBar(ft.Text(f'Prato "{nome}" salvo em Meus pratos.')))
        self.ao_voltar()
