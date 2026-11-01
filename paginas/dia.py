from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import db
import metas
from comum import CORES_MACROS, ICONES_REFEICOES, REFEICOES, campo_meta

COR_CONSUMIDO = '#66B2FF'
COR_RESTANTE = 'rgba(128, 128, 128, 0.25)'
COR_EXCEDIDO = '#FF9999'


def grafico_anel(consumido, meta):
    """Anel com o consumido em cor e o que falta em cinza; o número restante fica no centro."""
    restante = meta - consumido
    if restante >= 0:
        valores, cores = [consumido, restante], [COR_CONSUMIDO, COR_RESTANTE]
        texto, legenda = f"{restante:.0f}", "kcal restantes"
    else:
        valores, cores = [1], [COR_EXCEDIDO]
        texto, legenda = f"+{-restante:.0f}", "kcal acima da meta"

    fig = go.Figure(go.Pie(values=valores, hole=0.75, marker_colors=cores, sort=False,
                           direction='clockwise', textinfo='none', hoverinfo='skip'))
    fig.update_layout(
        showlegend=False, height=260, margin=dict(t=10, b=10, l=10, r=10),
        paper_bgcolor='rgba(0,0,0,0)',
        annotations=[dict(text=f"<span style='font-size:34px'><b>{texto}</b></span><br>{legenda}",
                          showarrow=False, font_size=14)],
    )
    return fig


def mostrar_saldo(df_dia, meta_calorias, perfil):
    consumido = df_dia['calorias'].sum()
    restante = meta_calorias - consumido

    col_anel, col_resumo = st.columns([2, 3])
    with col_anel:
        st.plotly_chart(grafico_anel(consumido, meta_calorias), width="stretch",
                        config={'displayModeBar': False})
    with col_resumo:
        # A "conta" do dia: meta - consumido = restante
        c1, c2, c3 = st.columns(3)
        c1.metric("🎯 Meta", f"{meta_calorias:.0f}")
        c2.metric("🍽️ Consumido", f"{consumido:.0f}")
        c3.metric("⏳ Restante" if restante >= 0 else "⚠️ Excedido", f"{abs(restante):.0f}")

        # As metas de macros acompanham a meta calórica (inclusive se ela for mudada à mão)
        meta_macros = metas.calcular_macros(meta_calorias, perfil['peso_kg'] if perfil else None)
        for nome, chave in [("🍞 Carboidratos", 'carboidratos'), ("🍗 Proteínas", 'proteinas'),
                            ("🥑 Gorduras", 'gorduras')]:
            valor, meta = df_dia[chave].sum(), meta_macros[chave]
            st.progress(min(valor / meta, 1.0), text=f"{nome}: {valor:.0f} de {meta:.0f} g")

        sodio_mg = df_dia['sodio'].sum() * 1000
        # 2000 mg é o limite diário de sódio recomendado pela OMS
        st.caption(f"🧂 Sódio: {sodio_mg:.0f} mg (limite recomendado: 2000 mg)")


def mostrar_agua(dia, perfil):
    meta_agua = metas.meta_agua_ml(perfil['peso_kg'] if perfil else None)
    total = db.total_agua(dia)

    col_info, col_botoes = st.columns([2, 3])
    with col_info:
        st.progress(min(total / meta_agua, 1.0), text=f"💧 Água: {total / 1000:.2f} de {meta_agua / 1000:.1f} L")
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


def escolher_refeicao(refeicao):
    # Roda antes da página recarregar, então a barra lateral já abre com a refeição escolhida
    st.session_state.refeicao_sidebar = refeicao
    st.toast(f"Escolha o alimento na barra lateral para o {refeicao}.", icon="👈")


def editar_item(item):
    """Botão ✏️ de cada alimento: abre uma janelinha para mudar o peso, a refeição ou apagar."""
    with st.popover("✏️", help="Editar ou apagar"):
        # A key inclui o id para cada alimento ter os seus próprios campos
        novo_peso = st.number_input("Peso (g):", min_value=1.0, value=float(item['porcao_g']),
                                    step=10.0, key=f"editar_peso_{item['id']}")
        nova_refeicao = st.selectbox("Refeição:", REFEICOES, key=f"editar_refeicao_{item['id']}",
                                     index=REFEICOES.index(item['refeicao'])
                                     if item['refeicao'] in REFEICOES else 0)
        col_salvar, col_apagar = st.columns(2)
        if col_salvar.button("💾 Salvar", key=f"salvar_{item['id']}", width="stretch"):
            db.atualizar_registro(item['id'], novo_peso, nova_refeicao)
            st.rerun()
        if col_apagar.button("❌ Apagar", key=f"apagar_{item['id']}", width="stretch"):
            db.deletar_consumo(item['id'])
            st.rerun()


