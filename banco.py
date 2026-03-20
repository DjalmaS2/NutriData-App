import sqlite3

def criar_banco_de_dados():
    # 1. Cria a conexão. Se o arquivo 'nutridata.db' não existir, o Python cria ele na hora.
    conexao = sqlite3.connect('nutridata.db')
    
    # 2. O 'cursor' é o que usamos para executar os comandos SQL dentro do banco
    cursor = conexao.cursor()
    
    # 3. Executando o comando SQL para criar a nossa tabela
    cursor.execute('''
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
    
    # 4. Salva as alterações e fecha a porta do banco
    conexao.commit()
    conexao.close()
    
    print("Banco de dados 'nutridata.db' e tabela 'historico_consumo' criados com sucesso!")

# Chama a função para executar a criação
criar_banco_de_dados()