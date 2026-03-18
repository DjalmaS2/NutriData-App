import requests

def buscar_alimento(codigo_de_barras):
    # 1. A URL da API pública apontando para o produto específico
    url = f"https://world.openfoodfacts.org/api/v0/product/{codigo_de_barras}.json"
    
    # 2. Fazendo o pedido (requisição GET) para a API
    resposta = requests.get(url)
    
    # 3. Verificando se a comunicação com o servidor deu certo (Status 200 = Sucesso)
    if resposta.status_code == 200:
        dados = resposta.json()
        
        # A API retorna 'status': 1 se encontrou o produto, e 0 se não encontrou
        if dados.get('status') == 1:
            produto = dados['product']
            
            # 4. Extraindo as informações específicas
            # Usamos o .get() para evitar erros caso o produto não tenha essa informação cadastrada
            nome = produto.get('product_name', 'Nome não disponível')
            nutrientes = produto.get('nutriments', {})
            
            # A base de dados geralmente padroniza os valores para cada 100 gramas
            carboidratos = nutrientes.get('carbohydrates_100g', 0)
            proteinas = nutrientes.get('proteins_100g', 0)
            gordura = nutrientes.get('fat_100g',0)
            sodio = nutrientes.get('sodium_100g', 0)
            
            print(f"--- Produto Encontrado ---")
            print(f"Nome: {nome}")
            print(f"Carboidratos (por 100g): {carboidratos}g")
            print(f"Proteínas (por 100g): {proteinas}g")
            print(f"Gorduras(por 100g):{gordura}g")
            print(f"Sódio (por 100g): {sodio}g")
            
        else:
            print("Produto não encontrado na base de dados do Open Food Facts.")
    else:
        print(f"Erro ao acessar a API. Código HTTP: {resposta.status_code}")

# Vamos testar com o código de barras da Nutella (como exemplo universal)
codigo_teste = "3017620422003" 
buscar_alimento(codigo_teste)