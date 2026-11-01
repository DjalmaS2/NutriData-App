import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
from PIL import Image

# No Windows o pyzbar precisa do "Visual C++ Redistributable 2013" instalado.
# Se ele faltar, o app abre normalmente e só a aba da câmera fica desativada.
try:
    from pyzbar.pyzbar import decode
except (ImportError, OSError):
    decode = None

import api
import db
import metas
import taco

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

# --- 3. FUNÇÕES DO BACKEND (a lógica de API, banco e TACO fica em api.py, db.py e taco.py) ---
def salvar_produto(produto, peso, refeicao):
    """Calcula a porção e salva no histórico. Serve para a API e para a TACO."""
    porcao = api.calcular_porcao(produto, peso)
    db.salvar_consumo(
        refeicao, produto['nome'], peso, porcao['calorias'], porcao['carboidratos'],
        porcao['proteinas'], porcao['gorduras'], porcao['sodio']
    )

def registrar_alimento(codigo_barras, peso, refeicao):
    """Busca o produto e salva no histórico. Retorna (sucesso, mensagem)."""
    try:
        produto = api.buscar_produto(codigo_barras)
    except api.ErroAPI as erro:
        return False, str(erro)
    if produto is None:
        return False, "Produto não achado na API."

    salvar_produto(produto, peso, refeicao)
    return True, produto['nome']

def ler_codigo_da_imagem(imagem_camera):
    if decode is None:
        return None
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
    
    aba_taco, aba_scan, aba_api, aba_meus = st.tabs(["🥦 Alimentos", "📷 Câmera", "🔍 Digitar", "⭐ Meus Pratos"])

    with aba_taco:
        # Alimentos sem código de barras (arroz, feijão, frutas...) vêm da Tabela TACO
        termo = st.text_input("Buscar alimento:", placeholder="ex: arroz cozido, feijão, banana")
        if termo:
            resultados = taco.buscar(termo)
            if resultados.empty:
                st.warning("Nenhum alimento encontrado. Tente outra palavra.")
            else:
                id_escolhido = st.selectbox(
                    f"{len(resultados)} resultado(s):",
                    options=resultados['id'].tolist(),
                    format_func=lambda x: resultados.loc[resultados['id'] == x, 'nome'].values[0]
                )
                produto = taco.como_produto(resultados[resultados['id'] == id_escolhido].iloc[0])
                porcao = api.calcular_porcao(produto, peso_input)
                st.caption(
                    f"Em {peso_input:.0f} g: {porcao['calorias']:.0f} kcal · "
                    f"C {porcao['carboidratos']:.1f} g · P {porcao['proteinas']:.1f} g · "
                    f"G {porcao['gorduras']:.1f} g"
                )
                if st.button("Salvar Alimento", key="btn_taco", width="stretch"):
                    salvar_produto(produto, float(peso_input), refeicao_input)
                    st.success(f"✅ {produto['nome']} salvo!")

    with aba_scan:
        if decode is None:
            st.warning("Leitor de código de barras indisponível neste computador (pyzbar não carregou).")
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
            st.info("Você ainda não tem pratos. Crie um na seção **🍲 Meus Pratos**.")
        else:
            id_prato = st.selectbox(
                "Escolha seu prato:", df_meus['id'].tolist(),
                format_func=lambda x: df_meus.loc[df_meus['id'] == x, 'nome_alimento'].values[0]
            )
            prato_dados = df_meus[df_meus['id'] == id_prato].iloc[0]
            st.caption(f"Prato inteiro: {prato_dados['porcao_g']:.0f} g · {prato_dados['calorias']:.0f} kcal")
            if st.button("Salvar Refeição Rápida", width="stretch"):
                # Proporcional ao peso consumido em relação ao prato inteiro
                fator = float(peso_input) / prato_dados['porcao_g']
                db.salvar_consumo(
                    refeicao_input, prato_dados['nome_alimento'], peso_input,
                    prato_dados['calorias'] * fator, prato_dados['carboidratos'] * fator,
                    prato_dados['proteinas'] * fator, prato_dados['gorduras'] * fator,
                    prato_dados['sodio'] * fator
                )
                st.success(f"✅ {prato_dados['nome_alimento']} adicionado à dieta!")

    st.divider()
    perfil = db.carregar_perfil()
    # O perfil fica aberto enquanto não foi preenchido, para chamar a atenção
    with st.expander("👤 Meu Perfil", expanded=perfil is None):
        atual = perfil or {}
        opcoes_atividade = list(metas.FATORES_ATIVIDADE)
        opcoes_objetivo = list(metas.AJUSTE_OBJETIVO)
        with st.form("form_perfil"):
            sexo = st.radio("Sexo:", ["Feminino", "Masculino"], horizontal=True,
                            index=["Feminino", "Masculino"].index(atual.get('sexo', "Feminino")))
            idade = st.number_input("Idade:", min_value=14, max_value=100, value=atual.get('idade', 30))
            peso = st.number_input("Peso (kg):", min_value=30.0, max_value=300.0,
                                   value=float(atual.get('peso_kg', 70.0)), step=0.5)
            altura = st.number_input("Altura (cm):", min_value=100.0, max_value=230.0,
                                     value=float(atual.get('altura_cm', 170.0)), step=1.0)
            atividade = st.selectbox("Nível de atividade:", opcoes_atividade,
                                     index=opcoes_atividade.index(atual.get('atividade', opcoes_atividade[0])))
            objetivo = st.selectbox("Objetivo:", opcoes_objetivo,
                                    index=opcoes_objetivo.index(atual.get('objetivo', "Manter peso")))
            if st.form_submit_button("Salvar Perfil", width="stretch"):
                db.salvar_perfil(sexo, idade, peso, altura, atividade, objetivo)
                st.rerun()

