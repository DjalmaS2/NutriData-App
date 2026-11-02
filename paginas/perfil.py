import streamlit as st

import db
import metas

st.title("Meu perfil")
st.caption("Com o perfil preenchido, o app calcula as suas metas de calorias, macronutrientes e água.")

perfil = db.carregar_perfil()
atual = perfil or {}
opcoes_sexo = ["Feminino", "Masculino"]
opcoes_atividade = list(metas.FATORES_ATIVIDADE)
opcoes_objetivo = list(metas.AJUSTE_OBJETIVO)

col_form, col_metas = st.columns(2)

with col_form:
    with st.form("form_perfil"):
        sexo = st.radio("Sexo:", opcoes_sexo, horizontal=True,
                        index=opcoes_sexo.index(atual.get('sexo', "Feminino")))
        idade = st.number_input("Idade:", min_value=14, max_value=100, value=atual.get('idade', 30))
        peso = st.number_input("Peso (kg):", min_value=30.0, max_value=300.0,
                               value=float(atual.get('peso_kg', 70.0)), step=0.5)
        altura = st.number_input("Altura (cm):", min_value=100.0, max_value=230.0,
                                 value=float(atual.get('altura_cm', 170.0)), step=1.0)
        atividade = st.selectbox("Nível de atividade:", opcoes_atividade,
                                 index=opcoes_atividade.index(atual.get('atividade', opcoes_atividade[0])))
        objetivo = st.selectbox("Objetivo:", opcoes_objetivo,
                                index=opcoes_objetivo.index(atual.get('objetivo', "Manter peso")))
        # value=None deixa o campo vazio: a meta de peso é opcional
        peso_meta = st.number_input("Meta de peso (kg, opcional):", min_value=30.0, max_value=300.0,
                                    value=atual.get('peso_meta'), step=0.5, placeholder="ex: 75",
                                    help="Com uma meta, o Histórico mostra quando você deve chegar lá.")
        somar_exercicio = st.checkbox(
            "Somar as calorias dos exercícios à meta do dia",
            value=bool(atual.get('somar_exercicio', 0)),
            help="O nível de atividade acima já considera os exercícios de costume. Se marcar esta opção, "
                 "escolha 'Sedentário', senão os exercícios serão contados duas vezes."
        )
        if st.form_submit_button("Salvar perfil", type="primary", width="stretch"):
            db.salvar_perfil(sexo, idade, peso, altura, atividade, objetivo, somar_exercicio, peso_meta)
            st.rerun()

with col_metas:
    st.subheader("Suas metas")
    if perfil is None:
        st.info("Preencha e salve o perfil para ver as suas metas.")
    else:
        calculo = metas.calcular_meta(perfil)
        macros = metas.calcular_macros(calculo['meta'], perfil['peso_kg'])
        st.metric("🔥 Calorias por dia", f"{calculo['meta']:.0f} kcal")
        c1, c2, c3 = st.columns(3)
        c1.metric("🍞 Carboidratos", f"{macros['carboidratos']:.0f} g")
        c2.metric("🍗 Proteínas", f"{macros['proteinas']:.0f} g")
        c3.metric("🥑 Gorduras", f"{macros['gorduras']:.0f} g")
        c4, c5 = st.columns(2)
        c4.metric("💧 Água", f"{metas.meta_agua_ml(perfil['peso_kg']) / 1000:.1f} L")
        if perfil.get('peso_meta'):
            falta = perfil['peso_meta'] - perfil['peso_kg']
            c5.metric("⚖️ Meta de peso", f"{perfil['peso_meta']:g} kg",
                      delta=f"faltam {abs(falta):.1f} kg" if abs(falta) >= 0.1 else "alcançada!",
                      delta_color="off")
        with st.expander("Como as metas são calculadas"):
            st.markdown(
                f"1. **Metabolismo basal** (fórmula de Mifflin-St Jeor): {calculo['tmb']:.0f} kcal, "
                "o que o corpo gasta em repouso.\n"
                f"2. **Gasto diário**: metabolismo basal × nível de atividade = {calculo['gasto']:.0f} kcal.\n"
                f"3. **Meta**: gasto diário ajustado ao objetivo ({perfil['objetivo'].lower()}), "
                f"nunca abaixo de {metas.META_MINIMA} kcal.\n"
                "4. **Macros**: proteína de 1,6 g por kg, gordura com 25% das calorias "
                "e carboidrato com o restante.\n"
                "5. **Água**: 35 ml por kg de peso."
            )
