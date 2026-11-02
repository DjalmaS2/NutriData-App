from datetime import datetime
from io import BytesIO

import pandas as pd
import streamlit as st

import db


def planilha_excel():
    """Uma aba por tabela, para abrir no Excel ou no Google Planilhas."""
    arquivo = BytesIO()
    with pd.ExcelWriter(arquivo, engine='openpyxl') as planilha:
        for nome, tabela in db.exportar_tabelas().items():
            tabela.to_excel(planilha, sheet_name=nome, index=False)
    return arquivo.getvalue()


st.title("Backup dos dados")
st.info(
    "Os seus dados ficam num arquivo dentro do servidor do app. No Streamlit Cloud esse arquivo "
    "é apagado quando o servidor reinicia, então **baixe um backup de vez em quando** e "
    "restaure quando precisar."
)

# Restauração feita na execução anterior: mostra a mensagem depois de recarregar
if 'aviso_backup' in st.session_state:
    st.success(st.session_state.pop('aviso_backup'))

contagem = db.contar_registros()
colunas = st.columns(len(contagem))
for coluna, (nome, total) in zip(colunas, contagem.items()):
    coluna.metric(nome, total)

hoje = datetime.now().strftime('%Y-%m-%d')
st.divider()

st.subheader("Baixar")
col_backup, col_planilha = st.columns(2)
with col_backup:
    st.markdown("**Backup completo**")
    st.caption("Um arquivo .db com tudo. É ele que você usa para restaurar depois.")
    st.download_button("💾 Baixar backup", type="primary", data=db.exportar_banco(), file_name=f"nutridata-backup-{hoje}.db",
                       mime="application/x-sqlite3", width="stretch")
with col_planilha:
    st.markdown("**Planilha (Excel)**")
    st.caption("Para ver ou analisar os dados no Excel ou no Google Planilhas. Não serve para restaurar.")
    st.download_button("📊 Baixar planilha", data=planilha_excel(), file_name=f"nutridata-{hoje}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       width="stretch")

st.divider()

st.subheader("Restaurar")
st.caption("Envie um arquivo de backup (.db) baixado nesta página. "
           "**Os dados atuais serão substituídos pelos do backup.**")
# Trocar a key limpa o campo de upload depois de uma restauração
if 'chave_upload' not in st.session_state:
    st.session_state.chave_upload = 0
arquivo = st.file_uploader("Arquivo de backup:", type=["db"], key=f"upload_{st.session_state.chave_upload}")
if arquivo is not None:
    confirmado = st.checkbox("Entendo que os dados atuais serão substituídos pelos do backup.")
    if st.button("♻️ Restaurar backup", type="primary", disabled=not confirmado):
        try:
            db.restaurar_banco(arquivo.getvalue())
        except db.BackupInvalido as erro:
            st.error(f"❌ {erro}")
        else:
            st.session_state.aviso_backup = f"✅ Backup '{arquivo.name}' restaurado com sucesso!"
            st.session_state.chave_upload += 1
            st.rerun()
