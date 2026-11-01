from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

import db
from comum import CORES_MACROS, campo_meta


def mostrar_calorias(df, meta_calorias):
    dias = st.radio("Período:", [7, 30, 90], horizontal=True, format_func=lambda d: f"Últimos {d} dias")

    # Um valor por dia; dias sem registro entram com 0 para o gráfico não "pular" datas
    colunas = ['calorias', 'carboidratos', 'proteinas', 'gorduras']
    periodo = pd.date_range(end=datetime.now().date(), periods=dias).date
    por_dia = df.groupby('data_apenas')[colunas].sum().reindex(periodo, fill_value=0)
    por_dia.index.name = 'Dia'

    registrados = por_dia[por_dia['calorias'] > 0]
    if registrados.empty:
        st.info(f"Nenhuma refeição registrada nos últimos {dias} dias.")
        return

    # A média considera só os dias com registro, para dias esquecidos não puxarem para baixo
    col1, col2, col3 = st.columns(3)
    col1.metric("📊 Média diária", f"{registrados['calorias'].mean():.0f} kcal")
    col2.metric("📝 Dias registrados", f"{len(registrados)} de {dias}")
    col3.metric("🎯 Dias dentro da meta", f"{(registrados['calorias'] <= meta_calorias).sum()}")

    st.subheader("Calorias por Dia")
    df_grafico = por_dia.reset_index()
    df_grafico['Situação'] = df_grafico['calorias'].map(
        lambda c: 'Acima da meta' if c > meta_calorias else 'Dentro da meta')
    fig = px.bar(df_grafico, x='Dia', y='calorias', color='Situação',
                 color_discrete_map={'Dentro da meta': '#66B2FF', 'Acima da meta': '#FF9999'},
                 labels={'calorias': 'kcal'})
    fig.add_hline(y=meta_calorias, line_dash='dash', annotation_text=f"Meta: {meta_calorias} kcal")
    st.plotly_chart(fig, width="stretch")

    st.subheader("Macronutrientes por Dia (g)")
    df_macros = df_grafico.melt(id_vars='Dia', value_vars=['carboidratos', 'proteinas', 'gorduras'],
                                var_name='Nutriente', value_name='Gramas')
    df_macros['Nutriente'] = df_macros['Nutriente'].str.capitalize()
    fig_macros = px.bar(df_macros, x='Dia', y='Gramas', color='Nutriente',
                        color_discrete_sequence=CORES_MACROS)
    st.plotly_chart(fig_macros, width="stretch")


def mostrar_peso(perfil):
    st.subheader("⚖️ Peso Corporal")
    pesos = db.carregar_pesos()

    if not pesos.empty:
        peso_inicial = float(pesos['peso_kg'].iloc[-1])
    else:
        peso_inicial = float(perfil['peso_kg']) if perfil else 70.0
    col_data, col_peso, col_botao = st.columns([2, 2, 1])
    dia = col_data.date_input("Dia da pesagem:", datetime.now().date(), key="dia_pesagem")
    peso = col_peso.number_input("Peso (kg):", min_value=30.0, max_value=300.0, value=peso_inicial,
                                 step=0.1, key="peso_pesagem")
    with col_botao:
        st.write("")
        st.write("")
        if st.button("Registrar", width="stretch"):
            db.registrar_peso(dia, peso)
            st.rerun()
    if perfil:
        st.caption("A pesagem mais recente atualiza o seu perfil, e a meta calórica se ajusta sozinha.")

    if pesos.empty:
        st.info("Nenhuma pesagem registrada ainda.")
        return

    if len(pesos) >= 2:
        variacao = pesos['peso_kg'].iloc[-1] - pesos['peso_kg'].iloc[0]
        st.metric("Variação desde a primeira pesagem", f"{pesos['peso_kg'].iloc[-1]:.1f} kg",
                  delta=f"{variacao:+.1f} kg", delta_color="off")
        fig = px.line(pesos, x='data', y='peso_kg', markers=True, labels={'data': 'Dia', 'peso_kg': 'kg'})
        st.plotly_chart(fig, width="stretch")

    with st.expander("Apagar uma pesagem"):
        id_peso = st.selectbox("Pesagem:", pesos['id'].tolist(), format_func=lambda x: (
            f"{pesos.loc[pesos['id'] == x, 'data'].values[0]:%d/%m/%Y} - "
            f"{pesos.loc[pesos['id'] == x, 'peso_kg'].values[0]:.1f} kg"))
        if st.button("🗑️ Apagar pesagem"):
            db.deletar_peso(id_peso)
            st.rerun()


st.title("📈 Histórico")
perfil = db.carregar_perfil()

_, col_meta = st.columns(2)
with col_meta:
    meta_calorias = campo_meta(perfil)

mostrar_calorias(db.carregar_historico(), meta_calorias)
st.divider()
mostrar_peso(perfil)
