import pandas as pd
import streamlit as st

import api
import db
import taco


def montar_prato():
    st.subheader("Montar um Prato")
    st.caption("Junte os ingredientes de uma receita e salve como prato. "
               "Depois é só registrar pela aba **⭐ Meus Pratos** na barra lateral.")

    # Os ingredientes ficam na memória da sessão até o prato ser salvo
    if 'ingredientes' not in st.session_state:
        st.session_state.ingredientes = []

    col_busca, col_gramas = st.columns([3, 1])
    with col_busca:
        termo = st.text_input("Ingrediente (Tabela TACO):", key="busca_ingrediente",
                              placeholder="ex: arroz cozido, frango grelhado")
    with col_gramas:
        gramas = st.number_input("Quantidade (g):", min_value=1.0, value=100.0, step=10.0,
                                 key="gramas_ingrediente")

    if termo:
        resultados = taco.buscar(termo)
        if resultados.empty:
            st.warning("Nenhum alimento encontrado. Tente outra palavra.")
        else:
            id_escolhido = st.selectbox(
                f"{len(resultados)} resultado(s):", resultados['id'].tolist(), key="escolha_ingrediente",
                format_func=lambda x: resultados.loc[resultados['id'] == x, 'nome'].values[0]
            )
            if st.button("➕ Adicionar ingrediente"):
                produto = taco.como_produto(resultados[resultados['id'] == id_escolhido].iloc[0])
                porcao = api.calcular_porcao(produto, gramas)
                st.session_state.ingredientes.append(
                    {'Ingrediente': produto['nome'], 'Gramas': gramas, **{k: float(v) for k, v in porcao.items()}}
                )

    ingredientes = pd.DataFrame(st.session_state.ingredientes)
    if ingredientes.empty:
        return

    tabela = ingredientes.assign(sodio=ingredientes['sodio'] * 1000).rename(columns={
        'calorias': 'kcal', 'carboidratos': 'Carb (g)', 'proteinas': 'Prot (g)',
        'gorduras': 'Gord (g)', 'sodio': 'Sódio (mg)', 'fibras': 'Fibras (g)', 'calcio': 'Cálcio (mg)',
        'ferro': 'Ferro (mg)', 'vitamina_c': 'Vit. C (mg)', 'potassio': 'Potássio (mg)'})
    st.dataframe(tabela.round(1), hide_index=True, width="stretch")

    soma_gramas = ingredientes['Gramas'].sum()
    st.markdown(f"**Total:** {soma_gramas:.0f} g · {ingredientes['calorias'].sum():.0f} kcal")

    with st.form("form_prato"):
        nome_prato = st.text_input("Nome do prato:", placeholder="ex: Marmita de frango")
        # Cozinhar muda o peso (a água evapora ou é absorvida), então dá para corrigir
        peso_final = st.number_input(
            "Peso do prato pronto (g):", min_value=1.0, value=float(soma_gramas),
            help="Pese o prato depois de pronto. Se não souber, deixe a soma dos ingredientes."
        )
        salvar = st.form_submit_button("💾 Salvar prato", width="stretch")
    if salvar:
        if not nome_prato.strip():
            st.error("Dê um nome ao prato.")
        else:
            db.salvar_prato(nome_prato.strip(), peso_final,
                            {n: ingredientes[n].sum() for n in db.NUTRIENTES})
            st.session_state.ingredientes = []
            st.rerun()

    if st.button("🧹 Limpar ingredientes"):
        st.session_state.ingredientes = []
        st.rerun()


def listar_pratos():
    st.subheader("📋 Pratos Salvos")
    df_meus = db.carregar_meus_alimentos()
    if df_meus.empty:
        st.info("Nenhum prato salvo ainda.")
        return
    for _, prato in df_meus.iterrows():
        col_info, col_apagar = st.columns([5, 1])
        col_info.markdown(
            f"**{prato['nome_alimento']}** — {prato['porcao_g']:.0f} g · {prato['calorias']:.0f} kcal · "
            f"C {prato['carboidratos']:.0f} g · P {prato['proteinas']:.0f} g · G {prato['gorduras']:.0f} g"
        )
        if col_apagar.button("🗑️", key=f"apagar_prato_{prato['id']}", help="Apagar prato"):
            db.deletar_prato(prato['id'])
            st.rerun()


st.title("🍲 Meus Pratos")
montar_prato()
st.divider()
listar_pratos()
