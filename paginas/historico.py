from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

import db
import metas
from comum import COR_EXCEDIDO, COR_PRINCIPAL, CORES_MACROS, campo_meta


def texto_previsao(semanas):
    """'cerca de 12 semanas (por volta de 25/01/2027)'"""
    data = datetime.now().date() + timedelta(weeks=semanas)
    quanto = "menos de 1 semana" if semanas < 1 else f"cerca de {semanas:.0f} semanas"
    return f"{quanto} (por volta de {data:%d/%m/%Y})"


def mostrar_meta_peso(perfil, pesos, peso_meta):
    peso_atual = float(pesos['peso_kg'].iloc[-1]) if not pesos.empty else float(perfil['peso_kg'])
    peso_inicial = float(pesos['peso_kg'].iloc[0]) if not pesos.empty else peso_atual
    falta = peso_meta - peso_atual

    with st.container(border=True):
        st.markdown(f"**🎯 Meta: {peso_meta:g} kg**")
        if abs(falta) < 0.1:
            st.success("Meta de peso alcançada! Que tal definir uma nova no Perfil?")
            return
        # Progresso desde a primeira pesagem (0% no início, 100% na meta)
        caminho = peso_meta - peso_inicial
        progresso = (peso_atual - peso_inicial) / caminho if caminho else 0
        st.progress(min(max(progresso, 0.0), 1.0),
                    text=f"Faltam {abs(falta):.1f} kg ({max(progresso, 0):.0%} do caminho desde {peso_inicial:g} kg)")

        ajuste = metas.AJUSTE_OBJETIVO[perfil['objetivo']]
        semanas_plano = metas.semanas_pelo_plano(peso_atual, peso_meta, ajuste)
        if semanas_plano is None:
            st.caption(f"📋 O objetivo do perfil ({perfil['objetivo'].lower()}) não leva até a meta. "
                       "Ajuste o objetivo no Perfil.")
        else:
            st.markdown(f"📋 **Seguindo o plano** ({ajuste:+d} kcal por dia): {texto_previsao(semanas_plano)}")

        ritmo = metas.ritmo_real_kg_semana(pesos)
        if ritmo is None:
            st.caption("📉 Registre pesagens por pelo menos uma semana para ver a previsão pelo seu ritmo real.")
        else:
            semanas_ritmo = metas.semanas_pelo_ritmo(peso_atual, peso_meta, ritmo)
            if semanas_ritmo is None:
                st.markdown(f"📉 **No seu ritmo real** ({ritmo:+.1f} kg por semana) você está se afastando "
                            "da meta.")
            else:
                st.markdown(f"📉 **No seu ritmo real** ({ritmo:+.1f} kg por semana): {texto_previsao(semanas_ritmo)}")
            # Mais de 1% do peso por semana é rápido demais para a maioria das pessoas
            if abs(ritmo) > peso_atual * 0.01:
                st.warning("O seu peso está mudando mais de 1% por semana. Vale conversar com um "
                           "nutricionista para fazer isso com segurança.")
        st.caption(f"Estimativas: 1 kg de peso corporal equivale a cerca de {metas.KCAL_POR_KG} kcal. "
                   "O corpo nem sempre segue a conta à risca.")


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

    st.subheader("Calorias por dia")
    df_grafico = por_dia.reset_index()
    df_grafico['Situação'] = df_grafico['calorias'].map(
        lambda c: 'Acima da meta' if c > meta_calorias else 'Dentro da meta')
    fig = px.bar(df_grafico, x='Dia', y='calorias', color='Situação',
                 color_discrete_map={'Dentro da meta': COR_PRINCIPAL, 'Acima da meta': COR_EXCEDIDO},
                 labels={'calorias': 'kcal'})
    # Legenda em cima do gráfico, para não cortar os nomes nas telas menores
    fig.update_layout(legend=dict(orientation='h', y=1.12, title_text=''))
    fig.add_hline(y=meta_calorias, line_dash='dash', annotation_text=f"Meta: {meta_calorias} kcal")
    st.plotly_chart(fig, width="stretch")

    st.subheader("Macronutrientes por dia (g)")
    df_macros = df_grafico.melt(id_vars='Dia', value_vars=['carboidratos', 'proteinas', 'gorduras'],
                                var_name='Nutriente', value_name='Gramas')
    df_macros['Nutriente'] = df_macros['Nutriente'].str.capitalize()
    fig_macros = px.bar(df_macros, x='Dia', y='Gramas', color='Nutriente',
                        color_discrete_sequence=CORES_MACROS)
    fig_macros.update_layout(legend=dict(orientation='h', y=1.12, title_text=''))
    st.plotly_chart(fig_macros, width="stretch")


def mostrar_peso(perfil):
    st.subheader("Peso corporal")
    pesos = db.carregar_pesos()

    if not pesos.empty:
        peso_inicial = float(pesos['peso_kg'].iloc[-1])
    else:
        peso_inicial = float(perfil['peso_kg']) if perfil else 70.0
    col_data, col_peso, col_botao = st.columns([2, 2, 1])
    dia = col_data.date_input("Dia da pesagem:", datetime.now().date(), key="dia_pesagem",
                                format="DD/MM/YYYY")
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

    peso_meta = perfil.get('peso_meta') if perfil else None
    if peso_meta:
        mostrar_meta_peso(perfil, pesos, peso_meta)

    if pesos.empty:
        st.info("Nenhuma pesagem registrada ainda.")
        return

    if len(pesos) >= 2:
        variacao = pesos['peso_kg'].iloc[-1] - pesos['peso_kg'].iloc[0]
        st.metric("Variação desde a primeira pesagem", f"{pesos['peso_kg'].iloc[-1]:.1f} kg",
                  delta=f"{variacao:+.1f} kg", delta_color="off")
        fig = px.line(pesos, x='data', y='peso_kg', markers=True, labels={'data': 'Dia', 'peso_kg': 'kg'},
                      color_discrete_sequence=[COR_PRINCIPAL])
        if peso_meta:
            fig.add_hline(y=peso_meta, line_dash='dash', annotation_text=f"Meta: {peso_meta:g} kg")
        st.plotly_chart(fig, width="stretch")

    with st.expander("Apagar uma pesagem"):
        id_peso = st.selectbox("Pesagem:", pesos['id'].tolist(), format_func=lambda x: (
            f"{pesos.loc[pesos['id'] == x, 'data'].values[0]:%d/%m/%Y} - "
            f"{pesos.loc[pesos['id'] == x, 'peso_kg'].values[0]:.1f} kg"))
        if st.button("🗑️ Apagar pesagem"):
            db.deletar_peso(id_peso)
            st.rerun()


st.title("Histórico")
st.caption("Como você tem se saído nas últimas semanas: calorias, macronutrientes e peso.")
perfil = db.carregar_perfil()

_, col_meta = st.columns(2)
with col_meta:
    meta_calorias = campo_meta(perfil)

mostrar_calorias(db.carregar_historico(), meta_calorias)
st.divider()
mostrar_peso(perfil)