# --- 5. O DASHBOARD VISUAL ---
def mostrar_dia(df, meta_calorias):
    data_hoje = datetime.now().date()
    dia_selecionado = st.date_input("Filtrar por data:", data_hoje)
    df_dia = df[df['data_apenas'] == dia_selecionado]

    if df_dia.empty:
        st.warning(f"Nenhuma refeição registrada para o dia {dia_selecionado.strftime('%d/%m/%Y')}.")
        return

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

    col_select, col_botao = st.columns([3, 1])
    with col_select:
        id_para_deletar = st.selectbox(
            "Selecione a refeição que deseja apagar:",
            options=df_dia['id'].tolist(),
            format_func=lambda x: f"ID {x} - {df_dia[df_dia['id'] == x]['nome_alimento'].values[0]} ({df_dia[df_dia['id'] == x]['porcao_g'].values[0]}g)"
        )
    with col_botao:
        st.write("")
        st.write("")
        if st.button("❌ Apagar Registro", width="stretch"):
            db.deletar_consumo(id_para_deletar)
            st.success("Apagado com sucesso!")
            st.rerun()


def mostrar_historico(df, meta_calorias):
    dias = st.radio("Período:", [7, 30, 90], horizontal=True, format_func=lambda d: f"Últimos {d} dias")

    # Um valor por dia; dias sem registro entram com 0 para o gráfico não "pular" datas
    colunas = ['calorias', 'carboidratos', 'proteinas', 'gorduras']
    periodo = pd.date_range(end=datetime.now().date(), periods=dias).date
    por_dia = df.groupby('data_apenas')[colunas].sum().reindex(periodo, fill_value=0)
    por_dia.index.name = 'Dia'

    registrados = por_dia[por_dia['calorias'] > 0]
    if registrados.empty:
        st.info(f"Nenhuma refeição registrada nos últimos {dias} dias.")
        return

    # A média considera só os dias com registro, para dias esquecidos não puxarem para baixo
    col1, col2, col3 = st.columns(3)
    col1.metric("📊 Média diária", f"{registrados['calorias'].mean():.0f} kcal")
    col2.metric("📝 Dias registrados", f"{len(registrados)} de {dias}")
    col3.metric("🎯 Dias dentro da meta", f"{(registrados['calorias'] <= meta_calorias).sum()}")

    st.subheader("Calorias por Dia")
    df_grafico = por_dia.reset_index()
    df_grafico['Situação'] = df_grafico['calorias'].map(
        lambda c: 'Acima da meta' if c > meta_calorias else 'Dentro da meta')
    fig = px.bar(df_grafico, x='Dia', y='calorias', color='Situação',
                 color_discrete_map={'Dentro da meta': '#66B2FF', 'Acima da meta': '#FF9999'},
                 labels={'calorias': 'kcal'})
    fig.add_hline(y=meta_calorias, line_dash='dash', annotation_text=f"Meta: {meta_calorias} kcal")
    st.plotly_chart(fig, width="stretch")

    st.subheader("Macronutrientes por Dia (g)")
    df_macros = df_grafico.melt(id_vars='Dia', value_vars=['carboidratos', 'proteinas', 'gorduras'],
                                var_name='Nutriente', value_name='Gramas')
    df_macros['Nutriente'] = df_macros['Nutriente'].str.capitalize()
    fig_macros = px.bar(df_macros, x='Dia', y='Gramas', color='Nutriente',
                        color_discrete_sequence=['#FF9999', '#66B2FF', '#99FF99'])
    st.plotly_chart(fig_macros, width="stretch")


