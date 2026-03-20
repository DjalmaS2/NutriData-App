import streamlit as st
import sqlite3
import pandas as pd
import requests
from datetime import datetime
import plotly.express as px

# --- 1. CONFIGURAÇÕES VISUAIS ---
st.set_page_config(page_title="NutriData Pro", layout="wide", page_icon="🍏")
st.title("🍏 NutriData - Dashboard Inteligente")

# --- 2. BANCO DE DADOS PRÉ-SALVOS (O Dicionário) ---
# Você pode adicionar quantos quiser aqui para nunca mais ter que digitar o código
ALIMENTOS_SALVOS = {
    "Nutella": "3017620422003",
    "Coca-Cola Lata": "7894900011517",
    "Aveia em Flocos Quaker": "7893000600125",
    "Digitar Novo Código...": "novo"
}

# --- 3. FUNÇÕES DO BACKEND ---
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
        
        # Matemática
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
    return df

# --- 4. BARRA LATERAL (Interface de Entrada) ---
with st.sidebar:
    st.header("🍽️ Adicionar Refeição")
    
    refeicao_input = st.selectbox("Refeição:", ["Café da Manhã", "Almoço", "Lanche", "Jantar"])
    
    # Menu Suspenso (Dropdown) que puxa do dicionário lá em cima
    opcao_alimento = st.selectbox("Escolha um alimento salvo:", list(ALIMENTOS_SALVOS.keys()))
    
    # Se o usuário escolher "Digitar Novo", abre uma caixa de texto. Se não, usa o código salvo.
    if opcao_alimento == "Digitar Novo Código...":
        codigo_input = st.text_input("Digite o Código de Barras:")
    else:
        codigo_input = ALIMENTOS_SALVOS[opcao_alimento]
        
    peso_input = st.number_input("Peso (g):", min_value=1.0, value=100.0, step=10.0)
    
    # Botão de Ação
    if st.button("Salvar no Banco", use_container_width=True):
        if codigo_input and codigo_input != "novo":
            sucesso, nome_registrado = registrar_alimento(codigo_input, float(peso_input), refeicao_input)
            if sucesso:
                st.success(f"✅ {nome_registrado} registrado!")
            else:
                st.error("❌ Produto não encontrado na API.")
        else:
            st.warning("⚠️ Informe um código válido.")

# --- 5. O DASHBOARD VISUAL ---
df = carregar_dados()

if df.empty:
    st.info("👈 Use o menu lateral esquerdo para adicionar sua primeira refeição!")
else:
    # 5.1 Cartões de Métricas Superiores
    st.subheader("📊 Resumo Nutricional Total")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🔥 Calorias", f"{df['calorias'].sum():.0f} kcal")
    col2.metric("🍞 Carboidratos", f"{df['carboidratos'].sum():.0f} g")
    col3.metric("🍗 Proteínas", f"{df['proteinas'].sum():.0f} g")
    col4.metric("🥑 Gorduras", f"{df['gorduras'].sum():.0f} g")
    
    st.divider()
    
    # 5.2 Gráficos Robustos com Plotly
    grafico1, grafico2 = st.columns(2)
    
    with grafico1:
        st.subheader("Proporção da Dieta")
        # Criando um gráfico de Rosca (Donut Chart) para os Macros
        df_macros = pd.DataFrame({
            'Nutriente': ['Carboidratos', 'Proteínas', 'Gorduras'],
            'Gramas': [df['carboidratos'].sum(), df['proteinas'].sum(), df['gorduras'].sum()]
        })
        fig_pie = px.pie(df_macros, values='Gramas', names='Nutriente', hole=0.5,
                         color_discrete_sequence=['#FF9999', '#66B2FF', '#99FF99'])
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with grafico2:
        st.subheader("Calorias por Refeição")
        # Gráfico de barras coloridas
        df_agrupado = df.groupby('refeicao')['calorias'].sum().reset_index()
        fig_bar = px.bar(df_agrupado, x='refeicao', y='calorias', color='refeicao')
        st.plotly_chart(fig_bar, use_container_width=True)