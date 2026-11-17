# Tela "Jejum intermitente": começar, acompanhar o tempo até a meta e ver o histórico
import asyncio
from datetime import timedelta

import flet as ft

import db
import horario
import jejum
import tema
from formatos import num
from logica import inicio_pela_hora, resumo_jejuns
from telas.componentes import avisar, confirmar, pagina_secundaria, pilulas, secao
from telas.graficos import barras, estatistica

PROTOCOLO_PADRAO = '16:8'
CINZA_ABAIXO = '#B9B2A4'  # barras dos jejuns que não chegaram à meta


class TelaJejum:
    def __init__(self, page: ft.Page, ao_voltar):
        self.page = page
        self.ao_voltar = ao_voltar
        self.aberta = False
        self.raiz = ft.Container(expand=True)

    def abrir(self):
        self.protocolo = PROTOCOLO_PADRAO
        self.hora_inicio = None  # None = agora
        self.aberta = True
        self.construir()
        # Atualiza o relógio do jejum sozinho enquanto a tela estiver aberta
        self.page.run_task(self._relogio)
        return self.raiz

    def _voltar(self):
        self.aberta = False
        self.ao_voltar()

    async def _relogio(self):
        while True:
            await asyncio.sleep(30)
            if not self.aberta:
                return
            if db.jejum_ativo() is not None:
                self.construir()
                self.page.update()

    def construir(self):
        ativo = db.jejum_ativo()
        controles = [self._ativo(ativo) if ativo else self._comecar(),
                     tema.texto('Jejum não é indicado para gestantes, menores de 18 anos, pessoas com diabetes ou '
                                'com histórico de transtorno alimentar sem acompanhamento de um profissional de '
                                'saúde.', 12, cor=tema.TEXTO_SUAVE),
                     *self._historico()]
        self.raiz.content = pagina_secundaria('Jejum intermitente', self._voltar, controles)
        return self.raiz

    # --- Jejum em andamento ---
    def _ativo(self, ativo):
        agora = horario.agora()
        horas = jejum.horas_decorridas(ativo['inicio'], agora)
        meta = ativo['meta_horas']
        fim = jejum.previsao_fim(ativo['inicio'], meta)
        cumpriu = horas >= meta

        anel = ft.Stack([
            ft.ProgressRing(value=min(horas / meta, 1.0), width=190, height=190, stroke_width=16,
                            stroke_cap=ft.StrokeCap.ROUND, color=tema.VERDE, bgcolor=tema.TRILHO),
            ft.Container(width=190, height=190, alignment=ft.Alignment.CENTER, content=ft.Column([
                tema.texto('Tempo de jejum', 12, cor=tema.TEXTO_SUAVE),
                tema.titulo(jejum.formatar_duracao(horas), 40),
                tema.texto(f'{min(horas / meta, 1):.0%} da meta de {num(meta, 0)} h', 12, cor=tema.TEXTO_SUAVE),
            ], spacing=2, tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER)),
        ], width=190, height=190)

        if cumpriu:
            situacao = tema.texto('Meta alcançada! Você já pode encerrar o jejum.', 14, 'negrito', tema.VERDE_ESCURO,
                                  text_align=ft.TextAlign.CENTER)
        else:
            situacao = tema.texto(f'Faltam {jejum.formatar_duracao(meta - horas)}: termina '
                                  f'{fim:%d/%m} às {fim:%H:%M}.', 14, text_align=ft.TextAlign.CENTER)

        def encerrar():
            db.encerrar_jejum(ativo['id'], horario.agora())
            avisar(self.page, f'Jejum encerrado com {jejum.formatar_duracao(horas)}.')
            self.construir()

        botao = ft.Button('Encerrar jejum', icon=ft.Icons.STOP_CIRCLE_OUTLINED, height=52, expand=True,
                          bgcolor=tema.VERDE_ESCURO if cumpriu else tema.CARTAO,
                          color=ft.Colors.WHITE if cumpriu else tema.EXCEDIDO,
                          on_click=lambda e: encerrar() if cumpriu else confirmar(
                              self.page, 'Encerrar antes da meta?',
                              f'Você está com {jejum.formatar_duracao(horas)} de {num(meta, 0)} h.', 'Encerrar',
                              encerrar))
        return tema.cartao(ft.Column([
            tema.texto(f"Jejum {ativo['protocolo']} · começou {ativo['inicio']:%d/%m} às {ativo['inicio']:%H:%M}",
                       13, cor=tema.TEXTO_SUAVE),
            ft.Row([anel], alignment=ft.MainAxisAlignment.CENTER),
            situacao,
            ft.Row([botao]),
        ], spacing=14, horizontal_alignment=ft.CrossAxisAlignment.CENTER), raio=24, padding=20)

    # --- Começar ---
    def _comecar(self):
        agora = horario.agora()
        inicio = agora if self.hora_inicio is None else inicio_pela_hora(self.hora_inicio, agora)
        quando = 'agora' if self.hora_inicio is None else \
            f"{'ontem' if inicio.date() < agora.date() else 'hoje'} às {inicio:%H:%M}"
        horas = jejum.PROTOCOLOS[self.protocolo]
        fim = jejum.previsao_fim(inicio, horas)

        def escolher_hora(e):
            self.page.show_dialog(ft.TimePicker(
                value=(self.hora_inicio or agora.time()).replace(second=0, microsecond=0),
                hour_format=ft.TimePickerHourFormat.H24, help_text='Hora da última refeição',
                cancel_text='Cancelar', confirm_text='OK', on_change=hora_escolhida,
            ))

        def hora_escolhida(e):
            self.hora_inicio = e.control.value
            self.construir()

        def usar_agora(e):
            self.hora_inicio = None
            self.construir()

        def comecar(e):
            momento = horario.agora() if self.hora_inicio is None else inicio_pela_hora(self.hora_inicio,
                                                                                        horario.agora())
            db.iniciar_jejum(self.protocolo, horas, momento)
            avisar(self.page, f'Jejum {self.protocolo} começou. Bom jejum!')
            self.construir()

        def trocar_protocolo(protocolo):
            self.protocolo = protocolo
            self.construir()

        return tema.cartao(ft.Column([
            tema.texto('Começar um jejum', 15, 'negrito'),
            tema.texto('Protocolo (horas de jejum : horas para comer)', 13, cor=tema.TEXTO_SUAVE),
            pilulas(list(jejum.PROTOCOLOS), self.protocolo, trocar_protocolo),
            tema.texto('Última refeição', 13, cor=tema.TEXTO_SUAVE),
            ft.Row([
                ft.OutlinedButton(quando.capitalize(), icon=ft.Icons.SCHEDULE, on_click=escolher_hora, height=44,
                                  style=ft.ButtonStyle(color=tema.TEXTO, side=ft.BorderSide(1, tema.BORDA))),
                ft.TextButton('Usar agora', on_click=usar_agora, visible=self.hora_inicio is not None),
            ], spacing=8, wrap=True),
            tema.texto(f'Meta de {horas} h: termina {fim:%d/%m} às {fim:%H:%M}.', 13, cor=tema.TEXTO_SUAVE),
            ft.Row([ft.Button('Começar jejum', icon=ft.Icons.PLAY_ARROW, on_click=comecar, height=52, expand=True,
                              bgcolor=tema.VERDE_ESCURO, color=ft.Colors.WHITE)]),
        ], spacing=12))

    # --- Histórico ---
    def _historico(self):
        jejuns = db.carregar_jejuns()
        resumo = resumo_jejuns(jejuns)
        if resumo['total'] == 0:
            return [secao('Histórico'), tema.texto('Nenhum jejum concluído ainda.', 14, cor=tema.TEXTO_SUAVE)]
        controles = [secao('Histórico'), ft.Row([
            estatistica('Jejuns', str(resumo['total'])),
            estatistica('Meta cumprida', f"{resumo['cumpridos']} de {resumo['total']}"),
            estatistica('Duração média', jejum.formatar_duracao(resumo['media_horas'])),
        ], spacing=8)]

        recentes = jejuns[jejuns['inicio'] >= horario.agora() - timedelta(days=14)].sort_values('inicio')
        if not recentes.empty:
            itens = [(f'{j.inicio:%d/%m}', float(j.horas), tema.VERDE if j.horas >= j.meta_horas else CINZA_ABAIXO)
                     for j in recentes.itertuples()]
            if len(itens) > 7:  # muitos jejuns: tira as datas de baixo de cada barra
                datas = [itens[0][0], itens[-1][0]]
                itens = [('', v, c) for _, v, c in itens]
            else:
                datas = None
            controles.append(tema.cartao(ft.Column([
                tema.texto('Últimas 2 semanas (horas)', 13, cor=tema.TEXTO_SUAVE),
                barras(itens, datas=datas, unidade='h'),
            ], spacing=8)))

        linhas = []
        for item in jejuns.head(10).itertuples():
            cumpriu = item.horas >= item.meta_horas
            linhas.append(ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE if cumpriu else ft.Icons.PAUSE_CIRCLE_OUTLINE, size=20,
                        color=tema.VERDE if cumpriu else tema.TEXTO_SUAVE),
                ft.Column([tema.texto(f'{item.inicio:%d/%m às %H:%M}', 14, 'medio'),
                           tema.texto(f'{item.protocolo} · meta {num(item.meta_horas, 0)} h', 12,
                                      cor=tema.TEXTO_SUAVE)], spacing=0, expand=True),
                tema.texto(jejum.formatar_duracao(item.horas), 14, 'negrito'),
                ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=tema.TEXTO_SUAVE, icon_size=20, tooltip='Apagar jejum',
                              on_click=lambda e, i=item: self._apagar(i)),
            ], spacing=10))
        controles.append(tema.cartao(ft.Column(linhas, spacing=4)))
        return controles

    def _apagar(self, item):
        def apagar():
            db.deletar_jejum(int(item.id))
            self.construir()
        confirmar(self.page, 'Apagar jejum?', f'{item.inicio:%d/%m às %H:%M} · {jejum.formatar_duracao(item.horas)}',
                  'Apagar', apagar)
