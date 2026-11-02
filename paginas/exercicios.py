from datetime import datetime, timedelta

import plotly.express as px
import streamlit as st

import db
import exercicios

PESO_PADRAO = 70.0


def avisar(mensagem, icone):
    # A mensagem fica guardada e aparece depois que a página recarrega
    st.session_state.aviso_exercicio = (mensagem, icone)


def mostrar_aviso():
    if 'aviso_exercicio' in st.session_state:
        mensagem, icone = st.session_state.pop('aviso_exercicio')
        st.toast(mensagem, icon=icone)


def mostrar_musculacao(dia):
    series = db.carregar_series()

    col_grupo, col_exercicio = st.columns(2)
    grupo = col_grupo.selectbox("Grupo muscular:", list(exercicios.BIBLIOTECA))
    exercicio = col_exercicio.selectbox("Exercício:", exercicios.BIBLIOTECA[grupo])

    # Como no Hevy: mostra o último treino e o recorde do exercício, para saber quanto colocar
    anteriores = series[(series['exercicio'] == exercicio) & (series['data'] < dia)]
    cargas = series.loc[series['exercicio'] == exercicio, 'carga_kg']
    recorde = cargas.max() if not cargas.empty else None
    if not anteriores.empty:
        ultimo_dia = anteriores['data'].max()
        ultimas = anteriores[anteriores['data'] == ultimo_dia]
        resumo = " · ".join(f"{s.repeticoes}×{s.carga_kg:g} kg" for s in ultimas.itertuples())
        st.caption(f"🕘 Último treino ({ultimo_dia:%d/%m}): {resumo}  \n🏆 Recorde: {recorde:g} kg")
        reps_padrao, carga_padrao = int(ultimas['repeticoes'].iloc[-1]), float(ultimas['carga_kg'].iloc[-1])
    else:
        st.caption("Primeira vez com este exercício. Comece leve!")
        reps_padrao, carga_padrao = 10, 0.0

    col_reps, col_carga, col_botao = st.columns([2, 2, 2], vertical_alignment="bottom")
    # A key inclui o exercício para os valores sugeridos mudarem ao trocar de exercício
    repeticoes = col_reps.number_input("Repetições:", min_value=1, max_value=100, value=reps_padrao,
                                       key=f"reps_{exercicio}")
    carga = col_carga.number_input("Carga (kg):", min_value=0.0, max_value=500.0, value=carga_padrao,
                                   step=2.5, key=f"carga_{exercicio}",
                                   help="Use 0 para exercícios só com o peso do corpo.")
    if col_botao.button("➕ Adicionar série", width="stretch"):
        db.registrar_serie(dia, exercicio, grupo, repeticoes, carga)
        if recorde is not None and carga > recorde:
            avisar(f"Novo recorde em {exercicio}: {carga:g} kg!", "🏆")
        else:
            avisar(f"Série registrada: {repeticoes}×{carga:g} kg", "✅")
        st.rerun()

    do_dia = series[series['data'] == dia]
    if do_dia.empty:
        st.info("Nenhuma série registrada neste dia.")
        return

    volume = (do_dia['repeticoes'] * do_dia['carga_kg']).sum()
    texto_series = "1 série" if len(do_dia) == 1 else f"{len(do_dia)} séries"
    st.markdown(f"**Treino do dia:** {texto_series} · volume {volume:,.0f} kg".replace(",", "."))
    for nome_exercicio, grupo_series in do_dia.groupby('exercicio', sort=False):
        with st.container(border=True):
            st.markdown(f"**{nome_exercicio}**")
            for numero, serie in enumerate(grupo_series.itertuples(), start=1):
                col_texto, col_apagar = st.columns([6, 1], vertical_alignment="center")
                col_texto.markdown(f"Série {numero}: {serie.repeticoes} × {serie.carga_kg:g} kg")
                if col_apagar.button("🗑️", key=f"apagar_serie_{serie.id}", help="Apagar série"):
                    db.deletar_serie(serie.id)
                    st.rerun()
    st.caption("Lembre de registrar o tempo do treino em **🏃 Atividades** para contar as calorias gastas.")


