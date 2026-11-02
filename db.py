import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

import pandas as pd

# O banco fica ao lado deste arquivo, não importa de qual pasta o app é iniciado
CAMINHO_BANCO = Path(__file__).with_name('nutridata.db')

# Colunas de nutrientes do histórico e dos pratos, com a unidade de cada uma.
# O sódio fica em gramas (como vem da API); os minerais e a vitamina C, em mg.
NUTRIENTES = {
    'calorias': 'kcal',
    'carboidratos': 'g',
    'proteinas': 'g',
    'gorduras': 'g',
    'sodio': 'g',
    'fibras': 'g',
    'calcio': 'mg',
    'ferro': 'mg',
    'vitamina_c': 'mg',
    'potassio': 'mg',
}
# Nutrientes que entraram depois; bancos antigos ganham essas colunas em criar_tabelas
NUTRIENTES_NOVOS = ['fibras', 'calcio', 'ferro', 'vitamina_c', 'potassio']


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
        # Bancos criados antes de cada coluna existir ganham a coluna aqui (com valor 0)
        for tabela, novas in [('meus_alimentos', ['sodio'] + NUTRIENTES_NOVOS),
                              ('historico_consumo', NUTRIENTES_NOVOS)]:
            colunas = [c[1] for c in conexao.execute(f"PRAGMA table_info({tabela})")]
            for coluna in novas:
                if coluna not in colunas:
                    conexao.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} REAL DEFAULT 0")
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
        # Somar ou não as calorias dos exercícios à meta do dia (0 = não, 1 = sim)
        colunas_perfil = [c[1] for c in conexao.execute("PRAGMA table_info(perfil)")]
        if 'somar_exercicio' not in colunas_perfil:
            conexao.execute("ALTER TABLE perfil ADD COLUMN somar_exercicio INTEGER DEFAULT 0")
        # Meta de peso em kg (vazia = sem meta)
        if 'peso_meta' not in colunas_perfil:
            conexao.execute("ALTER TABLE perfil ADD COLUMN peso_meta REAL")
        # Atividades com duração e calorias gastas (cardio, musculação...)
        conexao.execute('''
            CREATE TABLE IF NOT EXISTS atividades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT NOT NULL,
                atividade TEXT NOT NULL,
                minutos REAL NOT NULL,
                kcal REAL NOT NULL
            )
        ''')
        # Cada série de musculação: exercício, repetições e carga
        conexao.execute('''
            CREATE TABLE IF NOT EXISTS series (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT NOT NULL,
                exercicio TEXT NOT NULL,
                grupo TEXT NOT NULL,
                repeticoes INTEGER NOT NULL,
                carga_kg REAL NOT NULL
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


def _inserir(conexao, tabela, campos, nutrientes):
    """INSERT com os campos fixos + uma coluna por nutriente (os que faltarem entram como 0)."""
    valores = {**campos, **{n: float(nutrientes.get(n, 0)) for n in NUTRIENTES}}
    colunas = ', '.join(valores)
    marcadores = ', '.join('?' * len(valores))
    conexao.execute(f"INSERT INTO {tabela} ({colunas}) VALUES ({marcadores})", tuple(valores.values()))


def salvar_consumo(refeicao, nome, peso, nutrientes):
    """nutrientes: dict com as chaves de NUTRIENTES, já calculados para o peso consumido."""
    data_atual = datetime.now().strftime('%Y-%m-%d %H:%M')
    with conectar() as conexao:
        _inserir(conexao, 'historico_consumo',
                 {'data_registro': data_atual, 'refeicao': refeicao, 'nome_alimento': nome, 'porcao_g': peso},
                 nutrientes)
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
        multiplicar = ', '.join(f"{n} = {n} * ?" for n in NUTRIENTES)
        conexao.execute(
            f"UPDATE historico_consumo SET porcao_g = ?, refeicao = ?, {multiplicar} WHERE id = ?",
            (novo_peso, refeicao, *[fator] * len(NUTRIENTES), id_registro)
        )
        conexao.commit()


def deletar_consumo(id_registro):
    with conectar() as conexao:
        conexao.execute("DELETE FROM historico_consumo WHERE id = ?", (id_registro,))
        conexao.commit()


def carregar_meus_alimentos():
    with conectar() as conexao:
        return pd.read_sql_query("SELECT * FROM meus_alimentos ORDER BY nome_alimento", conexao)


def salvar_prato(nome, porcao_g, nutrientes):
    # Os valores são do prato inteiro; porcao_g é o peso total dele
    with conectar() as conexao:
        _inserir(conexao, 'meus_alimentos', {'nome_alimento': nome, 'porcao_g': porcao_g}, nutrientes)
        conexao.commit()


def deletar_prato(id_prato):
    with conectar() as conexao:
        conexao.execute("DELETE FROM meus_alimentos WHERE id = ?", (id_prato,))
        conexao.commit()


def salvar_perfil(sexo, idade, peso_kg, altura_cm, atividade, objetivo, somar_exercicio=False, peso_meta=None):
    # INSERT OR REPLACE: cria o perfil na primeira vez e atualiza nas próximas
    with conectar() as conexao:
        conexao.execute('''
            INSERT OR REPLACE INTO perfil
            (id, sexo, idade, peso_kg, altura_cm, atividade, objetivo, somar_exercicio, peso_meta)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (sexo, idade, peso_kg, altura_cm, atividade, objetivo, int(somar_exercicio), peso_meta))
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


