# Partes usadas por mais de uma página do app
import streamlit as st

import metas

REFEICOES = ["Café da Manhã", "Almoço", "Lanche", "Jantar"]
CORES_MACROS = ['#FF9999', '#66B2FF', '#99FF99']


def campo_meta(perfil):
    """Mostra o campo da meta diária (calculada pelo perfil, mas editável) e retorna o valor."""
    calculo = metas.calcular_meta(perfil) if perfil else None
    sugerida = round(calculo['meta']) if calculo else 2000
    meta = st.number_input("Sua Meta Diária (kcal):", min_value=500, value=sugerida, step=50)
    if calculo:
        st.caption(
            f"Calculada pelo seu perfil: metabolismo basal {calculo['tmb']:.0f} kcal · "
            f"gasto diário {calculo['gasto']:.0f} kcal · objetivo: {perfil['objetivo'].lower()}."
        )
    else:
        st.caption("Sem perfil, a meta padrão é 2000 kcal.")
        st.page_link("paginas/perfil.py", label="Preencher meu perfil", icon="👤")
    return meta
