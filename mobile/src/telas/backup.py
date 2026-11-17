# Tela "Backup": salvar uma cópia do banco (.db) e restaurar a partir dela
from pathlib import Path

import flet as ft

import db
import horario
import tema
from formatos import num
from telas.componentes import avisar, confirmar, pagina_secundaria, secao


class TelaBackup:
    def __init__(self, page: ft.Page, ao_voltar):
        self.page = page
        self.ao_voltar = ao_voltar
        self.raiz = ft.Container(expand=True)
        self.status = ft.Column(spacing=6)

    def abrir(self):
        self.status.controls = []
        return self.construir()

    def construir(self):
        contagem = db.contar_registros()
        linhas = [ft.Row([tema.texto(nome, 14, expand=True), tema.texto(num(total, 0), 14, 'negrito')])
                  for nome, total in contagem.items()]

        controles = [
            tema.cartao(ft.Row([
                ft.Icon(ft.Icons.PHONE_ANDROID, color=tema.VERDE_ESCURO),
                tema.texto('Os seus dados ficam só neste celular. Se ele for perdido, trocado ou o app for '
                           'desinstalado, eles somem. Salve um backup de vez em quando e guarde fora do '
                           'celular (Google Drive, e-mail, computador).', 14, expand=True),
            ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.START)),
            secao('O que tem no app'),
            tema.cartao(ft.Column(linhas, spacing=6)),
            secao('Salvar backup'),
            tema.cartao(ft.Column([
                tema.texto('Um arquivo .db com tudo: refeições, pratos, perfil, pesos, água, treinos e jejuns. '
                           'É ele que você usa para restaurar depois, inclusive no app web.', 13,
                           cor=tema.TEXTO_SUAVE),
                ft.Row([ft.Button('Salvar backup', icon=ft.Icons.SAVE_ALT, on_click=self._exportar, height=52,
                                  expand=True, bgcolor=tema.VERDE_ESCURO, color=ft.Colors.WHITE)]),
            ], spacing=12)),
            secao('Restaurar backup'),
            tema.cartao(ft.Column([
                tema.texto('Escolha um arquivo de backup do NutriData (.db). Os dados atuais serão substituídos '
                           'pelos do backup (o app guarda uma cópia dos atuais antes, por segurança).', 13,
                           cor=tema.TEXTO_SUAVE),
                ft.Row([ft.OutlinedButton('Escolher arquivo', icon=ft.Icons.UPLOAD_FILE, on_click=self._importar,
                                          height=52, expand=True,
                                          style=ft.ButtonStyle(color=tema.VERDE_ESCURO,
                                                               side=ft.BorderSide(1, tema.VERDE_ESCURO)))]),
            ], spacing=12)),
            self.status,
        ]
        self.raiz.content = pagina_secundaria('Backup', self.ao_voltar, controles)
        return self.raiz

    def _mensagem(self, texto, erro=False):
        self.status.controls = [tema.texto(texto, 14, 'medio', tema.EXCEDIDO if erro else tema.VERDE_ESCURO)]

    # --- Exportar ---
    async def _exportar(self, e=None):
        nome = f'nutridata-backup-{horario.agora():%Y-%m-%d}.db'
        try:
            # No celular abre a tela do Android para escolher onde salvar (Downloads, Drive...)
            caminho = await ft.FilePicker().save_file(dialog_title='Salvar backup do NutriData', file_name=nome,
                                                      src_bytes=db.exportar_banco())
        except Exception as erro:  # o sistema pode recusar (sem espaço, pasta protegida...)
            self._mensagem(f'Não foi possível salvar o backup: {erro}', erro=True)
            return
        if caminho:
            self._mensagem(f'Backup salvo: {Path(caminho).name}')
        else:
            self._mensagem('Nada foi salvo (você cancelou).')

    # --- Importar ---
    async def _importar(self, e=None):
        # Tipo "qualquer arquivo": o Android não reconhece a extensão .db no filtro.
        # O conteúdo é conferido por db.restaurar_banco, que recusa o que não for backup.
        arquivos = await ft.FilePicker().pick_files(dialog_title='Escolher backup do NutriData', with_data=True)
        if not arquivos:
            return
        arquivo = arquivos[0]
        conteudo = arquivo.bytes
        if conteudo is None and arquivo.path:  # no computador o arquivo pode vir só pelo caminho
            conteudo = Path(arquivo.path).read_bytes()
        if not conteudo:
            self._mensagem('Não foi possível ler o arquivo escolhido.', erro=True)
            self.page.update()
            return

        def restaurar():
            try:
                db.restaurar_banco(bytes(conteudo))
            except db.BackupInvalido as erro:
                self._mensagem(str(erro), erro=True)
                return
            avisar(self.page, 'Backup restaurado!')
            self.construir()
            self._mensagem(f'Backup "{arquivo.name}" restaurado com sucesso.')

        confirmar(self.page, 'Restaurar este backup?',
                  f'"{arquivo.name}" vai substituir todos os dados atuais do app.', 'Restaurar', restaurar)
        self.page.update()
