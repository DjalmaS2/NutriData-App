import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

import pandas as pd

# O banco fica ao lado deste arquivo, não importa de qual pasta o app é iniciado
CAMINHO_BANCO = Path(__file__).with_name('nutridata.db')


def conectar():
    return closing(sqlite3.connect(CAMINHO_BANCO))


def criar_tabelas():
    # Roda toda vez que o app inicia. O IF NOT EXISTS garante que nada é apagado.
    with conectar() as conexao:
        conexao.execute('''
            CREATE TABLE IF NOT EXISTS historico_consumo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_registro TEXT NOT NULL,
                refeicao TEXT NOT NULL,
                nome_alimento TEXT NOT NULL,
                porcao_g REAL,
                calorias REAL,
                carboidratos REAL,
                proteinas REAL,
                gorduras REAL,
                sodio REAL
            )
        ''')
        conexao.execute('''
            CREATE TABLE IF NOT EXISTS meus_alimentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_alimento TEXT NOT NULL,
                porcao_g REAL,
                calorias REAL,
                carboidratos REAL,
                proteinas REAL,
                gorduras REAL,
                sodio REAL DEFAULT 0
            )
        ''')
        # Bancos criados antes da coluna sodio existir ganham a coluna aqui
        colunas = [c[1] for c in conexao.execute("PRAGMA table_info(meus_alimentos)")]
        if 'sodio' not in colunas:
            conexao.execute("ALTER TABLE meus_alimentos ADD COLUMN sodio REAL DEFAULT 0")
        # Só existe uma linha (id = 1): o perfil de quem usa o app
        conexao.execute('''
            CREATE TABLE IF NOT EXISTS perfil (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                sexo TEXT NOT NULL,
                idade INTEGER NOT NULL,
                peso_kg REAL NOT NULL,
                altura_cm REAL NOT NULL,
                atividade TEXT NOT NULL,
                objetivo TEXT NOT NULL
            )
        ''')
        conexao.execute('''
            CREATE TABLE IF NOT EXISTS agua (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_registro TEXT NOT NULL,
                ml REAL NOT NULL
            )
        ''')
        # UNIQUE em data: no máximo uma pesagem por dia (a nova substitui a antiga)
        conexao.execute('''
            CREATE TABLE IF NOT EXISTS peso_corporal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT NOT NULL UNIQUE,
                peso_kg REAL NOT NULL
            )
        ''')
        conexao.commit()


def salvar_consumo(refeicao, nome, peso, calorias, carb, prot, gord, sodio):
    # O sódio é guardado em gramas, como vem da API
    data_atual = datetime.now().strftime('%Y-%m-%d %H:%M')
    with conectar() as conexao:
        conexao.execute('''
            INSERT INTO historico_consumo
            (data_registro, refeicao, nome_alimento, porcao_g, calorias, carboidratos, proteinas, gorduras, sodio)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (data_atual, refeicao, nome, peso, calorias, carb, prot, gord, sodio))
        conexao.commit()


def carregar_historico():
    with conectar() as conexao:
        df = pd.read_sql_query("SELECT * FROM historico_consumo", conexao)
    # Mesmo vazio, o DataFrame sai com a coluna data_apenas, para os filtros funcionarem
    df['data_registro'] = pd.to_datetime(df['data_registro'], format='mixed')
    df['data_apenas'] = df['data_registro'].dt.date
    return df


def atualizar_registro(id_registro, novo_peso, refeicao):
    # Todos os nutrientes são proporcionais ao peso, então basta multiplicar pelo fator
    with conectar() as conexao:
        (peso_antigo,) = conexao.execute(
            "SELECT porcao_g FROM historico_consumo WHERE id = ?", (id_registro,)).fetchone()
        fator = novo_peso / peso_antigo
        conexao.execute('''
            UPDATE historico_consumo
            SET porcao_g = ?, refeicao = ?, calorias = calorias * ?, carboidratos = carboidratos * ?,
                proteinas = proteinas * ?, gorduras = gorduras * ?, sodio = sodio * ?
            WHERE id = ?
        ''', (novo_peso, refeicao, fator, fator, fator, fator, fator, id_registro))
        conexao.commit()


def deletar_consumo(id_registro):
    with conectar() as conexao:
        conexao.execute("DELETE FROM historico_consumo WHERE id = ?", (id_registro,))
        conexao.commit()


def carregar_meus_alimentos():
    with conectar() as conexao:
        return pd.read_sql_query("SELECT * FROM meus_alimentos ORDER BY nome_alimento", conexao)


def salvar_prato(nome, porcao_g, calorias, carb, prot, gord, sodio):
    # Os valores são do prato inteiro; porcao_g é o peso total dele
    with conectar() as conexao:
        conexao.execute('''
            INSERT INTO meus_alimentos (nome_alimento, porcao_g, calorias, carboidratos, proteinas, gorduras, sodio)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (nome, porcao_g, calorias, carb, prot, gord, sodio))
        conexao.commit()


