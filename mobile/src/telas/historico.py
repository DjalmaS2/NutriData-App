# Tela "Histórico": calorias por dia, peso corporal e previsão da meta de peso
import flet as ft

import db
import horario
import metas
import tema
from formatos import num
from logica import calorias_por_dia, ler_gramas, meta_do_dia, resumo_periodo, texto_previsao
from telas.componentes import avisar, campo, confirmar, pagina, secao, segmentos
from telas.graficos import GraficoLinha, barras, estatistica

PERIODOS = {'7 dias': 7, '30 dias': 30, '90 dias': 90}
LETRAS_DIAS = ['S', 'T', 'Q', 'Q', 'S', 'S', 'D']


def rotulo_dia(dia, total):
    """Embaixo de cada barra: a letra do dia da semana (só no período de 7 dias)."""
    return LETRAS_DIAS[dia.weekday()] if total <= 7 else ''


class TelaHistorico:
    def __init__(self, page: ft.Page):
        self.page = page
        self.periodo = '7 dias'
        self.raiz = ft.Container(expand=True)

    def construir(self):
        perfil = db.carregar_perfil()
        hoje = horario.hoje()
        controles = [*self._calorias(perfil, hoje), *self._peso(perfil, hoje)]
        self.raiz.content = pagina('Histórico', 'Como você tem se saído: calorias e peso.', controles)
        return self.raiz

    def _trocar_periodo(self, periodo):
        self.periodo = periodo
        self.construir()

    # --- Calorias ---
    def _calorias(self, perfil, hoje):
        meta = meta_do_dia(perfil)
        dias = PERIODOS[self.periodo]
        historico = db.carregar_historico()
        por_dia = calorias_por_dia(historico, hoje, dias)
        resumo = resumo_periodo(por_dia, meta)
        controles = [secao('Calorias', f'meta {num(meta, 0)} kcal'),
                     segmentos(list(PERIODOS), self.periodo, self._trocar_periodo)]
        if resumo['dias_registrados'] == 0:
            return controles + [tema.texto(f'Nenhuma refeição registrada nos últimos {dias} dias.', 14,
                                           cor=tema.TEXTO_SUAVE)]
        itens = [(rotulo_dia(dia, dias), kcal, tema.EXCEDIDO if kcal > meta else tema.VERDE)
                 for dia, kcal in por_dia]
        # Em 30 e 90 dias as barras são finas: só a primeira, a do meio e a última data
        datas_eixo = None if dias <= 7 else [f'{por_dia[i][0]:%d/%m}' for i in (0, dias // 2, dias - 1)]
        legenda = ft.Row([self._legenda(tema.VERDE, 'Dentro da meta'), self._legenda(tema.EXCEDIDO, 'Acima')],
                         spacing=16)

        # Média de macros nos dias com registro
        dias_com_registro = [dia for dia, kcal in por_dia if kcal > 0]
        do_periodo = historico[historico['data_apenas'].isin(dias_com_registro)]
        medias = {m: do_periodo[m].sum() / len(dias_com_registro) for m in ['carboidratos', 'proteinas', 'gorduras']}

        return controles + [
            ft.Row([estatistica('Média diária', f"{num(resumo['media'], 0)} kcal"),
                    estatistica('Dias registrados', f"{resumo['dias_registrados']} de {dias}"),
                    estatistica('Dentro da meta', f"{resumo['dentro_da_meta']} dias")], spacing=8),
            tema.cartao(ft.Column([barras(itens, meta=meta, datas=datas_eixo), legenda], spacing=8)),
            tema.cartao(ft.Column([
                tema.texto('Média por dia registrado', 13, cor=tema.TEXTO_SUAVE),
                ft.Row([self._macro('Carboidratos', medias['carboidratos'], tema.CARBOIDRATOS),
                        self._macro('Proteínas', medias['proteinas'], tema.PROTEINAS),
                        self._macro('Gorduras', medias['gorduras'], tema.GORDURAS)], spacing=8),
            ], spacing=8)),
        ]

    @staticmethod
    def _legenda(cor, texto):
        return ft.Row([ft.Container(width=10, height=10, bgcolor=cor, border_radius=3),
                       tema.texto(texto, 12, cor=tema.TEXTO_SUAVE)], spacing=6, tight=True)

    @staticmethod
    def _macro(nome, gramas, cor):
        return ft.Column([ft.Row([ft.Container(width=8, height=8, bgcolor=cor, border_radius=999),
                                  tema.texto(nome, 12, cor=tema.TEXTO_SUAVE)], spacing=6),
                          tema.texto(f'{num(gramas, 0)} g', 16, 'negrito')], spacing=2, expand=True)

    # --- Peso ---
    def _peso(self, perfil, hoje):
        pesos = db.carregar_pesos()
        ultimo = float(pesos['peso_kg'].iloc[-1]) if not pesos.empty else (perfil['peso_kg'] if perfil else None)
        self.campo_peso = campo('Peso de hoje', suffix='kg', keyboard_type=ft.KeyboardType.NUMBER, expand=True,
                                value='' if ultimo is None else num(ultimo, 1, enxuto=True).replace('.', ''),
                                on_submit=self._registrar_peso)
        registrar = tema.cartao(ft.Column([
            ft.Row([self.campo_peso,
                    ft.Button('Registrar', on_click=self._registrar_peso, height=52, bgcolor=tema.VERDE_ESCURO,
                              color=ft.Colors.WHITE)], spacing=8),
            tema.texto('Uma pesagem por dia (a nova substitui a do mesmo dia). A mais recente atualiza o '
                       'Perfil, e a meta de calorias se ajusta sozinha.', 12, cor=tema.TEXTO_SUAVE),
        ], spacing=8))
        controles = [secao('Peso'), registrar]

        peso_meta = perfil.get('peso_meta') if perfil else None
        if peso_meta:
            controles.append(self._meta_peso(perfil, pesos, peso_meta, hoje))
        if pesos.empty:
            controles.append(tema.texto('Nenhuma pesagem registrada ainda.', 14, cor=tema.TEXTO_SUAVE))
            return controles

        if len(pesos) >= 2:
            variacao = pesos['peso_kg'].iloc[-1] - pesos['peso_kg'].iloc[0]
            grafico = GraficoLinha([float(p) for p in pesos['peso_kg']], meta=peso_meta)
            controles.append(tema.cartao(ft.Column([
                ft.Row([tema.texto('Desde a primeira pesagem', 13, cor=tema.TEXTO_SUAVE),
                        tema.texto(f'{num(variacao, sinal=True)} kg', 14, 'negrito')],
                       alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                grafico.raiz,
                ft.Row([tema.texto(f"{pesos['data'].iloc[0]:%d/%m}", 11, cor=tema.TEXTO_SUAVE),
                        tema.texto(f"{pesos['data'].iloc[-1]:%d/%m}", 11, cor=tema.TEXTO_SUAVE)],
                       alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ], spacing=8)))

        # As pesagens mais recentes primeiro, com a lixeira para apagar
        linhas = []
        for item in list(pesos.itertuples())[::-1][:10]:
            linhas.append(ft.Row([
                tema.texto(f'{item.data:%d/%m/%Y}', 14, expand=True),
                tema.texto(f'{num(item.peso_kg)} kg', 14, 'negrito'),
                ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=tema.TEXTO_SUAVE, icon_size=20,
                              tooltip='Apagar pesagem', on_click=lambda e, i=item: self._apagar_peso(i)),
            ], spacing=8))
        controles.append(tema.cartao(ft.Column([tema.texto('Últimas pesagens', 13, cor=tema.TEXTO_SUAVE), *linhas],
                                               spacing=0)))
        return controles

    def _meta_peso(self, perfil, pesos, peso_meta, hoje):
        peso_atual = float(pesos['peso_kg'].iloc[-1]) if not pesos.empty else float(perfil['peso_kg'])
        peso_inicial = float(pesos['peso_kg'].iloc[0]) if not pesos.empty else peso_atual
        falta = peso_meta - peso_atual
        titulo = ft.Row([ft.Icon(ft.Icons.FLAG_OUTLINED, color=tema.VERDE_ESCURO, size=20),
                         tema.texto(f'Meta: {num(peso_meta, enxuto=True)} kg', 15, 'negrito')], spacing=8)
        if abs(falta) < 0.1:
            return tema.cartao(ft.Column([titulo, tema.texto('Meta de peso alcançada! Que tal definir uma nova '
                                                             'no Perfil?', 14)], spacing=8))

        caminho = peso_meta - peso_inicial
        progresso = (peso_atual - peso_inicial) / caminho if caminho else 0
        partes = [titulo, tema.barra(progresso, tema.VERDE, altura=8),
                  tema.texto(f'Faltam {num(abs(falta))} kg ({max(progresso, 0):.0%} do caminho desde '
                             f'{num(peso_inicial, enxuto=True)} kg)', 13, cor=tema.TEXTO_SUAVE)]

        ajuste = metas.AJUSTE_OBJETIVO[perfil['objetivo']]
        semanas_plano = metas.semanas_pelo_plano(peso_atual, peso_meta, ajuste)
        if semanas_plano is None:
            partes.append(self._linha(ft.Icons.ASSIGNMENT_OUTLINED, 'Pelo plano',
                                      f"O objetivo do perfil ({perfil['objetivo'].lower()}) não leva até a meta. "
                                      'Ajuste o objetivo no Perfil.'))
        else:
            partes.append(self._linha(ft.Icons.ASSIGNMENT_OUTLINED, f'Pelo plano ({ajuste:+d} kcal por dia)',
                                      texto_previsao(semanas_plano, hoje)))

        ritmo = metas.ritmo_real_kg_semana(pesos)
        if ritmo is None:
            partes.append(self._linha(ft.Icons.TRENDING_DOWN, 'Pelo seu ritmo real',
                                      'Registre pesagens por pelo menos uma semana para ver esta previsão.'))
        else:
            semanas_ritmo = metas.semanas_pelo_ritmo(peso_atual, peso_meta, ritmo)
            partes.append(self._linha(
                ft.Icons.TRENDING_DOWN, f'Pelo seu ritmo real ({num(ritmo, sinal=True)} kg por semana)',
                'Você está se afastando da meta.' if semanas_ritmo is None else texto_previsao(semanas_ritmo, hoje)))
            # Mais de 1% do peso por semana é rápido demais para a maioria das pessoas
            if abs(ritmo) > peso_atual * 0.01:
                partes.append(tema.texto('O seu peso está mudando mais de 1% por semana. Vale conversar com um '
                                         'nutricionista para fazer isso com segurança.', 13, cor=tema.EXCEDIDO))
        partes.append(tema.texto(f'Estimativas: 1 kg de peso corporal equivale a cerca de '
                                 f'{num(metas.KCAL_POR_KG, 0)} kcal.', 11, cor=tema.TEXTO_SUAVE))
        return tema.cartao(ft.Column(partes, spacing=10))

    @staticmethod
    def _linha(icone, titulo, texto):
        return ft.Row([ft.Icon(icone, size=18, color=tema.TEXTO_SUAVE),
                       ft.Column([tema.texto(titulo, 13, 'medio'), tema.texto(texto, 13, cor=tema.TEXTO_SUAVE)],
                                 spacing=0, expand=True)], spacing=10, vertical_alignment=ft.CrossAxisAlignment.START)

    def _registrar_peso(self, e=None):
        peso = ler_gramas(self.campo_peso.value or '')
        if peso is None or not 30 <= peso <= 300:
            self.campo_peso.error = 'Entre 30 e 300 kg'
            return
        db.registrar_peso(horario.hoje(), peso)
        avisar(self.page, f'Pesagem de {num(peso)} kg registrada.')
        self.construir()

    def _apagar_peso(self, item):
        def apagar():
            db.deletar_peso(int(item.id))
            self.construir()
        confirmar(self.page, 'Apagar pesagem?', f'{item.data:%d/%m/%Y}: {num(item.peso_kg)} kg', 'Apagar', apagar)
