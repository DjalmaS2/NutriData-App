import api
import db

# Teste rápido pelo terminal, usando os mesmos módulos do dashboard
db.criar_tabelas()

print("=== Bem-vindo ao NutriData App ===")
codigo_teste = "3017620422003"  # Nutella

peso_input = float(input("Quantas gramas você consumiu? (ex: 30): "))
refeicao_input = input("Qual foi a refeição? (ex: Café da Manhã, Almoço, Janta): ")

try:
    produto = api.buscar_produto(codigo_teste)
except api.ErroAPI as erro:
    print(f"Erro ao acessar a API: {erro}")
else:
    if produto is None:
        print("Produto não encontrado na base de dados.")
    else:
        porcao = api.calcular_porcao(produto, peso_input)
        print(f"\n--- Resumo do Consumo: {produto['nome']} ---")
        print(f"Porção ingerida: {peso_input}g")
        print(f"🔥 Calorias: {porcao['calorias']:.2f} kcal")
        print(f"Carboidratos: {porcao['carboidratos']:.2f}g")
        print(f"Proteínas: {porcao['proteinas']:.2f}g")
        print(f"Gorduras: {porcao['gorduras']:.2f}g")
        print(f"Sódio: {porcao['sodio'] * 1000:.0f}mg")
        print("-" * 30)

        db.salvar_consumo(refeicao_input, produto['nome'], peso_input, porcao['calorias'],
                          porcao['carboidratos'], porcao['proteinas'], porcao['gorduras'], porcao['sodio'])
        print("✅ Sucesso: Refeição salva no seu histórico do banco de dados!")
