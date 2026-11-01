import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
from PIL import Image
from pyzbar.pyzbar import decode

import api
import db

# --- 1. CONFIGURAÇÕES VISUAIS ---
st.set_page_config(page_title="NutriData Pro", layout="wide", page_icon="🍏")
st.title("🍏 NutriData - Dashboard Inteligente")

# --- 2. BANCO DE DADOS ---
# Garante que as tabelas existem (essencial no primeiro acesso / no deploy)
db.criar_tabelas()

ALIMENTOS_SALVOS = {
    "Nutella": "3017620422003",
    "Coca-Cola Lata": "7894900011517",
    "Aveia em Flocos Quaker": "7891000370643",
    "Digitar Novo Código...": "novo"
}

# --- 3. FUNÇÕES DO BACKEND (a lógica de API e banco fica em api.py e db.py) ---
def registrar_alimento(codigo_barras, peso, refeicao):
    """Busca o produto e salva no histórico. Retorna (sucesso, mensagem)."""
    try:
        produto = api.buscar_produto(codigo_barras)
    except api.ErroAPI as erro:
        return False, str(erro)
    if produto is None:
        return False, "Produto não achado na API."

    porcao = api.calcular_porcao(produto, peso)
    db.salvar_consumo(
        refeicao, produto['nome'], peso, porcao['calorias'], porcao['carboidratos'],
        porcao['proteinas'], porcao['gorduras'], porcao['sodio']
    )
    return True, produto['nome']

def ler_codigo_da_imagem(imagem_camera):
    img = Image.open(imagem_camera)
    codigos = decode(img)
    if codigos:
        return codigos[0].data.decode('utf-8')
    return None

# --- 4. BARRA LATERAL (Interface de Entrada) ---
with st.sidebar:
    st.header("🍽️ Adicionar Refeição")
    refeicao_input = st.selectbox("Refeição:", ["Café da Manhã", "Almoço", "Lanche", "Jantar"])
    peso_input = st.number_input("Peso consumido (g):", min_value=1.0, value=100.0, step=10.0)
    
    aba_scan, aba_api, aba_meus = st.tabs(["📷 Câmera", "🔍 Digitar", "⭐ Meus Pratos"])
    
    with aba_scan:
        # 1. Cria a memória do botão (começa desligado)
        if 'usar_camera' not in st.session_state:
            st.session_state.usar_camera = False

        # 2. O Botão que liga e desliga
        if st.button("📸 Ligar / Desligar Câmera", width="stretch"):
            # Inverte o estado (se tá ligado, desliga. Se tá desligado, liga)
            st.session_state.usar_camera = not st.session_state.usar_camera
            st.rerun()

        # 3. Só mostra a câmera SE o botão estiver ligado
        if st.session_state.usar_camera:
            st.write("Aponte o código de barras para a câmera:")
            foto = st.camera_input("Scanear", label_visibility="collapsed")
            
            if foto is not None:
                codigo_scaneado = ler_codigo_da_imagem(foto)
                if codigo_scaneado:
                    st.success(f"Código lido: {codigo_scaneado}")
                    if st.button("Buscar e Salvar", key="btn_scan", width="stretch"):
                        sucesso, mensagem = registrar_alimento(codigo_scaneado, float(peso_input), refeicao_input)
                        if sucesso: 
                            st.success(f"✅ {mensagem} salvo!")
                            # Opcional: Desliga a câmera automaticamente após salvar
                            st.session_state.usar_camera = False
                            st.rerun()
                        else: 
                            st.error(f"❌ {mensagem}")
                else:
                    st.warning("Nenhum código detectado. Tente aproximar ou melhorar o foco.")
        else:
            # Mensagem quando a câmera estiver escondida
            st.info("Câmera em modo de economia. Clique no botão acima para usar.")

    with aba_api:
        codigo_input = st.text_input("Digite o Código de Barras:")
        if st.button("Buscar e Salvar", key="btn_api", width="stretch"):
            sucesso, mensagem = registrar_alimento(codigo_input, float(peso_input), refeicao_input)
            if sucesso: st.success(f"✅ {mensagem} salvo!")
            else: st.error(f"❌ {mensagem}")

    with aba_meus:
        df_meus = db.carregar_meus_alimentos()
        if df_meus.empty:
            st.info("Você ainda não tem pratos customizados salvos no banco.")
        else:
            prato_escolhido = st.selectbox("Escolha seu prato:", df_meus['nome_alimento'].tolist())
            if st.button("Salvar Refeição Rápida", width="stretch"):
                prato_dados = df_meus[df_meus['nome_alimento'] == prato_escolhido].iloc[0]
                fator = float(peso_input) / prato_dados['porcao_g']
                db.salvar_consumo(
                    refeicao_input, prato_escolhido, peso_input,
                    prato_dados['calorias'] * fator, prato_dados['carboidratos'] * fator,
                    prato_dados['proteinas'] * fator, prato_dados['gorduras'] * fator, 0
                )
                st.success(f"✅ {prato_escolhido} adicionado à dieta!")
                st.rerun()

