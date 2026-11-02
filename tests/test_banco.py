import sqlite3
from datetime import date

import pytest

import db

HOJE = date(2026, 11, 2)


def test_salvar_e_carregar_refeicao():
    db.salvar_consumo('Almoço', 'Arroz', 150, {'calorias': 192, 'carboidratos': 42})
    historico = db.carregar_historico()
    assert len(historico) == 1
    registro = historico.iloc[0]
    assert registro['nome_alimento'] == 'Arroz'
    assert registro['calorias'] == 192
    assert registro['ferro'] == 0  # nutriente não informado entra como 0


def test_editar_peso_recalcula_todos_os_nutrientes():
    db.salvar_consumo('Almoço', 'Feijão', 100, {'calorias': 76, 'fibras': 8.5, 'sodio': 0.002})
    id_registro = int(db.carregar_historico().iloc[0]['id'])
    db.atualizar_registro(id_registro, 200, 'Jantar')
    registro = db.carregar_historico().iloc[0]
    assert registro['porcao_g'] == 200
    assert registro['refeicao'] == 'Jantar'
    assert registro['calorias'] == pytest.approx(152)
    assert registro['fibras'] == pytest.approx(17)
    assert registro['sodio'] == pytest.approx(0.004)


def test_historico_vazio_tem_coluna_de_data():
    assert 'data_apenas' in db.carregar_historico().columns


def test_agua_soma_e_desfaz():
    db.registrar_agua(HOJE, 250)
    db.registrar_agua(HOJE, 500)
    assert db.total_agua(HOJE) == 750
    db.desfazer_agua(HOJE)
    assert db.total_agua(HOJE) == 250


def test_pesagem_recente_atualiza_o_perfil():
    db.salvar_perfil('Masculino', 30, 82, 180, 'Moderado (exercício 3-5x por semana)', 'Perder peso')
    db.registrar_peso(date(2026, 10, 25), 81.2)
    db.registrar_peso(HOJE, 80.4)
    assert db.carregar_perfil()['peso_kg'] == 80.4
    # Uma pesagem antiga, lançada depois, não muda o peso atual do perfil
    db.registrar_peso(date(2026, 10, 1), 85)
    assert db.carregar_perfil()['peso_kg'] == 80.4


def test_uma_pesagem_por_dia():
    db.registrar_peso(HOJE, 80)
    db.registrar_peso(HOJE, 79.5)
    pesos = db.carregar_pesos()
    assert pesos['peso_kg'].tolist() == [79.5]


def test_calorias_de_exercicio_do_dia():
    db.registrar_atividade(HOJE, 'Corrida (10 km/h)', 30, 392)
    db.registrar_atividade(HOJE, 'Caminhada (5 km/h)', 20, 93)
    db.registrar_atividade(date(2026, 11, 1), 'Yoga', 60, 200)
    assert db.kcal_exercicio(HOJE) == 485


def test_prato_guarda_todos_os_nutrientes():
    db.salvar_prato('Marmita', 250, {'calorias': 383, 'vitamina_c': 10})
    prato = db.carregar_meus_alimentos().iloc[0]
    assert prato['porcao_g'] == 250
    assert prato['vitamina_c'] == 10


def test_banco_antigo_ganha_colunas_novas(banco_temporario):
    # Simula um banco da primeira versão do app, sem os micronutrientes
    banco_temporario.unlink()
    conexao = sqlite3.connect(banco_temporario)
    conexao.execute('''CREATE TABLE historico_consumo (id INTEGER PRIMARY KEY, data_registro TEXT,
        refeicao TEXT, nome_alimento TEXT, porcao_g REAL, calorias REAL, carboidratos REAL,
        proteinas REAL, gorduras REAL, sodio REAL)''')
    conexao.execute("INSERT INTO historico_consumo VALUES (1, '2026-03-20 10:53', '1', 'Nutella', 10, 54, 6, 1, 3, 0)")
    conexao.commit()
    conexao.close()

    db.criar_tabelas()

    registro = db.carregar_historico().iloc[0]
    assert registro['nome_alimento'] == 'Nutella'   # dados antigos preservados
    assert registro['fibras'] == 0                    # coluna nova criada
