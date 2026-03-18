import requests
import sqlite3
from datetime import datetime

# --- 1. Nova Função: Salvar no Banco ---
def salvar_no_banco(refeicao, nome_alimento, peso, carb, prot, gord, sodio):
    # Conecta ao arquivo que você acabou de criar
    conexao = sqlite3.connect('nutridata.db')
    cursor = conexao.cursor()
    
    # Pega a data e hora exata de agora
    data_atual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # O comando SQL para INSERIR os dados. As interrogações (?) são uma medida de segurança.
    cursor.execute('''
        INSERT INTO historico_consumo 
        (data_registro, refeicao, nome_alimento, porcao_g, carboidratos, proteinas, gorduras, sodio)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (data_atual, refeicao, nome_alimento, peso, carb, prot, gord, sodio))
    
    conexao.commit()
    conexao.close()
    print("✅ Sucesso: Refeição salva no seu histórico do banco de dados!")


# --- 2. A Função da API (com a chamada para o banco) ---
def calcular_nutrientes(codigo_de_barras, peso_consumido, tipo_refeicao):
    url = f"https://world.openfoodfacts.org/api/v0/product/{codigo_de_barras}.json"
    resposta = requests.get(url)
    
    if resposta.status_code == 200:
        dados = resposta.json()
        
        if dados.get('status') == 1:
            produto = dados['product']
            nome = produto.get('product_name', 'Nome não disponível')
            nutrientes = produto.get('nutriments', {})
            
            carb_100g = nutrientes.get('carbohydrates_100g', 0)
            prot_100g = nutrientes.get('proteins_100g', 0)
            gordura_100g = nutrientes.get('fat_100g', 0) 
            sodio_100g = nutrientes.get('sodium_100g', 0)
            
            peso = float(peso_consumido)
            carb_real = (carb_100g / 100) * peso
            prot_real = (prot_100g / 100) * peso
            gordura_real = (gordura_100g / 100) * peso 
            sodio_real = (sodio_100g / 100) * peso
            
            print(f"\n--- Resumo do Consumo: {nome} ---")
            print(f"Porção ingerida: {peso}g")
            print(f"Carboidratos: {carb_real:.2f}g")
            print(f"Proteínas: {prot_real:.2f}g")
            print(f"Gorduras: {gordura_real:.2f}g")
            print(f"Sódio: {sodio_real:.2f}g")
            print("-" * 30)
            
            # 👇 AQUI ESTÁ A MÁGICA: Chamamos a função de salvar passando todos os dados calculados
            salvar_no_banco(tipo_refeicao, nome, peso, carb_real, prot_real, gordura_real, sodio_real)
            
        else:
            print("Produto não encontrado na base de dados.")
    else:
        print(f"Erro ao acessar a API. Código HTTP: {resposta.status_code}")

# --- 3. Interação com o usuário ---
print("=== Bem-vindo ao NutriData App ===")
codigo_teste = "3017620422003" # Nutella
print("Produto lido: Nutella")

# Perguntando as duas informações cruciais
peso_input = input("Quantas gramas você consumiu? (ex: 30): ")
refeicao_input = input("Qual foi a refeição? (ex: Café da Manhã, Almoço, Janta): ")

# Iniciando o motor
calcular_nutrientes(codigo_teste, peso_input, refeicao_input)