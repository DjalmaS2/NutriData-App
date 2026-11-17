# Tela "Hoje": saldo de calorias, macros, água e o diário de refeições do dia
import flet as ft

import db
import exercicios
import horario
import metas
import tema
from formatos import REFEICOES, num

DIAS_SEMANA = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
MESES = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto',
         'setembro', 'outubro', 'novembro', 'dezembro']
MACROS = [('Carboidratos', 'carboidratos', tema.CARBOIDRATOS),
          ('Proteínas', 'proteinas', tema.PROTEINAS),
          ('Gorduras', 'gorduras', tema.GORDURAS)]


def data_por_extenso(dia):
    """date(2026, 11, 2) -> 'Segunda, 2 de novembro'"""
    return f'{DIAS_SEMANA[dia.weekday()]}, {dia.day} de {MESES[dia.month - 1]}'


def ler_gramas(texto):
    """'150' ou '150,5' -> número; None se não for um peso válido."""
    try:
        valor = float(texto.strip().replace(',', '.'))
    except ValueError:
        return None
    return valor if valor > 0 else None


class TelaHoje:
    def __init__(self, page: ft.Page, ao_adicionar):
        self.page = page
        self.ao_adicionar = ao_adicionar  # função chamada com o nome da refeição
        self.coluna = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=16, expand=True)
        self.raiz = ft.Container(content=self.coluna, padding=ft.Padding.symmetric(vertical=20, horizontal=20),
                                 expand=True)

    def construir(self):
        """Lê o banco e monta a tela inteira de novo (simples e sempre atualizado)."""
        dia = horario.hoje()
        historico = db.carregar_historico()
        df_dia = historico[historico['data_apenas'] == dia]
        perfil = db.carregar_perfil()

        self.coluna.controls = [
            self._cabecalho(dia, historico),
            self._resumo(df_dia, perfil, dia),
            self._agua(dia, perfil),
            ft.Row(
                [tema.titulo('Diário', 22, semi=True),
                 tema.texto(f'{len(REFEICOES)} refeições', 13, cor=tema.TEXTO_SUAVE)],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.END,
            ),
            *[self._refeicao(nome, df_dia[df_dia['refeicao'] == nome]) for nome in REFEICOES],
        ]
        # Registros antigos com refeição fora da lista (ex.: '1') não podem sumir da tela
        outros = df_dia[~df_dia['refeicao'].isin(REFEICOES)]
        if not outros.empty:
            self.coluna.controls.append(self._refeicao('Outros', outros, pode_adicionar=False))
        return self.raiz

    def recarregar(self):
        self.construir()
        self.page.update()

    # --- Partes da tela ---
    def _cabecalho(self, dia, historico):
        dias_com_registro = set(historico['data_apenas'])
        sequencia = exercicios.sequencia_dias(dias_com_registro, dia)
        partes = [ft.Column([tema.texto(data_por_extenso(dia), 13, cor=tema.TEXTO_SUAVE),
                             tema.titulo('Hoje', 30)], spacing=0)]
        if sequencia > 0:
            partes.append(ft.Container(
                content=ft.Row([ft.Icon(ft.Icons.LOCAL_FIRE_DEPARTMENT_OUTLINED, size=16,
                                        color=tema.SEQUENCIA_TEXTO),
                                tema.texto(f"{sequencia} {'dia seguido' if sequencia == 1 else 'dias seguidos'}",
                                           13, 'negrito', tema.SEQUENCIA_TEXTO)],
                               spacing=6, tight=True),
                bgcolor=tema.SEQUENCIA_FUNDO, border_radius=999,
                padding=ft.Padding.symmetric(vertical=8, horizontal=12),
            ))
        return ft.Row(partes, alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    def _resumo(self, df_dia, perfil, dia):
        meta = round(metas.calcular_meta(perfil)['meta']) if perfil else 2000
        gasto_exercicio = db.kcal_exercicio(dia)
        # Igual ao app web: somar os exercícios à meta é uma opção do perfil
        somar = bool(perfil and perfil.get('somar_exercicio'))
        exercicio = gasto_exercicio if somar else 0
        meta_total = meta + exercicio
        consumido = df_dia['calorias'].sum()
        restante = meta_total - consumido
        excedeu = restante < 0

        anel = ft.Stack(
            [
                ft.ProgressRing(value=min(consumido / meta_total, 1.0) if meta_total else 0,
                                width=150, height=150, stroke_width=14, stroke_cap=ft.StrokeCap.ROUND,
                                color=tema.EXCEDIDO if excedeu else tema.VERDE, bgcolor=tema.TRILHO),
                ft.Container(
                    width=150, height=150, alignment=ft.Alignment.CENTER,
                    content=ft.Column(
                        [tema.titulo(('+' if excedeu else '') + num(abs(restante), 0), 32,
                                     color=tema.EXCEDIDO if excedeu else tema.TEXTO),
                         tema.texto('kcal acima' if excedeu else 'kcal restantes', 12, cor=tema.TEXTO_SUAVE)],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2, tight=True,
                    ),
                ),
            ],
            width=150, height=150,
        )

        def numero(rotulo, valor, cor=tema.TEXTO):
            return ft.Column([tema.texto(rotulo, 12, cor=tema.TEXTO_SUAVE),
                              tema.texto(valor, 18, 'negrito', cor)], spacing=0)

        conta = [numero('Meta', f'{num(meta, 0)} kcal'), numero('Consumido', f'{num(consumido, 0)} kcal')]
        if gasto_exercicio > 0:
            conta.append(numero('Exercício' if somar else 'Exercício (fora da meta)',
                                f'+ {num(gasto_exercicio, 0)} kcal', tema.VERDE_ESCURO))

        meta_macros = metas.calcular_macros(meta_total, perfil['peso_kg'] if perfil else None)
        macros = []
        for nome, chave, cor in MACROS:
            valor, alvo = df_dia[chave].sum(), meta_macros[chave]
            macros.append(ft.Column(
                [tema.texto(nome, 12, cor=tema.TEXTO_SUAVE),
                 tema.barra(valor / alvo if alvo else 0, tema.EXCEDIDO if valor > alvo else cor),
                 ft.Row([tema.texto(num(valor, 0), 13, 'negrito'),
                         tema.texto(f'/ {num(alvo, 0)} g', 13, cor=tema.TEXTO_SUAVE)], spacing=4)],
                spacing=6, expand=True,
            ))

        return tema.cartao(ft.Column([
            ft.Row([anel, ft.Column(conta, spacing=10, expand=True)], spacing=18),
            ft.Row(macros, spacing=12),
        ], spacing=18), raio=24, padding=20)

    def _agua(self, dia, perfil):
        meta_ml = metas.meta_agua_ml(perfil['peso_kg'] if perfil else None)
        total = db.total_agua(dia)

        def beber(ml):
            def _clique(e):
                db.registrar_agua(horario.hoje(), ml)
                self.recarregar()
            return _clique

        def desfazer(e):
            db.desfazer_agua(horario.hoje())
            self.recarregar()

        def botao(rotulo, ml):
            return ft.OutlinedButton(
                content=rotulo, on_click=beber(ml), height=44,
                style=ft.ButtonStyle(color=tema.AGUA_TEXTO, side=ft.BorderSide(1, '#C9D9E1'),
                                     padding=ft.Padding.symmetric(horizontal=12)),
            )

        icone = ft.Container(ft.Icon(ft.Icons.WATER_DROP_OUTLINED, color=tema.AGUA_TEXTO, size=22),
                             width=40, height=40, border_radius=12, bgcolor=tema.AGUA_FUNDO,
                             alignment=ft.Alignment.CENTER)
        info = ft.Column(
            [ft.Row([tema.texto('Água', 14, 'negrito'),
                     tema.texto(f'{num(total / 1000, 2)} de {num(meta_ml / 1000, 1)} L', 14, cor=tema.TEXTO_SUAVE)],
                    spacing=6),
             tema.barra(total / meta_ml, tema.GORDURAS)],
            spacing=6, expand=True,
        )
        botoes = ft.Row(
            [botao('+250', 250), botao('+500', 500),
             ft.IconButton(ft.Icons.UNDO, icon_color=tema.TEXTO_SUAVE, tooltip='Desfazer o último copo',
                           on_click=desfazer, disabled=total == 0)],
            spacing=8, alignment=ft.MainAxisAlignment.END,
        )
        return tema.cartao(ft.Column([ft.Row([icone, info], spacing=14), botoes], spacing=10),
                           padding=ft.Padding.symmetric(vertical=14, horizontal=16))

    def _refeicao(self, nome, itens, pode_adicionar=True):
        botao_mais = ft.IconButton(
            ft.Icons.ADD, icon_color=tema.VERDE_ESCURO, bgcolor=tema.VERDE_CLARO,
            tooltip=f'Adicionar em {nome}', on_click=lambda e: self.ao_adicionar(nome),
            visible=pode_adicionar,
        )
        if itens.empty:
            return tema.cartao(ft.Row(
                [ft.Column([tema.texto(nome, 15, 'negrito'),
                            tema.texto('Nada registrado ainda', 13, cor=tema.TEXTO_SUAVE)], spacing=2),
                 botao_mais],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ))

        cabecalho = ft.Row(
            [tema.texto(nome, 15, 'negrito'),
             ft.Row([tema.texto(f"{num(itens['calorias'].sum(), 0)} kcal", 14, cor=tema.TEXTO_SUAVE), botao_mais],
                    spacing=10, tight=True)],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
        linhas = [self._item(linha) for linha in itens.sort_values('data_registro').itertuples()]
        return tema.cartao(ft.Column([cabecalho, *linhas], spacing=4))

    def _item(self, linha):
        """Uma linha do diário; tocar nela abre editar/apagar."""
        return ft.Container(
            content=ft.Row(
                [ft.Row([tema.texto(linha.nome_alimento, 14, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS,
                                    expand=True),
                         tema.texto(f'· {num(linha.porcao_g, 0, enxuto=True)} g', 14, cor=tema.TEXTO_SUAVE)],
                        spacing=6, expand=True),
                 tema.texto(num(linha.calorias, 0), 14)],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=ft.Padding.symmetric(vertical=8),
            ink=True,
            border_radius=8,
            on_click=lambda e, l=linha: self._editar(l),
        )

    # --- Editar / apagar ---
    def _editar(self, linha):
        campo_peso = ft.TextField(
            label='Porção (g)', value=num(linha.porcao_g, 1, enxuto=True).replace('.', ''),
            keyboard_type=ft.KeyboardType.NUMBER, suffix='g', autofocus=True,
        )
        campo_refeicao = ft.Dropdown(
            label='Refeição', value=linha.refeicao if linha.refeicao in REFEICOES else REFEICOES[0],
            options=[ft.DropdownOption(key=r, text=r) for r in REFEICOES], width=320,
        )
        kcal_por_g = linha.calorias / linha.porcao_g if linha.porcao_g else 0
        previa = tema.texto(f'{num(linha.calorias, 0)} kcal', 13, cor=tema.TEXTO_SUAVE)

        def atualizar_previa(e):
            gramas = ler_gramas(campo_peso.value)
            previa.value = f'{num(kcal_por_g * gramas, 0)} kcal' if gramas else 'Digite um peso válido'

        campo_peso.on_change = atualizar_previa

        def salvar(e):
            gramas = ler_gramas(campo_peso.value)
            if not gramas:
                campo_peso.error = 'Digite um peso maior que zero'
                return
            if linha.porcao_g:
                db.atualizar_registro(int(linha.id), gramas, campo_refeicao.value)
            self.page.pop_dialog()
            self.recarregar()

        def confirmar_apagar(e):
            self.page.pop_dialog()
            self._confirmar_apagar(linha)

        self.page.show_dialog(ft.AlertDialog(
            title=tema.titulo(linha.nome_alimento, 20, semi=True),
            content=ft.Column([campo_peso, previa, campo_refeicao], tight=True, spacing=12, width=320),
            actions=[
                ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=tema.EXCEDIDO, tooltip='Apagar',
                              on_click=confirmar_apagar),
                ft.Row([ft.TextButton('Cancelar', on_click=lambda e: self.page.pop_dialog()),
                        ft.Button('Salvar', on_click=salvar, bgcolor=tema.VERDE_ESCURO, color=ft.Colors.WHITE)],
                       tight=True),
            ],
            actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            bgcolor=tema.FUNDO,
        ))

    def _confirmar_apagar(self, linha):
        def apagar(e):
            db.deletar_consumo(int(linha.id))
            self.page.pop_dialog()
            self.recarregar()

        self.page.show_dialog(ft.AlertDialog(
            title=tema.titulo('Apagar registro?', 20, semi=True),
            content=tema.texto(f'{linha.nome_alimento} · {num(linha.porcao_g, 0, enxuto=True)} g '
                               f'({num(linha.calorias, 0)} kcal) sai do diário de hoje.'),
            actions=[
                ft.TextButton('Cancelar', on_click=lambda e: self.page.pop_dialog()),
                ft.Button('Apagar', on_click=apagar, bgcolor=tema.EXCEDIDO, color=ft.Colors.WHITE),
            ],
            bgcolor=tema.FUNDO,
        ))