def deletar_prato(id_prato):
    with conectar() as conexao:
        conexao.execute("DELETE FROM meus_alimentos WHERE id = ?", (id_prato,))
        conexao.commit()


def salvar_perfil(sexo, idade, peso_kg, altura_cm, atividade, objetivo):
    # INSERT OR REPLACE: cria o perfil na primeira vez e atualiza nas próximas
    with conectar() as conexao:
        conexao.execute('''
            INSERT OR REPLACE INTO perfil (id, sexo, idade, peso_kg, altura_cm, atividade, objetivo)
            VALUES (1, ?, ?, ?, ?, ?, ?)
        ''', (sexo, idade, peso_kg, altura_cm, atividade, objetivo))
        conexao.commit()


def carregar_perfil():
    """Retorna o perfil como dict, ou None se ainda não foi preenchido."""
    with conectar() as conexao:
        conexao.row_factory = sqlite3.Row
        linha = conexao.execute("SELECT * FROM perfil WHERE id = 1").fetchone()
    return dict(linha) if linha else None


def registrar_agua(dia, ml):
    # Usa o dia escolhido com a hora atual, para permitir lançar água em dias anteriores
    data_registro = f"{dia:%Y-%m-%d} {datetime.now():%H:%M}"
    with conectar() as conexao:
        conexao.execute("INSERT INTO agua (data_registro, ml) VALUES (?, ?)", (data_registro, ml))
        conexao.commit()


def total_agua(dia):
    with conectar() as conexao:
        (total,) = conexao.execute(
            "SELECT COALESCE(SUM(ml), 0) FROM agua WHERE data_registro LIKE ?", (f"{dia:%Y-%m-%d}%",)
        ).fetchone()
    return total


def desfazer_agua(dia):
    """Apaga o último copo registrado no dia."""
    with conectar() as conexao:
        conexao.execute(
            "DELETE FROM agua WHERE id = "
            "(SELECT id FROM agua WHERE data_registro LIKE ? ORDER BY id DESC LIMIT 1)",
            (f"{dia:%Y-%m-%d}%",)
        )
        conexao.commit()


def registrar_peso(dia, peso_kg):
    data = f"{dia:%Y-%m-%d}"
    with conectar() as conexao:
        conexao.execute("INSERT OR REPLACE INTO peso_corporal (data, peso_kg) VALUES (?, ?)", (data, peso_kg))
        # Se for a pesagem mais recente, atualiza o perfil para a meta se ajustar sozinha
        (data_mais_recente,) = conexao.execute("SELECT MAX(data) FROM peso_corporal").fetchone()
        if data_mais_recente == data:
            conexao.execute("UPDATE perfil SET peso_kg = ? WHERE id = 1", (peso_kg,))
        conexao.commit()


def carregar_pesos():
    with conectar() as conexao:
        df = pd.read_sql_query("SELECT * FROM peso_corporal ORDER BY data", conexao)
    df['data'] = pd.to_datetime(df['data']).dt.date
    return df


def deletar_peso(id_peso):
    with conectar() as conexao:
        conexao.execute("DELETE FROM peso_corporal WHERE id = ?", (id_peso,))
        conexao.commit()
