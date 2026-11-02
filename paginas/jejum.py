from datetime import datetime, timedelta

import plotly.express as px
import streamlit as st

import db
import jejum
from comum import COR_PRINCIPAL, COR_RESTANTE


@st.fragment(run_every=60)
def mostrar_jejum_ativo():
    # fragment com run_every: só este pedaço da página se atualiza sozinho a cada minuto
    ativo = db.jejum_ativo()
    if ativo is None:
        st.rerun(scope="app")
    agora = datetime.now()
    horas = jejum.horas_decorridas(ativo['inicio'], agora)
    fim_previsto = jejum.previsao_fim(ativo['inicio'], ativo['meta_horas'])
    percentual = horas / ativo['meta_horas']

    with st.container(border=True):
        st.markdown(f"**Jejum {ativo['protocolo']} em andamento** · começou {ativo['inicio']:%d/%m às %H:%M}")
        st.metric("⏱️ Tempo de jejum", jejum.formatar_duracao(horas))
        st.progress(min(percentual, 1.0), text=f"{min(percentual, 1.0):.0%} da meta de {ativo['meta_horas']:g} horas")
        if horas >= ativo['meta_horas']:
            st.success(f"🎉 Meta alcançada! Você já pode encerrar o jejum.")
        else:
            st.caption(f"Faltam {jejum.formatar_duracao(ativo['meta_horas'] - horas)}: "
                       f"termina {fim_previsto:%d/%m às %H:%M}.")
        if st.button("⏹️ Encerrar jejum", type="primary", width="stretch"):
            db.encerrar_jejum(ativo['id'], agora)
            st.rerun(scope="app")


def mostrar_inicio():
    with st.container(border=True):
        st.markdown("**Começar um jejum**")
        protocolo = st.radio("Protocolo (horas de jejum : horas para comer):", list(jejum.PROTOCOLOS),
                             index=2, horizontal=True)
        agora = datetime.now()
        # Dá para começar no passado, se você esqueceu de iniciar na hora da última refeição
        col_dia, col_hora = st.columns(2)
        dia = col_dia.date_input("Última refeição em:", agora.date(), format="DD/MM/YYYY",
                                 max_value=agora.date())
        hora = col_hora.time_input("às:", agora.time().replace(second=0, microsecond=0), step=300)
        inicio = datetime.combine(dia, hora)
        if inicio > agora:
            st.warning("O início não pode ser no futuro.")
        elif st.button("▶️ Começar jejum", type="primary", width="stretch"):
            db.iniciar_jejum(protocolo, jejum.PROTOCOLOS[protocolo], inicio)
            st.rerun()


def mostrar_historico_jejuns():
    jejuns = db.carregar_jejuns()
    st.subheader("Histórico")
    if jejuns.empty:
        st.info("Nenhum jejum concluído ainda.")
        return

    completos = jejuns[jejuns['horas'] >= jejuns['meta_horas']]
    c1, c2, c3 = st.columns(3)
    c1.metric("Jejuns", len(jejuns))
    c2.metric("Meta cumprida", f"{len(completos)} de {len(jejuns)}")
    c3.metric("Duração média", jejum.formatar_duracao(jejuns['horas'].mean()))

    recentes = jejuns[jejuns['inicio'] >= datetime.now() - timedelta(days=14)].sort_values('inicio')
    if not recentes.empty:
        grafico = recentes.assign(
            Dia=recentes['inicio'].dt.date,
            Situação=recentes.apply(lambda j: 'Meta cumprida' if j['horas'] >= j['meta_horas'] else 'Abaixo da meta',
                                    axis=1))
        fig = px.bar(grafico, x='Dia', y='horas', color='Situação', labels={'horas': 'Horas de jejum'},
                     color_discrete_map={'Meta cumprida': COR_PRINCIPAL, 'Abaixo da meta': '#B9B2A4'})
        st.plotly_chart(fig, width="stretch")

    for item in jejuns.head(10).itertuples():
        col_texto, col_apagar = st.columns([6, 1], vertical_alignment="center")
        marca = "✅" if item.horas >= item.meta_horas else "⏸️"
        col_texto.markdown(f"{marca} {item.inicio:%d/%m %H:%M} · **{jejum.formatar_duracao(item.horas)}** "
                           f"de {item.meta_horas:g}h ({item.protocolo})")
        if col_apagar.button("🗑️", key=f"apagar_jejum_{item.id}", help="Apagar jejum"):
            db.deletar_jejum(item.id)
            st.rerun()


st.title("Jejum intermitente")
st.caption("Marque quando parou de comer e acompanhe o tempo até a meta do protocolo.")

if db.jejum_ativo():
    mostrar_jejum_ativo()
else:
    mostrar_inicio()

st.caption("⚠️ Jejum não é indicado para gestantes, menores de 18 anos, pessoas com diabetes ou com histórico "
           "de transtorno alimentar sem acompanhamento de um profissional de saúde.")
st.divider()
mostrar_historico_jejuns()
