import streamlit as st
import sqlite3
import pandas as pd
import requests
from datetime import datetime
import plotly.express as px

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

# --- 3. FUNÇÕES DO BACKEND ---
def salvar_no_banco(refeicao, nome, peso, calorias, carb, prot, gord, sodio):
    conexao = sqlite3.connect('nutridata.db')
    cursor = conexao.cursor()
    # Salvando Ano-Mês-Dia Hora:Minuto
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
    # --- MÁGICA DO PANDAS AQUI ---
    if not df.empty:
        # Transforma a coluna de texto em formato oficial de Data do Python
        df['data_registro'] = pd.to_datetime(df['data_registro'])
        # Cria uma nova coluna separando apenas o DIA (ignorando a hora) para o filtro
        df['data_apenas'] = df['data_registro'].dt.date 
    return df
#Exluir caso queria
def deletar_do_banco(id_registro):
    conexao = sqlite3.connect('nutridata.db')
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM historico_consumo WHERE id = ?", (id_registro,))
    conexao.commit()
    conexao.close()

# --- 4. BARRA LATERAL (Interface de Entrada) ---
with st.sidebar:
    st.header("🍽️ Adicionar Refeição")
    refeicao_input = st.selectbox("Refeição:", ["Café da Manhã", "Almoço", "Lanche", "Jantar"])
    opcao_alimento = st.selectbox("Escolha um alimento salvo:", list(ALIMENTOS_SALVOS.keys()))
    
    if opcao_alimento == "Digitar Novo Código...":
        codigo_input = st.text_input("Digite o Código de Barras:")
    else:
        codigo_input = ALIMENTOS_SALVOS[opcao_alimento]
        
    peso_input = st.number_input("Peso (g):", min_value=1.0, value=100.0, step=10.0)
    
    if st.button("Salvar no Banco", use_container_width=True):
        if codigo_input and codigo_input != "novo":
            sucesso, nome_registrado = registrar_alimento(codigo_input, float(peso_input), refeicao_input)
            if sucesso:
                st.success(f"✅ {nome_registrado} registrado!")
            else:
                st.error("❌ Produto não encontrado na API.")
        else:
            st.warning("⚠️ Informe um código válido.")

# --- 5. O DASHBOARD VISUAL (Agora com Filtros!) ---
df = carregar_dados()

if df.empty:
    st.info("👈 Use o menu lateral esquerdo para adicionar sua primeira refeição!")
else:
    # 5.1 Filtros Superiores
    st.subheader("📅 Controle Diário")
    col_calendario, col_meta = st.columns(2)
    
    with col_calendario:
        # Pega a data de hoje para o calendário já abrir no dia certo
        data_hoje = datetime.now().date()
        dia_selecionado = st.date_input("Filtrar por data:", data_hoje)
        
    with col_meta:
        # Define a meta calórica
        meta_calorias = st.number_input("Sua Meta Diária (kcal):", min_value=500, value=2000, step=100)

    # Aplica o filtro: cria uma tabela nova contendo SÓ o que foi comido no dia selecionado
    df_dia = df[df['data_apenas'] == dia_selecionado]

    if df_dia.empty:
        st.warning(f"Nenhuma refeição registrada para o dia {dia_selecionado.strftime('%d/%m/%Y')}.")
    else:
        # 5.2 Barra de Progresso Inteligente
        total_calorias_dia = df_dia['calorias'].sum()
        porcentagem = total_calorias_dia / meta_calorias
        
        st.markdown(f"**Progresso:** {total_calorias_dia:.0f} kcal consumidas de {meta_calorias} kcal.")
        
        # Limita a barra em 1.0 (100%) para o Streamlit não dar erro se você comer demais
        st.progress(min(porcentagem, 1.0))
        
        if porcentagem > 1.0:
            st.error("⚠️ Você ultrapassou a sua meta diária de calorias!")
        elif porcentagem >= 0.8:
            st.warning("Atenção: Você está perto de atingir sua meta!")
        else:
            st.success("Você está dentro da meta calórica!")
            
        st.divider()

        # 5.3 Cartões de Métricas (Agora usando apenas os dados do dia!)
        st.subheader(f"📊 Resumo do Dia ({dia_selecionado.strftime('%d/%m')})")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("🔥 Calorias", f"{df_dia['calorias'].sum():.0f} kcal")
        col2.metric("🍞 Carboidratos", f"{df_dia['carboidratos'].sum():.0f} g")
        col3.metric("🍗 Proteínas", f"{df_dia['proteinas'].sum():.0f} g")
        col4.metric("🥑 Gorduras", f"{df_dia['gorduras'].sum():.0f} g")
        
        st.divider()
        
        # 5.4 Gráficos (Atualizados para o dia)
        grafico1, grafico2 = st.columns(2)
        with grafico1:
            st.subheader("Proporção da Dieta")
            df_macros = pd.DataFrame({
                'Nutriente': ['Carboidratos', 'Proteínas', 'Gorduras'],
                'Gramas': [df_dia['carboidratos'].sum(), df_dia['proteinas'].sum(), df_dia['gorduras'].sum()]
            })
            # Só renderiza o gráfico de rosca se houver macronutrientes maiores que zero
            if df_macros['Gramas'].sum() > 0:
                fig_pie = px.pie(df_macros, values='Gramas', names='Nutriente', hole=0.5,
                                 color_discrete_sequence=['#FF9999', '#66B2FF', '#99FF99'])
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("Não há dados de macronutrientes suficientes para este gráfico.")
            
        with grafico2:
            st.subheader("Calorias por Refeição")
            df_agrupado = df_dia.groupby('refeicao')['calorias'].sum().reset_index()
            fig_bar = px.bar(df_agrupado, x='refeicao', y='calorias', color='refeicao')
            st.plotly_chart(fig_bar, use_container_width=True)
            # --- 5.5 Área de Gerenciamento (DELETAR) ---
        st.divider()
        st.subheader("🗑️ Gerenciar Registros do Dia")
        
        # Pega todos os IDs registrados no dia selecionado
        lista_ids = df_dia['id'].tolist()
        
        if len(lista_ids) > 0:
            col_select, col_botao = st.columns([3, 1])
            
            with col_select:
                # Cria a caixa de seleção mostrando o ID e o Nome do alimento
                id_para_deletar = st.selectbox(
                    "Selecione a refeição que deseja apagar:", 
                    options=lista_ids,
                    format_func=lambda x: f"ID {x} - {df_dia[df_dia['id'] == x]['nome_alimento'].values[0]} ({df_dia[df_dia['id'] == x]['porcao_g'].values[0]}g)"
                )
                
            with col_botao:
                st.write("") # Dá um pequeno espaço para alinhar com a caixa ao lado
                st.write("")
                # Se o botão for clicado, roda a função e reinicia a página
                if st.button("❌ Apagar Registro", use_container_width=True):
                    deletar_do_banco(id_para_deletar)
                    st.success("Apagado com sucesso!")
                    st.rerun() # Essa função do Streamlit atualiza a tela na hora!