# Tela "Perfil": dados da pessoa e as metas calculadas a partir deles
import flet as ft

import db
import metas
import tema
from formatos import num
from logica import validar_perfil
from telas.componentes import avisar, campo, lista_suspensa, pagina, pilulas, secao
from telas.graficos import estatistica

SEXOS = ['Feminino', 'Masculino']
OBJETIVOS = list(metas.AJUSTE_OBJETIVO)
ATIVIDADES = list(metas.FATORES_ATIVIDADE)


def texto_numero(valor):
    """80.0 -> '80', 80.5 -> '80,5' (para preencher os campos)."""
    return '' if valor is None else num(valor, 1, enxuto=True).replace('.', '')


class TelaPerfil:
    def __init__(self, page: ft.Page, ao_jejum, ao_backup):
        self.page = page
        self.ao_jejum = ao_jejum    # abre a tela de Jejum
        self.ao_backup = ao_backup  # abre a tela de Backup
        self.raiz = ft.Container(expand=True)

    def construir(self):
        perfil = db.carregar_perfil()
        atual = perfil or {}
        self.sexo = atual.get('sexo', SEXOS[0])
        self.objetivo = atual.get('objetivo', 'Manter peso')

        self.campos = {
            'idade': campo('Idade', value=str(atual.get('idade', '')), keyboard_type=ft.KeyboardType.NUMBER,
                           expand=True),
            'peso_kg': campo('Peso', value=texto_numero(atual.get('peso_kg')), suffix='kg',
                             keyboard_type=ft.KeyboardType.NUMBER, expand=True),
            'altura_cm': campo('Altura', value=texto_numero(atual.get('altura_cm')), suffix='cm',
                               keyboard_type=ft.KeyboardType.NUMBER, expand=True),
            'peso_meta': campo('Meta de peso (opcional)', value=texto_numero(atual.get('peso_meta')), suffix='kg',
                               keyboard_type=ft.KeyboardType.NUMBER, hint_text='ex: 75',
                               helper='O Histórico mostra quando você chega lá.'),
        }
        self.atividade = lista_suspensa('Nível de atividade', ATIVIDADES, atual.get('atividade', ATIVIDADES[0]))
        self.somar = ft.Switch(value=bool(atual.get('somar_exercicio', 0)), active_color=tema.VERDE_ESCURO)
        self.area_sexo = ft.Container(pilulas(SEXOS, self.sexo, self._trocar_sexo))
        self.area_objetivo = ft.Container(pilulas(OBJETIVOS, self.objetivo, self._trocar_objetivo))

        formulario = tema.cartao(ft.Column([
            tema.texto('Sexo', 13, cor=tema.TEXTO_SUAVE), self.area_sexo,
            ft.Row([self.campos['idade'], self.campos['peso_kg'], self.campos['altura_cm']], spacing=8),
            self.atividade,
            tema.texto('Objetivo', 13, cor=tema.TEXTO_SUAVE), self.area_objetivo,
            self.campos['peso_meta'],
            ft.Row([ft.Column([tema.texto('Somar os exercícios à meta do dia', 14, 'medio'),
                               tema.texto('O nível de atividade já conta os exercícios de costume. Se ligar, '
                                          'escolha "Sedentário" para não contar duas vezes.', 12,
                                          cor=tema.TEXTO_SUAVE)], spacing=2, expand=True),
                    self.somar], spacing=12),
            ft.Row([ft.Button('Salvar perfil', on_click=self._salvar, height=52, expand=True,
                              bgcolor=tema.VERDE_ESCURO, color=ft.Colors.WHITE)]),
        ], spacing=14, horizontal_alignment=ft.CrossAxisAlignment.STRETCH))

        controles = [self._metas(perfil), secao('Mais'), self._mais(), secao('Seus dados'), formulario]
        self.raiz.content = pagina('Perfil', 'Com o perfil preenchido, o app calcula as suas metas.', controles)
        return self.raiz

    def _metas(self, perfil):
        if perfil is None:
            return tema.cartao(ft.Row([
                ft.Icon(ft.Icons.INFO_OUTLINE, color=tema.VERDE_ESCURO),
                tema.texto('Preencha e salve o perfil para calcular as suas metas. '
                           'Até lá, a meta é de 2.000 kcal por dia.', 14, expand=True),
            ], spacing=12))
        calculo = metas.calcular_meta(perfil)
        macros = metas.calcular_macros(calculo['meta'], perfil['peso_kg'])
        linha_peso = []
        if perfil.get('peso_meta'):
            falta = perfil['peso_meta'] - perfil['peso_kg']
            linha_peso = [estatistica('Meta de peso', f"{num(perfil['peso_meta'], enxuto=True)} kg",
                                      f'faltam {num(abs(falta))} kg' if abs(falta) >= 0.1 else 'alcançada!')]
        explicacao = ft.ExpansionTile(
            title=tema.texto('Como as metas são calculadas', 14, 'medio'),
            controls=[tema.texto(
                f"1. Metabolismo basal (fórmula de Mifflin-St Jeor): {num(calculo['tmb'], 0)} kcal, "
                'o que o corpo gasta em repouso.\n'
                f"2. Gasto diário: metabolismo basal × nível de atividade = {num(calculo['gasto'], 0)} kcal.\n"
                f"3. Meta: gasto diário ajustado ao objetivo ({perfil['objetivo'].lower()}), nunca abaixo de "
                f'{num(metas.META_MINIMA, 0)} kcal.\n'
                '4. Macros: proteína de 1,6 g por kg, gordura com 25% das calorias e carboidrato com o resto.\n'
                '5. Água: 35 ml por kg de peso.', 13, cor=tema.TEXTO_SUAVE)],
            controls_padding=ft.Padding.only(bottom=8), tile_padding=0, shape=ft.RoundedRectangleBorder(),
            collapsed_shape=ft.RoundedRectangleBorder(),
        )
        return tema.cartao(ft.Column([
            tema.texto('Suas metas por dia', 13, cor=tema.TEXTO_SUAVE),
            ft.Row([tema.titulo(num(calculo['meta'], 0), 34), tema.texto('kcal', 16, cor=tema.TEXTO_SUAVE)],
                   spacing=6, vertical_alignment=ft.CrossAxisAlignment.END),
            ft.Row([estatistica('Carboidratos', f"{num(macros['carboidratos'], 0)} g"),
                    estatistica('Proteínas', f"{num(macros['proteinas'], 0)} g"),
                    estatistica('Gorduras', f"{num(macros['gorduras'], 0)} g")], spacing=8),
            ft.Row([estatistica('Água', f"{num(metas.meta_agua_ml(perfil['peso_kg']) / 1000)} L"), *linha_peso],
                   spacing=8),
            explicacao,
        ], spacing=10), raio=24, padding=20)

    def _mais(self):
        def item(icone, titulo, detalhe, ao_tocar):
            return ft.ListTile(
                leading=ft.Container(ft.Icon(icone, color=tema.VERDE_ESCURO, size=22), width=40, height=40,
                                     border_radius=12, bgcolor=tema.VERDE_CLARO, alignment=ft.Alignment.CENTER),
                title=tema.texto(titulo, 15, 'negrito'), subtitle=tema.texto(detalhe, 12, cor=tema.TEXTO_SUAVE),
                trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT, color=tema.TEXTO_SUAVE),
                on_click=lambda e: ao_tocar(), content_padding=ft.Padding.symmetric(horizontal=4),
            )
        return tema.cartao(ft.Column([
            item(ft.Icons.TIMER_OUTLINED, 'Jejum intermitente', 'Começar e acompanhar o tempo de jejum', self.ao_jejum),
            ft.Divider(height=1, color=tema.BORDA),
            item(ft.Icons.BACKUP_OUTLINED, 'Backup', 'Salvar e restaurar os seus dados', self.ao_backup),
        ], spacing=0), padding=ft.Padding.symmetric(vertical=6, horizontal=12))

    def _trocar_sexo(self, sexo):
        self.sexo = sexo
        self.area_sexo.content = pilulas(SEXOS, sexo, self._trocar_sexo)

    def _trocar_objetivo(self, objetivo):
        self.objetivo = objetivo
        self.area_objetivo.content = pilulas(OBJETIVOS, objetivo, self._trocar_objetivo)

    def _salvar(self, e=None):
        valores, erros = validar_perfil({nome: c.value for nome, c in self.campos.items()})
        for nome, controle in self.campos.items():
            controle.error = erros.get(nome)
        if erros:
            avisar(self.page, 'Confira os campos marcados em vermelho.')
            return
        atividade = self.atividade.controls[0].value
        db.salvar_perfil(self.sexo, valores['idade'], valores['peso_kg'], valores['altura_cm'], atividade,
                         self.objetivo, self.somar.value, valores['peso_meta'])
        avisar(self.page, 'Perfil salvo. As metas foram atualizadas.')
        self.construir()
