import sqlite3

import pytest

import db


def test_restaurar_volta_os_dados_do_backup(banco_temporario):
    db.salvar_consumo('Almoço', 'Arroz', 100, {'calorias': 128})
    backup = db.exportar_banco()

    db.salvar_consumo('Jantar', 'Pizza', 300, {'calorias': 800})
    db.restaurar_banco(backup)

    assert db.carregar_historico()['nome_alimento'].tolist() == ['Arroz']
    # O banco de antes da restauração fica guardado por segurança
    assert banco_temporario.with_name('nutridata-antes-da-restauracao.db').exists()


@pytest.mark.parametrize('conteudo', [b'', b'texto qualquer', b'SQLite format 3\x00' + b'\x00' * 50])
def test_arquivo_invalido_nao_mexe_nos_dados(conteudo):
    db.salvar_consumo('Almoço', 'Arroz', 100, {'calorias': 128})
    with pytest.raises(db.BackupInvalido):
        db.restaurar_banco(conteudo)
    assert len(db.carregar_historico()) == 1


def test_banco_de_outro_programa_e_recusado():
    outro = sqlite3.connect(':memory:')
    outro.execute('CREATE TABLE clientes (nome TEXT)')
    with pytest.raises(db.BackupInvalido, match='NutriData'):
        db.restaurar_banco(outro.serialize())


def test_contagem_e_planilha_tem_todas_as_tabelas():
    db.salvar_consumo('Almoço', 'Arroz', 100, {'calorias': 128})
    assert db.contar_registros()['Refeições'] == 1
    assert set(db.exportar_tabelas()) == set(db.TABELAS_BACKUP.values())