def mostrar_pratos():
    st.subheader("🍲 Montar um Prato")
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
    if not ingredientes.empty:
        tabela = ingredientes.assign(sodio=ingredientes['sodio'] * 1000).rename(columns={
            'calorias': 'kcal', 'carboidratos': 'Carb (g)', 'proteinas': 'Prot (g)',
            'gorduras': 'Gord (g)', 'sodio': 'Sódio (mg)'})
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
                db.salvar_prato(nome_prato.strip(), peso_final, ingredientes['calorias'].sum(),
                                ingredientes['carboidratos'].sum(), ingredientes['proteinas'].sum(),
                                ingredientes['gorduras'].sum(), ingredientes['sodio'].sum())
                st.session_state.ingredientes = []
                st.rerun()

        if st.button("🧹 Limpar ingredientes"):
            st.session_state.ingredientes = []
            st.rerun()

    st.divider()
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


# Meta calculada pelo perfil; sem perfil, usa 2000 kcal como padrão
calculo_meta = metas.calcular_meta(perfil) if perfil else None
meta_sugerida = round(calculo_meta['meta']) if calculo_meta else 2000

df = db.carregar_historico()

col_secao, col_meta = st.columns([2, 1])
with col_secao:
    # Um radio (e não st.tabs) para a seção escolhida continuar aberta quando a página recarrega
    secao = st.radio("Seção:", ["📅 Dia", "📈 Histórico", "🍲 Meus Pratos"], horizontal=True, key="secao")
with col_meta:
    meta_calorias = st.number_input("Sua Meta Diária (kcal):", min_value=500, value=meta_sugerida, step=50)
    if calculo_meta:
        st.caption(
            f"Calculada pelo seu perfil: metabolismo basal {calculo_meta['tmb']:.0f} kcal · "
            f"gasto diário {calculo_meta['gasto']:.0f} kcal · objetivo: {perfil['objetivo'].lower()}."
        )
    else:
        st.caption("Preencha **👤 Meu Perfil** na barra lateral para calcular a sua meta.")

st.divider()

if secao == "🍲 Meus Pratos":
    mostrar_pratos()
elif df.empty:
    st.info("👈 Use o menu lateral esquerdo para adicionar sua primeira refeição!")
elif secao == "📈 Histórico":
    mostrar_historico(df, meta_calorias)
else:
    mostrar_dia(df, meta_calorias)
