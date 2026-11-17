# NutriData Mobile: app Android feito com Flet (https://flet.dev).
# No computador:  flet run   (dentro da pasta mobile/)
import os
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ_REPOSITORIO = AQUI.parent.parent

# A lógica (db.py, metas.py, taco.py...) é a mesma do app web e fica na raiz do repositório.
# No APK não existe "a raiz do repositório": antes de gerar o APK, preparar_build.py copia
# esses arquivos para src/nucleo/. Se essa cópia existir, ela é usada; senão, a raiz.
_nucleo = AQUI / 'nucleo'
sys.path.insert(0, str(_nucleo if _nucleo.is_dir() else RAIZ_REPOSITORIO))

import flet as ft  # noqa: E402

import db  # noqa: E402
import tema  # noqa: E402
from telas.hoje import TelaHoje  # noqa: E402


def caminho_banco():
    """Onde fica o banco do app.

    - NUTRIDATA_BANCO (variável de ambiente): um banco escolhido à mão, para testes.
    - FLET_APP_STORAGE_DATA: a pasta de dados do app, criada pelo Flet. No celular é uma
      pasta privada do app, que não some ao atualizar o APK.
    """
    if os.environ.get('NUTRIDATA_BANCO'):
        caminho = Path(os.environ['NUTRIDATA_BANCO'])
    else:
        pasta = Path(os.environ.get('FLET_APP_STORAGE_DATA') or AQUI.parent / 'dados_locais')
        caminho = pasta / 'nutridata.db'
    caminho = caminho.resolve()
    # Proteção: o app do celular nunca deve abrir o banco do app web (nutridata.db da raiz)
    if caminho == (RAIZ_REPOSITORIO / 'nutridata.db').resolve():
        raise RuntimeError('O app mobile não pode usar o nutridata.db do app web.')
    caminho.parent.mkdir(parents=True, exist_ok=True)
    return caminho


# Telas da barra de baixo, na ordem. O botão do meio (índice 2) é o "+ Adicionar".
ABAS = [
    ('Hoje', ft.Icons.HOME_OUTLINED, ft.Icons.HOME),
    ('Histórico', ft.Icons.BAR_CHART_OUTLINED, ft.Icons.BAR_CHART),
    (None, None, None),
    ('Treino', ft.Icons.FITNESS_CENTER_OUTLINED, ft.Icons.FITNESS_CENTER),
    ('Perfil', ft.Icons.PERSON_OUTLINE, ft.Icons.PERSON),
]
INDICE_ADICIONAR = 2


def em_breve(nome, etapa):
    """Tela provisória para o que ainda vai ser feito."""
    return ft.Container(
        expand=True,
        alignment=ft.Alignment.CENTER,
        padding=24,
        content=ft.Column(
            [tema.titulo(nome, 26), tema.texto(f'Chega na etapa {etapa}.', cor=tema.TEXTO_SUAVE)],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
        ),
    )


def main(page: ft.Page):
    page.title = 'NutriData'
    tema.aplicar(page)
    page.padding = 0

    db.CAMINHO_BANCO = caminho_banco()
    db.criar_tabelas()
    print(f'Banco em uso: {db.CAMINHO_BANCO}')

    area = ft.Container(expand=True)
    hoje = TelaHoje(page, ao_adicionar=lambda refeicao: abrir_adicionar(refeicao))

    def mostrar(indice):
        if indice == 0:
            area.content = hoje.construir()
        elif indice == 1:
            area.content = em_breve('Histórico', 3)
        elif indice == 3:
            area.content = em_breve('Treino', 3)
        elif indice == 4:
            area.content = em_breve('Perfil', 3)

    def abrir_adicionar(refeicao=None):
        # A tela Adicionar chega na etapa 2; por enquanto, só um aviso
        page.show_dialog(ft.SnackBar(ft.Text('A tela Adicionar alimento chega na etapa 2.')))

    def trocar_aba(e):
        indice = int(e.control.selected_index)
        if indice == INDICE_ADICIONAR:
            # O "+" não é uma aba: abre a tela de adicionar e volta a marcar a aba anterior
            e.control.selected_index = barra.data
            abrir_adicionar()
            return
        barra.data = indice
        mostrar(indice)

    botao_mais = ft.Container(
        content=ft.Icon(ft.Icons.ADD, color=ft.Colors.WHITE, size=28),
        width=56, height=56, border_radius=999, bgcolor=tema.VERDE_ESCURO,
        alignment=ft.Alignment.CENTER,
    )
    destinos = []
    for nome, icone, icone_marcado in ABAS:
        if nome is None:
            destinos.append(ft.NavigationBarDestination(icon=botao_mais, label='Adicionar'))
        else:
            destinos.append(ft.NavigationBarDestination(icon=icone, selected_icon=icone_marcado, label=nome))

    barra = ft.NavigationBar(
        destinations=destinos,
        selected_index=0,
        data=0,  # guarda a aba atual (para o "+" voltar a ela)
        bgcolor=tema.CARTAO,
        indicator_color=tema.VERDE_CLARO,
        label_behavior=ft.NavigationBarLabelBehavior.ONLY_SHOW_SELECTED,
        on_change=trocar_aba,
    )
    page.navigation_bar = barra

    mostrar(0)
    page.add(ft.SafeArea(content=area, expand=True))


if __name__ == '__main__':
    ft.run(main, assets_dir='assets')