# --- 5. O DASHBOARD VISUAL ---
df = db.carregar_historico()

if df.empty:
    st.info("👈 Use o menu lateral esquerdo para adicionar sua primeira refeição!")
else:
    st.subheader("📅 Controle Diário")
    col_calendario, col_meta = st.columns(2)
    
    with col_calendario:
        data_hoje = datetime.now().date()
        dia_selecionado = st.date_input("Filtrar por data:", data_hoje)
        
    with col_meta:
        meta_calorias = st.number_input("Sua Meta Diária (kcal):", min_value=500, value=2000, step=100)

    df_dia = df[df['data_apenas'] == dia_selecionado]

    if df_dia.empty:
        st.warning(f"Nenhuma refeição registrada para o dia {dia_selecionado.strftime('%d/%m/%Y')}.")
    else:
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

        st.subheader(f"📊 Resumo do Dia ({dia_selecionado.strftime('%d/%m')})")
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("🔥 Calorias", f"{df_dia['calorias'].sum():.0f} kcal")
        col2.metric("🍞 Carboidratos", f"{df_dia['carboidratos'].sum():.0f} g")
        col3.metric("🍗 Proteínas", f"{df_dia['proteinas'].sum():.0f} g")
        col4.metric("🥑 Gorduras", f"{df_dia['gorduras'].sum():.0f} g")
        col5.metric("🧂 Sódio", f"{df_dia['sodio'].sum() * 1000:.0f} mg")
        
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
                                 color_discrete_sequence=['#FF9999', '#66B2FF', '#99FF99'])
                st.plotly_chart(fig_pie, width="stretch")
            else:
                st.info("Não há dados de macronutrientes suficientes para este gráfico.")
            
        with grafico2:
            st.subheader("Calorias por Refeição")
            df_agrupado = df_dia.groupby('refeicao')['calorias'].sum().reset_index()
            fig_bar = px.bar(df_agrupado, x='refeicao', y='calorias', color='refeicao')
            st.plotly_chart(fig_bar, width="stretch")
            
        st.divider()
        st.subheader("🗑️ Gerenciar Registros do Dia")
        
        lista_ids = df_dia['id'].tolist()
        if len(lista_ids) > 0:
            col_select, col_botao = st.columns([3, 1])
            with col_select:
                id_para_deletar = st.selectbox(
                    "Selecione a refeição que deseja apagar:", 
                    options=lista_ids,
                    format_func=lambda x: f"ID {x} - {df_dia[df_dia['id'] == x]['nome_alimento'].values[0]} ({df_dia[df_dia['id'] == x]['porcao_g'].values[0]}g)"
                )
            with col_botao:
                st.write("") 
                st.write("")
                if st.button("❌ Apagar Registro", width="stretch"):
                    db.deletar_consumo(id_para_deletar)
                    st.success("Apagado com sucesso!")
                    st.rerun()