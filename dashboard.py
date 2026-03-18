import streamlit as st
import sqlite3
import pandas as pd

# 1. Configuração inicial da página web
st.set_page_config(page_title="Meu NutriData", layout="wide")
st.title("🍏 Dashboard de Consumo Nutricional")
st.write("Acompanhe aqui o seu histórico de alimentação e macronutrientes.")

# 2. Função para ler o Banco de Dados e transformar em Tabela (DataFrame)
def carregar_dados():
    conexao = sqlite3.connect('nutridata.db')
    # Comando SQL para pegar todas as colunas da nossa tabela
    query = "SELECT data_registro, refeicao, nome_alimento, porcao_g, carboidratos, proteinas, gorduras FROM historico_consumo"
    
    # O Pandas transforma o resultado do SQL em uma tabela super inteligente
    df = pd.read_sql_query(query, conexao)
    conexao.close()
    return df

# Executa a função e guarda os dados na variável 'df'
df = carregar_dados()

# 3. Construindo a tela do Dashboard
if df.empty:
    # Se o banco estiver vazio, mostra um aviso amigável
    st.warning("Seu banco de dados ainda está vazio. Execute seu script da API para adicionar algumas refeições!")
else:
    # Dividindo a tela em duas colunas
    coluna1, coluna2 = st.columns(2)
    
    with coluna1:
        st.subheader("📚 Histórico Completo")
        # Mostra a tabela inteira na tela
        st.dataframe(df)
        
    with coluna2:
        st.subheader("📊 Consumo de Macronutrientes por Refeição")
        # Matemática rápida do Pandas: Agrupa por refeição e soma as proteínas/carbs/gorduras
        df_agrupado = df.groupby('refeicao')[['carboidratos', 'proteinas', 'gorduras']].sum()
        
        # Gera um gráfico de barras automático
        st.bar_chart(df_agrupado)