def mostrar_diario(df_dia):
    st.subheader("📒 Diário")
    # Registros com refeição fora da lista (dados antigos) aparecem em "Outros"
    outros = sorted(set(df_dia['refeicao']) - set(REFEICOES))
    for refeicao in REFEICOES + (["Outros"] if outros else []):
        if refeicao == "Outros":
            itens = df_dia[df_dia['refeicao'].isin(outros)]
        else:
            itens = df_dia[df_dia['refeicao'] == refeicao]

        with st.container(border=True):
            col_titulo, col_total, col_botao = st.columns([4, 2, 2], vertical_alignment="center")
            col_titulo.markdown(f"**{ICONES_REFEICOES.get(refeicao, '🍽️')} {refeicao}**")
            col_total.markdown(f"**{itens['calorias'].sum():.0f} kcal**")
            if refeicao != "Outros":
                col_botao.button("➕ Adicionar", key=f"adicionar_{refeicao}", width="stretch",
                                 on_click=escolher_refeicao, args=(refeicao,))

            if itens.empty:
                st.caption("Nada registrado ainda.")
            for _, item in itens.iterrows():
                col_nome, col_kcal, col_editar = st.columns([6, 2, 1], vertical_alignment="center")
                col_nome.markdown(
                    f"{item['nome_alimento']}  \n"
                    f":gray[{item['porcao_g']:.0f} g · C {item['carboidratos']:.0f} g · "
                    f"P {item['proteinas']:.0f} g · G {item['gorduras']:.0f} g]"
                )
                col_kcal.markdown(f"{item['calorias']:.0f} kcal")
                with col_editar:
                    editar_item(item)


def mostrar_graficos(df_dia):
    with st.expander("📊 Gráficos do dia"):
        grafico1, grafico2 = st.columns(2)
        with grafico1:
            st.markdown("**Proporção da Dieta**")
            df_macros = pd.DataFrame({
                'Nutriente': ['Carboidratos', 'Proteínas', 'Gorduras'],
                'Gramas': [df_dia['carboidratos'].sum(), df_dia['proteinas'].sum(), df_dia['gorduras'].sum()]
            })
            if df_macros['Gramas'].sum() > 0:
                fig_pie = go.Figure(go.Pie(labels=df_macros['Nutriente'], values=df_macros['Gramas'],
                                           hole=0.5, marker_colors=CORES_MACROS))
                st.plotly_chart(fig_pie, width="stretch")
            else:
                st.info("Não há dados de macronutrientes suficientes para este gráfico.")
        with grafico2:
            st.markdown("**Calorias por Refeição**")
            df_agrupado = df_dia.groupby('refeicao')['calorias'].sum().reindex(REFEICOES).dropna()
            fig_bar = go.Figure(go.Bar(x=df_agrupado.index, y=df_agrupado.values, marker_color=COR_CONSUMIDO))
            fig_bar.update_layout(yaxis_title='kcal')
            st.plotly_chart(fig_bar, width="stretch")


st.title("📅 Controle Diário")
perfil = db.carregar_perfil()
df = db.carregar_historico()

col_calendario, col_meta = st.columns(2)
with col_calendario:
    dia_selecionado = st.date_input("Filtrar por data:", datetime.now().date())
with col_meta:
    meta_calorias = campo_meta(perfil)

df_dia = df[df['data_apenas'] == dia_selecionado]

st.divider()
mostrar_saldo(df_dia, meta_calorias, perfil)
mostrar_agua(dia_selecionado, perfil)
st.divider()
if df.empty:
    st.info("👈 Use o menu lateral esquerdo para adicionar sua primeira refeição!")
mostrar_diario(df_dia)
if not df_dia.empty:
    mostrar_graficos(df_dia)
