# Partes usadas por mais de uma página do app
import streamlit as st

import metas

REFEICOES = ["Café da Manhã", "Almoço", "Lanche", "Jantar"]
ICONES_REFEICOES = {"Café da Manhã": "☀️", "Almoço": "🍛", "Lanche": "🍎", "Jantar": "🌙"}

# Paleta do app: as mesmas cores do tema em .streamlit/config.toml.
# Tons médios, que ficam legíveis tanto no modo claro quanto no escuro.
COR_PRINCIPAL = '#2F9E6A'   # verde-folha: consumido, dentro da meta
COR_EXCEDIDO = '#E4572E'    # tomate: acima da meta
COR_RESTANTE = 'rgba(128, 128, 128, 0.22)'  # cinza transparente: o que ainda falta
COR_CARBOIDRATOS = '#E9A23B'  # trigo
COR_PROTEINAS = '#C8507A'     # framboesa
COR_GORDURAS = '#3A8FB7'      # azul-petróleo
CORES_MACROS = [COR_CARBOIDRATOS, COR_PROTEINAS, COR_GORDURAS]  # na ordem carboidratos, proteínas, gorduras


def campo_meta(perfil):
    """Mostra o campo da meta diária (calculada pelo perfil, mas editável) e retorna o valor."""
    calculo = metas.calcular_meta(perfil) if perfil else None
    sugerida = round(calculo['meta']) if calculo else 2000
    meta = st.number_input("Meta diária (kcal):", min_value=500, value=sugerida, step=50)
    if calculo:
        st.caption(
            f"Calculada pelo seu perfil: metabolismo basal {calculo['tmb']:.0f} kcal · "
            f"gasto diário {calculo['gasto']:.0f} kcal · objetivo: {perfil['objetivo'].lower()}."
        )
    else:
        st.caption("Sem perfil, a meta padrão é 2000 kcal.")
        st.page_link("paginas/perfil.py", label="Preencher meu perfil", icon="👤")
    return meta
