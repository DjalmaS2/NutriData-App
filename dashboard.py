import streamlit as st
from PIL import Image

# No Windows o pyzbar precisa do "Visual C++ Redistributable 2013" instalado.
# Se ele faltar, o app abre normalmente e só a aba da câmera fica desativada.
try:
    from pyzbar.pyzbar import decode
except (ImportError, OSError):
    decode = None

import api
import db
import taco
from comum import ICONES_REFEICOES, REFEICOES

# Este arquivo roda em toda página: configura o app, monta a barra lateral
# e no final abre a página escolhida (os arquivos ficam na pasta paginas/).

# --- 1. CONFIGURAÇÕES VISUAIS ---
st.set_page_config(page_title="NutriData", layout="wide", page_icon="imagens/icone.svg")
# Logo no topo da barra lateral (as cores e fontes do tema ficam em .streamlit/config.toml)
st.logo("imagens/logo.svg", size="large", icon_image="imagens/icone.svg")

# --- 2. BANCO DE DADOS ---
# Garante que as tabelas existem (essencial no primeiro acesso / no deploy)
db.criar_tabelas()

# --- 3. FUNÇÕES DO BACKEND (a lógica de API, banco e TACO fica em api.py, db.py e taco.py) ---
def salvar_produto(produto, peso, refeicao):
    """Calcula a porção e salva no histórico. Serve para a API e para a TACO."""
    db.salvar_consumo(refeicao, produto['nome'], peso, api.calcular_porcao(produto, peso))

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

# --- 4. PÁGINAS ---
# O menu de páginas aparece no topo da barra lateral
pagina = st.navigation([
    st.Page("paginas/dia.py", title="Dia", icon="📅", default=True),
    st.Page("paginas/historico.py", title="Histórico", icon="📈"),
    st.Page("paginas/pratos.py", title="Meus Pratos", icon="🍲"),
    st.Page("paginas/exercicios.py", title="Exercícios", icon="🏋️"),
    st.Page("paginas/perfil.py", title="Perfil", icon="👤"),
    st.Page("paginas/backup.py", title="Backup", icon="💾"),
])

# --- 5. BARRA LATERAL (Interface de Entrada, igual em todas as páginas) ---
with st.sidebar:
    st.header("Registrar alimento")
    st.caption("Escolha a refeição e o peso, depois busque o alimento numa das abas.")
    # A key permite que o botão "Adicionar" de cada refeição na página Dia escolha a refeição aqui
    refeicao_input = st.selectbox("Refeição:", REFEICOES, key="refeicao_sidebar",
                                  format_func=lambda r: f"{ICONES_REFEICOES[r]} {r}")
    peso_input = st.number_input("Peso consumido (g):", min_value=1.0, value=100.0, step=10.0)

    aba_taco, aba_scan, aba_api, aba_meus = st.tabs(["🥦 Alimentos", "📷 Câmera", "🔍 Digitar", "⭐ Meus Pratos"])

    with aba_taco:
        # Alimentos sem código de barras (arroz, feijão, frutas...) vêm da Tabela TACO
        termo = st.text_input("Buscar alimento (Tabela TACO):", placeholder="ex: arroz cozido, feijão, banana")
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
                if st.button("Salvar alimento", key="btn_taco", type="primary", width="stretch"):
                    salvar_produto(produto, float(peso_input), refeicao_input)
                    st.success(f"✅ {produto['nome']} salvo!")

    with aba_scan:
        if decode is None:
            st.warning("Leitor de código de barras indisponível neste computador (pyzbar não carregou).")
        # 1. Cria a memória do botão (começa desligado)
        if 'usar_camera' not in st.session_state:
            st.session_state.usar_camera = False

        # 2. O Botão que liga e desliga
        if st.button("📸 Ligar / desligar câmera", width="stretch"):
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
                    if st.button("Buscar e salvar", key="btn_scan", type="primary", width="stretch"):
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
        codigo_input = st.text_input("Código de barras:", placeholder="ex: 7891000100103")
        if st.button("Buscar e salvar", key="btn_api", type="primary", width="stretch"):
            sucesso, mensagem = registrar_alimento(codigo_input, float(peso_input), refeicao_input)
            if sucesso: st.success(f"✅ {mensagem} salvo!")
            else: st.error(f"❌ {mensagem}")

    with aba_meus:
        df_meus = db.carregar_meus_alimentos()
        if df_meus.empty:
            st.info("Você ainda não tem pratos.")
            st.page_link("paginas/pratos.py", label="Criar um prato", icon="🍲")
        else:
            id_prato = st.selectbox(
                "Escolha seu prato:", df_meus['id'].tolist(),
                format_func=lambda x: df_meus.loc[df_meus['id'] == x, 'nome_alimento'].values[0]
            )
            prato_dados = df_meus[df_meus['id'] == id_prato].iloc[0]
            st.caption(f"Prato inteiro: {prato_dados['porcao_g']:.0f} g · {prato_dados['calorias']:.0f} kcal")
            if st.button("Salvar refeição rápida", type="primary", width="stretch"):
                # Proporcional ao peso consumido em relação ao prato inteiro
                fator = float(peso_input) / prato_dados['porcao_g']
                db.salvar_consumo(refeicao_input, prato_dados['nome_alimento'], peso_input,
                                  {n: prato_dados[n] * fator for n in db.NUTRIENTES})
                st.success(f"✅ {prato_dados['nome_alimento']} adicionado à dieta!")

# --- 6. ABRE A PÁGINA ESCOLHIDA ---
# Roda depois da barra lateral, então um alimento recém-salvo já aparece na página
pagina.run()
