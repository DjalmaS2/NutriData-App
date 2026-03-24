import streamlit as st
import sqlite3
import pandas as pd
import requests
from datetime import datetime
import plotly.express as px
from PIL import Image
from pyzbar.pyzbar import decode

# --- 1. CONFIGURAÇÕES VISUAIS ---
st.set_page_config(page_title="NutriData Pro", layout="wide", page_icon="🍏")
st.title("🍏 NutriData - Dashboard Inteligente")

# --- 2. BANCO DE DADOS PRÉ-SALVOS ---
ALIMENTOS_SALVOS = {
    "Nutella": "3017620422003",
    "Coca-Cola Lata": "7894900011517",
    "Aveia em Flocos Quaker": "7891000370643",
    "Digitar Novo Código...": "novo"
}

# --- 3. FUNÇÕES DO BACKEND (Todas as funções devem ficar aqui em cima!) ---
def salvar_no_banco(refeicao, nome, peso, calorias, carb, prot, gord, sodio):
    conexao = sqlite3.connect('nutridata.db')
    cursor = conexao.cursor()
    data_atual = datetime.now().strftime('%Y-%m-%d %H:%M')
    cursor.execute('''
        INSERT INTO historico_consumo 
        (data_registro, refeicao, nome_alimento, porcao_g, calorias, carboidratos, proteinas, gorduras, sodio)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (data_atual, refeicao, nome, peso, calorias, carb, prot, gord, sodio))
    conexao.commit()
    conexao.close()

def registrar_alimento(codigo_barras, peso, refeicao):
    url = f"https://world.openfoodfacts.org/api/v0/product/{codigo_barras}.json"
    resposta = requests.get(url)
    if resposta.status_code == 200 and resposta.json().get('status') == 1:
        nutrientes = resposta.json()['product'].get('nutriments', {})
        nome = resposta.json()['product'].get('product_name', 'Nome Desconhecido')
        
        calorias = (nutrientes.get('energy-kcal_100g', 0) / 100) * peso
        carb = (nutrientes.get('carbohydrates_100g', 0) / 100) * peso
        prot = (nutrientes.get('proteins_100g', 0) / 100) * peso
        gord = (nutrientes.get('fat_100g', 0) / 100) * peso
        sodio = (nutrientes.get('sodium_100g', 0) / 100) * peso
        
        salvar_no_banco(refeicao, nome, peso, calorias, carb, prot, gord, sodio)
        return True, nome
    return False, ""

def carregar_dados():
    conexao = sqlite3.connect('nutridata.db')
    df = pd.read_sql_query("SELECT * FROM historico_consumo", conexao)
    conexao.close()
    if not df.empty:
        df['data_registro'] = pd.to_datetime(df['data_registro'])
        df['data_apenas'] = df['data_registro'].dt.date 
    return df

def deletar_do_banco(id_registro):
    conexao = sqlite3.connect('nutridata.db')
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM historico_consumo WHERE id = ?", (id_registro,))
    conexao.commit()
    conexao.close()

def ler_codigo_da_imagem(imagem_camera):
    img = Image.open(imagem_camera)
    codigos = decode(img)
    if codigos:
        return codigos[0].data.decode('utf-8')
    return None

def carregar_meus_alimentos():
    conexao = sqlite3.connect('nutridata.db')
    try:
        df_meus = pd.read_sql_query("SELECT * FROM meus_alimentos", conexao)
    except:
        df_meus = pd.DataFrame() 
    conexao.close()
    return df_meus

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
                        sucesso, nome = registrar_alimento(codigo_scaneado, float(peso_input), refeicao_input)
                        if sucesso: 
                            st.success(f"✅ {nome} salvo!")
                            # Opcional: Desliga a câmera automaticamente após salvar
                            st.session_state.usar_camera = False
                            st.rerun()
                        else: 
                            st.error("❌ Produto não achado na API.")
                else:
                    st.warning("Nenhum código detectado. Tente aproximar ou melhorar o foco.")
        else:
            # Mensagem quando a câmera estiver escondida
            st.info("Câmera em modo de economia. Clique no botão acima para usar.")

    with aba_api:
        codigo_input = st.text_input("Digite o Código de Barras:")
        if st.button("Buscar e Salvar", key="btn_api", width="stretch"):
            sucesso, nome = registrar_alimento(codigo_input, float(peso_input), refeicao_input)
            if sucesso: st.success(f"✅ {nome} salvo!")
            else: st.error("❌ Produto não achado na API.")

    with aba_meus:
        df_meus = carregar_meus_alimentos()
        if df_meus.empty:
            st.info("Você ainda não tem pratos customizados salvos no banco.")
        else:
            prato_escolhido = st.selectbox("Escolha seu prato:", df_meus['nome_alimento'].tolist())
            if st.button("Salvar Refeição Rápida", width="stretch"):
                prato_dados = df_meus[df_meus['nome_alimento'] == prato_escolhido].iloc[0]
                fator = float(peso_input) / prato_dados['porcao_g']
                salvar_no_banco(
                    refeicao_input, prato_escolhido, peso_input,
                    prato_dados['calorias'] * fator, prato_dados['carboidratos'] * fator,
                    prato_dados['proteinas'] * fator, prato_dados['gorduras'] * fator, 0
                )
                st.success(f"✅ {prato_escolhido} adicionado à dieta!")
                st.rerun()

# --- 5. O DASHBOARD VISUAL ---
df = carregar_dados()

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
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("🔥 Calorias", f"{df_dia['calorias'].sum():.0f} kcal")
        col2.metric("🍞 Carboidratos", f"{df_dia['carboidratos'].sum():.0f} g")
        col3.metric("🍗 Proteínas", f"{df_dia['proteinas'].sum():.0f} g")
        col4.metric("🥑 Gorduras", f"{df_dia['gorduras'].sum():.0f} g")
        
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
                    deletar_do_banco(id_para_deletar)
                    st.success("Apagado com sucesso!")
                    st.rerun()