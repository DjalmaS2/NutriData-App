import requests

def calcular_nutrientes(codigo_de_barras, peso_consumido):
    url = f"https://world.openfoodfacts.org/api/v0/product/{codigo_de_barras}.json"
    resposta = requests.get(url)
    
    if resposta.status_code == 200:
        dados = resposta.json()
        
        if dados.get('status') == 1:
            produto = dados['product']
            nome = produto.get('product_name', 'Nome não disponível')
            nutrientes = produto.get('nutriments', {})
            
            # Pegando os valores base (por 100g)
            carb_100g = nutrientes.get('carbohydrates_100g', 0)
            prot_100g = nutrientes.get('proteins_100g', 0)
            gordura_100g = nutrientes.get('fat_100g', 0) 
            sodio_100g = nutrientes.get('sodium_100g', 0)
            
            # Calculando a proporção exata pelo peso
            peso = float(peso_consumido)
            carb_real = (carb_100g / 100) * peso
            prot_real = (prot_100g / 100) * peso
            gordura_real = (gordura_100g / 100) * peso 
            sodio_real = (sodio_100g / 100) * peso
            
            # Exibindo o resultado final
            print(f"\n--- Resumo do Consumo: {nome} ---")
            print(f"Porção ingerida: {peso}g")
            print(f"Carboidratos: {carb_real:.2f}g")
            print(f"Proteínas: {prot_real:.2f}g")
            print(f"Gorduras: {gordura_real:.2f}g")
            print(f"Sódio: {sodio_real:.2f}g")
            
        else:
            print("Produto não encontrado na base de dados.")
    else:
        print(f"Erro ao acessar a API. Código HTTP: {resposta.status_code}")

# --- Interação principal do programa ---
codigo_teste = "3017620422003" # Código da Nutella
print("Produto lido: Nutella")
peso_input = input("Quantas gramas você consumiu? (Digite apenas números, ex: 30): ")

calcular_nutrientes(codigo_teste, peso_input)