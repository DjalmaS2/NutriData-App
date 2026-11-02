from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

import db
import exercicios
from comum import COR_PRINCIPAL

PESO_PADRAO = 70.0


def avisar(mensagem, icone):
    # A mensagem fica guardada e aparece depois que a página recarrega
    st.session_state.aviso_exercicio = (mensagem, icone)


def mostrar_aviso():
    if 'aviso_exercicio' in st.session_state:
        mensagem, icone = st.session_state.pop('aviso_exercicio')
        st.toast(mensagem, icon=icone)


def registrar(dia, perfil):
    peso = perfil['peso_kg'] if perfil else PESO_PADRAO
    with st.container(border=True):
        st.markdown("**Registrar treino**")
        col_atividade, col_minutos = st.columns([3, 1])
        atividade = col_atividade.selectbox("Atividade:", list(exercicios.ATIVIDADES_MET))
        minutos = col_minutos.number_input("Tempo (min):", min_value=5, max_value=600, value=60, step=5)
        estimativa = exercicios.calcular_kcal(atividade, minutos, peso)

        # A estimativa já vem preenchida, mas dá para trocar (ex.: pelo número do relógio).
        # A key muda com a atividade e o tempo, para a estimativa nova aparecer ao trocar um deles.
        col_kcal, col_botao = st.columns([3, 1], vertical_alignment="bottom")
        kcal = col_kcal.number_input("Calorias gastas (kcal):", min_value=0, max_value=5000,
                                     value=int(round(estimativa)), step=10, key=f"kcal_{atividade}_{minutos}")
        if col_botao.button("💾 Registrar", type="primary", width="stretch"):
            db.registrar_atividade(dia, atividade, minutos, kcal)
            avisar(f"{atividade}: {kcal} kcal registradas", "🔥")
            st.rerun()
        st.caption(f"Estimativa de {estimativa:.0f} kcal para {peso:g} kg"
                   + ("" if perfil else " (peso padrão; preencha o Perfil para ficar mais preciso)")
                   + ". Se o seu relógio ou aparelho mostrou outro valor, é só trocar.")


def mostrar_dia(dia, atividades):
    do_dia = atividades[atividades['data'] == dia]
    st.subheader(f"Treinos de {dia:%d/%m}")
    if do_dia.empty:
        st.info("Nenhum treino registrado neste dia.")
        return
    st.markdown(f"**Total:** {do_dia['minutos'].sum():.0f} min · {do_dia['kcal'].sum():.0f} kcal")
    for item in do_dia.itertuples():
        col_texto, col_apagar = st.columns([6, 1], vertical_alignment="center")
        col_texto.markdown(f"{item.atividade} · {item.minutos:.0f} min · **{item.kcal:.0f} kcal**")
        if col_apagar.button("🗑️", key=f"apagar_atividade_{item.id}", help="Apagar treino"):
            db.deletar_atividade(item.id)
            st.rerun()


def mostrar_semana(atividades):
    hoje = datetime.now().date()
    periodo = pd.date_range(end=hoje, periods=7).date
    semana = atividades[atividades['data'].isin(periodo)]

    st.subheader("Últimos 7 dias")
    c1, c2, c3 = st.columns(3)
    c1.metric("📆 Dias com treino", semana['data'].nunique())
    c2.metric("⏱️ Tempo total", f"{semana['minutos'].sum() / 60:.1f} h")
    c3.metric("🔥 Calorias gastas", f"{semana['kcal'].sum():.0f} kcal")
    if semana.empty:
        return
    por_dia = semana.groupby('data')['kcal'].sum().reindex(periodo, fill_value=0).reset_index()
    por_dia.columns = ['Dia', 'kcal']
    fig = px.bar(por_dia, x='Dia', y='kcal', color_discrete_sequence=[COR_PRINCIPAL])
    st.plotly_chart(fig, width="stretch")


st.title("Exercícios")
st.caption("Registre o tempo de cada treino e veja quantas calorias você gastou.")
mostrar_aviso()
perfil = db.carregar_perfil()
atividades = db.carregar_atividades()

dia = st.date_input("Dia do treino:", datetime.now().date(), format="DD/MM/YYYY")
registrar(dia, perfil)
mostrar_dia(dia, atividades)
st.divider()
mostrar_semana(atividades)
