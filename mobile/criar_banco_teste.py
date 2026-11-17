r"""Cria um banco de teste com dados de exemplo para ver o app funcionando.

Uso (dentro da pasta mobile/):
    .venv\Scripts\python criar_banco_teste.py
Depois abra o app apontando para ele (PowerShell):
    $env:NUTRIDATA_BANCO = "dados_teste\nutridata-teste.db"; flet run

Nunca mexe no nutridata.db do app web nem no banco do próprio app.
"""
import sys
from datetime import timedelta
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))  # raiz do repositório: db.py, horario.py...

import db  # noqa: E402
import horario  # noqa: E402

CAMINHO = AQUI / 'dados_teste' / 'nutridata-teste.db'


def criar():
    CAMINHO.parent.mkdir(exist_ok=True)
    CAMINHO.unlink(missing_ok=True)  # começa do zero a cada vez
    db.CAMINHO_BANCO = CAMINHO
    db.criar_tabelas()

    hoje = horario.hoje()
    db.salvar_perfil('Masculino', 30, 80, 180, 'Moderado (exercício 3-5x por semana)', 'Perder peso',
                     peso_meta=75)
    refeicoes_de_hoje = [
        ('Café da Manhã', 'Pão, trigo, francês', 50, {'calorias': 150, 'carboidratos': 29, 'proteinas': 4, 'gorduras': 2}),
        ('Café da Manhã', 'Banana, prata, crua', 100, {'calorias': 98, 'carboidratos': 26, 'proteinas': 1.3, 'gorduras': 0.1}),
        ('Almoço', 'Arroz, tipo 1, cozido', 150, {'calorias': 192, 'carboidratos': 42, 'proteinas': 3.8, 'gorduras': 0.3}),
        ('Almoço', 'Feijão, carioca, cozido', 100, {'calorias': 76, 'carboidratos': 13.6, 'proteinas': 4.8, 'gorduras': 0.5}),
        ('Almoço', 'Frango, peito, sem pele, grelhado', 120, {'calorias': 191, 'carboidratos': 0, 'proteinas': 38.4, 'gorduras': 3.0}),
    ]
    for refeicao, nome, gramas, nutrientes in refeicoes_de_hoje:
        db.salvar_consumo(refeicao, nome, gramas, nutrientes)
    db.registrar_agua(hoje, 500)
    db.registrar_agua(hoje, 250)
    db.registrar_atividade(hoje, 'Caminhada (5 km/h)', 40, 187)

    # Alguns dias anteriores, para a sequência de dias e o histórico terem dados
    with db.conectar() as conexao:
        for dias_atras in range(1, 5):
            dia = hoje - timedelta(days=dias_atras)
            conexao.execute(
                "INSERT INTO historico_consumo (data_registro, refeicao, nome_alimento, porcao_g, calorias,"
                " carboidratos, proteinas, gorduras, sodio) VALUES (?, 'Almoço', 'Arroz, tipo 1, cozido', 200,"
                " 256, 56, 5, 0.4, 0)", (f'{dia:%Y-%m-%d} 12:30',))
        conexao.commit()
    for dias_atras, peso in [(21, 81.6), (14, 81.0), (7, 80.4), (0, 80.0)]:
        db.registrar_peso(hoje - timedelta(days=dias_atras), peso)
    print(f'Banco de teste criado em {CAMINHO}')


if __name__ == '__main__':
    criar()