def mostrar_atividades(dia, perfil):
    peso = perfil['peso_kg'] if perfil else PESO_PADRAO
    col_atividade, col_minutos = st.columns([3, 1])
    atividade = col_atividade.selectbox("Atividade:", list(exercicios.ATIVIDADES_MET))
    minutos = col_minutos.number_input("Minutos:", min_value=1, max_value=600, value=45)
    kcal = exercicios.calcular_kcal(atividade, minutos, peso)

    col_info, col_botao = st.columns([3, 1], vertical_alignment="center")
    col_info.caption(f"Estimativa: **{kcal:.0f} kcal** para {peso:g} kg"
                     + ("" if perfil else " (peso padrão; preencha o Perfil para ficar mais preciso)"))
    if col_botao.button("💾 Registrar", width="stretch"):
        db.registrar_atividade(dia, atividade, minutos, kcal)
        avisar(f"{atividade}: {kcal:.0f} kcal registradas", "🔥")
        st.rerun()

    atividades = db.carregar_atividades()
    do_dia = atividades[atividades['data'] == dia]
    if do_dia.empty:
        st.info("Nenhuma atividade registrada neste dia.")
        return

    st.markdown(f"**Gasto do dia:** {do_dia['kcal'].sum():.0f} kcal em {do_dia['minutos'].sum():.0f} min")
    for item in do_dia.itertuples():
        col_texto, col_apagar = st.columns([6, 1], vertical_alignment="center")
        col_texto.markdown(f"{item.atividade} · {item.minutos:.0f} min · {item.kcal:.0f} kcal")
        if col_apagar.button("🗑️", key=f"apagar_atividade_{item.id}", help="Apagar atividade"):
            db.deletar_atividade(item.id)
            st.rerun()


def mostrar_evolucao():
    series = db.carregar_series()
    if series.empty:
        st.info("Registre algumas séries para ver a sua evolução.")
        return

    exercicio = st.selectbox("Exercício:", sorted(series['exercicio'].unique()), key="evolucao_exercicio")
    do_exercicio = series[series['exercicio'] == exercicio]
    # Por dia: a maior carga e o volume (repetições x carga somados)
    por_dia = (do_exercicio.assign(volume=do_exercicio['repeticoes'] * do_exercicio['carga_kg'])
               .groupby('data').agg(carga_maxima=('carga_kg', 'max'), volume=('volume', 'sum')).reset_index())
    c1, c2 = st.columns(2)
    c1.metric("🏆 Recorde", f"{por_dia['carga_maxima'].max():g} kg")
    c2.metric("📅 Treinos com este exercício", len(por_dia))
    fig = px.line(por_dia, x='data', y='carga_maxima', markers=True,
                  labels={'data': 'Dia', 'carga_maxima': 'Maior carga (kg)'})
    st.plotly_chart(fig, width="stretch")

    st.subheader("Séries por grupo muscular (últimos 7 dias)")
    semana = series[series['data'] > datetime.now().date() - timedelta(days=7)]
    if semana.empty:
        st.caption("Nenhuma série nos últimos 7 dias.")
    else:
        contagem = semana.groupby('grupo').size().reset_index(name='Séries')
        fig_grupos = px.bar(contagem, x='grupo', y='Séries', labels={'grupo': 'Grupo muscular'})
        st.plotly_chart(fig_grupos, width="stretch")


st.title("🏋️ Exercícios")
mostrar_aviso()
perfil = db.carregar_perfil()

# Dias com treino: série de musculação ou atividade registrada
hoje = datetime.now().date()
dias_treino = set(db.carregar_series()['data']) | set(db.carregar_atividades()['data'])
treinos_semana = sum(1 for d in dias_treino if hoje - timedelta(days=6) <= d <= hoje)

col_data, col_semana = st.columns(2)
dia = col_data.date_input("Dia do treino:", hoje)
col_semana.metric("📆 Dias com treino nos últimos 7 dias", treinos_semana)

secao = st.radio("Seção:", ["🏋️ Musculação", "🏃 Atividades", "📈 Evolução"], horizontal=True,
                 key="secao_exercicios", label_visibility="collapsed")
st.divider()
if secao == "🏋️ Musculação":
    mostrar_musculacao(dia)
elif secao == "🏃 Atividades":
    mostrar_atividades(dia, perfil)
else:
    mostrar_evolucao()
