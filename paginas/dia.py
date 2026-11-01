from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

import db
import metas
from comum import CORES_MACROS, REFEICOES, campo_meta


def mostrar_agua(dia, perfil):
    st.subheader("💧 Água")
    meta_agua = metas.meta_agua_ml(perfil['peso_kg'] if perfil else None)
    total = db.total_agua(dia)

    col_info, col_botoes = st.columns([2, 3])
    with col_info:
        st.markdown(f"**{total / 1000:.2f} L** de {meta_agua / 1000:.1f} L")
        st.progress(min(total / meta_agua, 1.0))
    with col_botoes:
        b1, b2, b3 = st.columns(3)
        if b1.button("🥛 +250 ml", width="stretch"):
            db.registrar_agua(dia, 250)
            st.rerun()
        if b2.button("🍶 +500 ml", width="stretch"):
            db.registrar_agua(dia, 500)
            st.rerun()
        if b3.button("↩️ Desfazer", width="stretch", disabled=total == 0):
            db.desfazer_agua(dia)
            st.rerun()


def mostrar_resumo(df_dia, dia, meta_calorias, perfil):
    total_calorias_dia = df_dia['calorias'].sum()
    porcentagem = total_calorias_dia / meta_calorias

    st.markdown(f"**Progresso:** {total_calorias_dia:.0f} kcal consumidas de {meta_calorias} kcal.")
    st.progress(min(porcentagem, 1.0))

    if porcentagem > 1.0:
        st.error("⚠️ Você ultrapassou a sua meta diária de calorias!")
    elif porcentagem >= 0.8:
        st.warning("Atenção: Você está perto de atingir sua meta!")
    else:
        st.success("Você está dentro da meta calórica!")

    st.divider()

    st.subheader(f"📊 Resumo do Dia ({dia.strftime('%d/%m')})")
    # As metas de macros acompanham a meta calórica (inclusive se ela for mudada à mão)
    meta_macros = metas.calcular_macros(meta_calorias, perfil['peso_kg'] if perfil else None)
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("🔥 Calorias", f"{total_calorias_dia:.0f} kcal")
    col1.caption(f"meta {meta_calorias} kcal")
    for coluna, nome, chave in [(col2, "🍞 Carboidratos", 'carboidratos'),
                                (col3, "🍗 Proteínas", 'proteinas'),
                                (col4, "🥑 Gorduras", 'gorduras')]:
        consumido, meta = df_dia[chave].sum(), meta_macros[chave]
        coluna.metric(nome, f"{consumido:.0f} g")
        coluna.progress(min(consumido / meta, 1.0))
        coluna.caption(f"meta {meta:.0f} g · faltam {max(meta - consumido, 0):.0f} g")
    col5.metric("🧂 Sódio", f"{df_dia['sodio'].sum() * 1000:.0f} mg")
    # 2000 mg é o limite diário de sódio recomendado pela OMS
    col5.caption("limite recomendado: 2000 mg")

    st.divider()

    grafico1, grafico2 = st.columns(2)
    with grafico1:
        st.subheader("Proporção da Dieta")
        df_macros = pd.DataFrame({
            'Nutriente': ['Carboidratos', 'Proteínas', 'Gorduras'],
            'Gramas': [df_dia['carboidratos'].sum(), df_dia['proteinas'].sum(), df_dia['gorduras'].sum()]
        })
        if df_macros['Gramas'].sum() > 0:
            fig_pie = px.pie(df_macros, values='Gramas', names='Nutriente', hole=0.5,
                             color_discrete_sequence=CORES_MACROS)
            st.plotly_chart(fig_pie, width="stretch")
        else:
            st.info("Não há dados de macronutrientes suficientes para este gráfico.")

    with grafico2:
        st.subheader("Calorias por Refeição")
        df_agrupado = df_dia.groupby('refeicao')['calorias'].sum().reset_index()
        fig_bar = px.bar(df_agrupado, x='refeicao', y='calorias', color='refeicao')
        st.plotly_chart(fig_bar, width="stretch")


def mostrar_edicao(df_dia):
    st.subheader("✏️ Editar ou Apagar Registros do Dia")

    id_registro = st.selectbox(
        "Selecione o registro:",
        options=df_dia['id'].tolist(),
        format_func=lambda x: f"ID {x} - {df_dia[df_dia['id'] == x]['nome_alimento'].values[0]} ({df_dia[df_dia['id'] == x]['porcao_g'].values[0]:.0f}g)"
    )
    registro = df_dia[df_dia['id'] == id_registro].iloc[0]
    col_peso, col_refeicao, col_salvar, col_apagar = st.columns([2, 2, 1, 1])
    # A key inclui o id para os campos trocarem de valor ao escolher outro registro
    novo_peso = col_peso.number_input("Peso (g):", min_value=1.0, value=float(registro['porcao_g']),
                                      step=10.0, key=f"editar_peso_{id_registro}")
    nova_refeicao = col_refeicao.selectbox("Refeição:", REFEICOES, key=f"editar_refeicao_{id_registro}",
                                           index=REFEICOES.index(registro['refeicao'])
                                           if registro['refeicao'] in REFEICOES else 0)
    with col_salvar:
        st.write("")
        st.write("")
        if st.button("💾 Salvar", width="stretch"):
            db.atualizar_registro(id_registro, novo_peso, nova_refeicao)
            st.rerun()
    with col_apagar:
        st.write("")
        st.write("")
        if st.button("❌ Apagar", width="stretch"):
            db.deletar_consumo(id_registro)
            st.rerun()


st.title("📅 Controle Diário")
perfil = db.carregar_perfil()
df = db.carregar_historico()

col_calendario, col_meta = st.columns(2)
with col_calendario:
    dia_selecionado = st.date_input("Filtrar por data:", datetime.now().date())
with col_meta:
    meta_calorias = campo_meta(perfil)

st.divider()
mostrar_agua(dia_selecionado, perfil)
st.divider()

df_dia = df[df['data_apenas'] == dia_selecionado]
if df.empty:
    st.info("👈 Use o menu lateral esquerdo para adicionar sua primeira refeição!")
elif df_dia.empty:
    st.warning(f"Nenhuma refeição registrada para o dia {dia_selecionado.strftime('%d/%m/%Y')}.")
else:
    mostrar_resumo(df_dia, dia_selecionado, meta_calorias, perfil)
    st.divider()
    mostrar_edicao(df_dia)