def registrar_atividade(dia, atividade, minutos, kcal):
    with conectar() as conexao:
        conexao.execute("INSERT INTO atividades (data, atividade, minutos, kcal) VALUES (?, ?, ?, ?)",
                        (f"{dia:%Y-%m-%d}", atividade, minutos, kcal))
        conexao.commit()


def carregar_atividades():
    with conectar() as conexao:
        df = pd.read_sql_query("SELECT * FROM atividades ORDER BY data, id", conexao)
    df['data'] = pd.to_datetime(df['data']).dt.date
    return df


def deletar_atividade(id_atividade):
    with conectar() as conexao:
        conexao.execute("DELETE FROM atividades WHERE id = ?", (id_atividade,))
        conexao.commit()


def kcal_exercicio(dia):
    """Total de calorias gastas em atividades no dia."""
    with conectar() as conexao:
        (total,) = conexao.execute(
            "SELECT COALESCE(SUM(kcal), 0) FROM atividades WHERE data = ?", (f"{dia:%Y-%m-%d}",)
        ).fetchone()
    return total


def registrar_serie(dia, exercicio, grupo, repeticoes, carga_kg):
    with conectar() as conexao:
        conexao.execute(
            "INSERT INTO series (data, exercicio, grupo, repeticoes, carga_kg) VALUES (?, ?, ?, ?, ?)",
            (f"{dia:%Y-%m-%d}", exercicio, grupo, repeticoes, carga_kg)
        )
        conexao.commit()


def carregar_series():
    with conectar() as conexao:
        df = pd.read_sql_query("SELECT * FROM series ORDER BY data, id", conexao)
    df['data'] = pd.to_datetime(df['data']).dt.date
    return df


def deletar_serie(id_serie):
    with conectar() as conexao:
        conexao.execute("DELETE FROM series WHERE id = ?", (id_serie,))
        conexao.commit()


# --- BACKUP ---
# Tabelas com dados do usuário, na ordem em que aparecem na planilha exportada
TABELAS_BACKUP = {
    'historico_consumo': 'Refeições',
    'meus_alimentos': 'Pratos',
    'perfil': 'Perfil',
    'peso_corporal': 'Peso',
    'agua': 'Água',
    'atividades': 'Atividades',
    'series': 'Séries',
}


def exportar_banco():
    """Retorna o banco inteiro como bytes (um arquivo .db pronto para baixar)."""
    with conectar() as conexao:
        return conexao.serialize()


def contar_registros():
    with conectar() as conexao:
        return {nome: conexao.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
                for tabela, nome in TABELAS_BACKUP.items()}


def exportar_tabelas():
    """Cada tabela como DataFrame, com o nome em português (para a planilha)."""
    with conectar() as conexao:
        return {nome: pd.read_sql_query(f"SELECT * FROM {tabela}", conexao)
                for tabela, nome in TABELAS_BACKUP.items()}


class BackupInvalido(Exception):
    """O arquivo enviado não é um backup do NutriData."""


def restaurar_banco(conteudo):
    """Substitui o banco atual pelo backup (bytes de um arquivo .db).

    Antes guarda uma cópia do banco atual em 'nutridata-antes-da-restauracao.db'.
    """
    # Todo arquivo SQLite começa com este texto; barra arquivos vazios ou de outro tipo
    if not conteudo.startswith(b'SQLite format 3\x00'):
        raise BackupInvalido("O arquivo não é um banco de dados válido.")
    # Abre o backup só na memória, para conferir antes de mexer no banco de verdade
    backup = sqlite3.connect(':memory:')
    try:
        backup.deserialize(conteudo)
        tabelas = {linha[0] for linha in backup.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    except sqlite3.DatabaseError as erro:
        backup.close()
        raise BackupInvalido("O arquivo não é um banco de dados válido.") from erro
    if 'historico_consumo' not in tabelas:
        backup.close()
        raise BackupInvalido("O arquivo não parece ser um backup do NutriData.")

    CAMINHO_BANCO.with_name('nutridata-antes-da-restauracao.db').write_bytes(exportar_banco())
    with conectar() as atual:
        # backup() copia página por página, sem precisar apagar o arquivo aberto
        backup.backup(atual)
    backup.close()
    # Backups de versões antigas do app ganham as tabelas e colunas novas
    criar_tabelas()
