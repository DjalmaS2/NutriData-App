# Tela "Treino": atividade + tempo -> calorias gastas (estimativa que dá para trocar)
from datetime import timedelta

import flet as ft

import db
import exercicios
import horario
import tema
from formatos import num
from logica import ler_gramas, resumo_semana
from telas.componentes import avisar, campo, confirmar, lista_suspensa, pagina, secao
from telas.graficos import barras, estatistica

PESO_PADRAO = 70.0  # usado na estimativa enquanto o perfil não tem peso
ATIVIDADES = list(exercicios.ATIVIDADES_MET)
LETRAS_DIAS = ['S', 'T', 'Q', 'Q', 'S', 'S', 'D']  # segunda a domingo


def texto_inteiro(valor):
    return num(valor, 0).replace('.', '')


class TelaTreino:
    def __init__(self, page: ft.Page):
        self.page = page
        self.raiz = ft.Container(expand=True)

    def construir(self):
        perfil = db.carregar_perfil()
        self.peso = perfil['peso_kg'] if perfil else PESO_PADRAO
        self.tem_perfil = perfil is not None
        hoje = horario.hoje()
        atividades = db.carregar_atividades()

        self.atividade = lista_suspensa('Atividade', ATIVIDADES, ATIVIDADES[0], ao_mudar=self._recalcular)
        self.minutos = campo('Tempo', value='60', suffix='min', keyboard_type=ft.KeyboardType.NUMBER,
                             expand=True, on_change=self._recalcular)
        self.kcal = campo('Calorias gastas', suffix='kcal', keyboard_type=ft.KeyboardType.NUMBER, expand=True)
        self.estimativa = tema.texto('', 12, cor=tema.TEXTO_SUAVE)
        self._recalcular()

        registrar = tema.cartao(ft.Column([
            tema.texto('Registrar treino de hoje', 15, 'negrito'),
            self.atividade,
            ft.Row([self.minutos, self.kcal], spacing=8),
            self.estimativa,
            ft.Row([ft.Button('Registrar', icon=ft.Icons.CHECK, on_click=self._registrar, height=52, expand=True,
                              bgcolor=tema.VERDE_ESCURO, color=ft.Colors.WHITE)]),
        ], spacing=12))

        controles = [registrar, *self._hoje(atividades, hoje), *self._semana(atividades, hoje)]
        self.raiz.content = pagina('Treino', 'Atividade e tempo: o app estima as calorias gastas.', controles)
        return self.raiz

    # --- Registrar ---
    def _recalcular(self, e=None):
        """Atualiza a estimativa (e o campo de calorias) quando muda a atividade ou o tempo."""
        minutos = ler_gramas(self.minutos.value or '')
        atividade = self.atividade.controls[0].value
        if not minutos:
            self.estimativa.value = 'Digite o tempo em minutos.'
            return
        estimativa = exercicios.calcular_kcal(atividade, minutos, self.peso)
        self.kcal.value = texto_inteiro(estimativa)
        self.estimativa.value = (f'Estimativa para {num(self.peso, enxuto=True)} kg'
                                 + ('' if self.tem_perfil else ' (peso padrão; preencha o Perfil)')
                                 + '. Se o relógio mostrou outro valor, é só trocar.')

    def _registrar(self, e=None):
        minutos = ler_gramas(self.minutos.value or '')
        kcal = ler_gramas(self.kcal.value or '')
        self.minutos.error = None if minutos else 'Tempo inválido'
        self.kcal.error = None if kcal else 'Calorias inválidas'
        if not minutos or not kcal:
            return
        atividade = self.atividade.controls[0].value
        db.registrar_atividade(horario.hoje(), atividade, minutos, round(kcal))
        avisar(self.page, f'{atividade}: {num(kcal, 0)} kcal registradas.')
        self.construir()

    # --- Treinos de hoje ---
    def _hoje(self, atividades, hoje):
        do_dia = atividades[atividades['data'] == hoje]
        if do_dia.empty:
            return [secao('Hoje'), tema.texto('Nenhum treino registrado hoje.', 14, cor=tema.TEXTO_SUAVE)]
        linhas = []
        for item in do_dia.itertuples():
            linhas.append(ft.Container(
                ft.Row([ft.Column([tema.texto(item.atividade, 14, 'medio'),
                                   tema.texto(f'{num(item.minutos, 0)} min', 12, cor=tema.TEXTO_SUAVE)],
                                  spacing=0, expand=True),
                        tema.texto(f'{num(item.kcal, 0)} kcal', 14, 'negrito'),
                        ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=tema.TEXTO_SUAVE, icon_size=20,
                                      tooltip='Apagar treino', on_click=lambda e, i=item: self._apagar(i))],
                       spacing=8),
                ink=True, border_radius=8, padding=ft.Padding.only(top=4, bottom=4),
                on_click=lambda e, i=item: self._editar(i),
            ))
        total = f"{num(do_dia['minutos'].sum(), 0)} min · {num(do_dia['kcal'].sum(), 0)} kcal"
        return [secao('Hoje', total), tema.cartao(ft.Column(linhas, spacing=2))]

    def _apagar(self, item):
        def apagar():
            db.deletar_atividade(int(item.id))
            self.construir()
            self.page.update()
        confirmar(self.page, 'Apagar treino?', f'{item.atividade} · {num(item.minutos, 0)} min · '
                  f'{num(item.kcal, 0)} kcal', 'Apagar', apagar)

    def _editar(self, item):
        minutos = campo('Tempo', value=texto_inteiro(item.minutos), suffix='min',
                        keyboard_type=ft.KeyboardType.NUMBER)
        kcal = campo('Calorias gastas', value=texto_inteiro(item.kcal), suffix='kcal',
                     keyboard_type=ft.KeyboardType.NUMBER)

        def salvar(e):
            novo_min, nova_kcal = ler_gramas(minutos.value or ''), ler_gramas(kcal.value or '')
            minutos.error = None if novo_min else 'Tempo inválido'
            kcal.error = None if nova_kcal else 'Calorias inválidas'
            if not novo_min or not nova_kcal:
                return
            # O banco não tem "atualizar treino": apaga e registra de novo no mesmo dia
            db.deletar_atividade(int(item.id))
            db.registrar_atividade(item.data, item.atividade, novo_min, round(nova_kcal))
            self.page.pop_dialog()
            self.construir()

        self.page.show_dialog(ft.AlertDialog(
            title=tema.titulo(item.atividade, 20, semi=True),
            content=ft.Column([minutos, kcal], tight=True, spacing=12, width=320),
            actions=[ft.TextButton('Cancelar', on_click=lambda e: self.page.pop_dialog()),
                     ft.Button('Salvar', on_click=salvar, bgcolor=tema.VERDE_ESCURO, color=ft.Colors.WHITE)],
            bgcolor=tema.FUNDO,
        ))

    # --- Semana ---
    def _semana(self, atividades, hoje):
        resumo = resumo_semana(atividades, hoje)
        dias = [hoje - timedelta(days=n) for n in range(6, -1, -1)]
        por_dia = atividades.groupby('data')['kcal'].sum().to_dict() if not atividades.empty else {}
        grafico = barras([(LETRAS_DIAS[d.weekday()], float(por_dia.get(d, 0)), tema.VERDE) for d in dias])
        return [
            secao('Últimos 7 dias'),
            ft.Row([estatistica('Dias com treino', str(resumo['dias'])),
                    estatistica('Tempo', f"{num(resumo['minutos'] / 60)} h"),
                    estatistica('Gasto', f"{num(resumo['kcal'], 0)} kcal")], spacing=8),
            tema.cartao(grafico),
        ]
