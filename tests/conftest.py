import pytest

import db


@pytest.fixture(autouse=True)
def banco_temporario(tmp_path, monkeypatch):
    """Todo teste usa um banco novo e vazio numa pasta temporária.

    autouse=True: vale para todos os testes sem precisar pedir, então
    nenhum teste mexe no nutridata.db de verdade.
    """
    monkeypatch.setattr(db, 'CAMINHO_BANCO', tmp_path / 'teste.db')
    db.criar_tabelas()
    return tmp_path / 'teste.db'
