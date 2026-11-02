<p align="center">
  <img src="imagens/logo.svg" alt="NutriData" width="220">
</p>

# NutriData

App de nutrição feito em **Python** e **Streamlit**: registre o que você come, acompanhe calorias,
macronutrientes, vitaminas e minerais, água, peso e exercícios, tudo com dados brasileiros
(Tabela TACO) e sem nenhum serviço pago.

## Funcionalidades

| Página | O que faz |
|---|---|
| 📅 **Dia** | Calorias restantes da meta, diário por refeição (café, almoço, lanche e jantar), metas de macros, água, fibras/vitaminas/minerais e sequência de dias registrando |
| 📈 **Histórico** | Calorias por dia (7, 30 ou 90 dias) com a linha da meta, evolução do peso e previsão de quando você chega à meta de peso |
| 🍲 **Meus Pratos** | Monte receitas com ingredientes da TACO e registre só a parte que comeu |
| 🏋️ **Exercícios** | Registre a atividade e o tempo de treino; o app estima as calorias gastas (e você pode ajustar) |
| ⏱️ **Jejum** | Cronômetro de jejum intermitente (12:12 a 20:4) com histórico e metas cumpridas |
| 👤 **Perfil** | Calcula a meta calórica (fórmula de Mifflin-St Jeor), os macros e a água pelo seu perfil, e guarda a meta de peso |
| 💾 **Backup** | Baixa e restaura todos os dados e exporta uma planilha Excel |

Na barra lateral, em qualquer página, dá para registrar um alimento de três jeitos:
**busca na Tabela TACO** (que entende erros de digitação, como "feisao" → feijão), **código de barras pela câmera** ou **digitando o código** (Open Food Facts).

## Como rodar

Precisa do [Python](https://www.python.org/downloads/) 3.11 ou mais novo.

```bash
pip install -r requirements.txt
streamlit run dashboard.py
```

O app abre no navegador em `http://localhost:8501`. Para parar, aperte **Ctrl + C** no terminal.

> **Câmera no Windows:** a leitura de código de barras usa o `pyzbar`, que no Windows precisa do
> [Visual C++ Redistributable 2013](https://www.microsoft.com/download/details.aspx?id=40784).
> Sem ele o app funciona normalmente; só a aba da câmera fica desativada.

## Testes

```bash
pip install -r requirements-dev.txt
python -m pytest
```

Os testes conferem os cálculos (metas, macros, porções, calorias de exercício, sequência de dias),
a busca na TACO, a API (com respostas simuladas, sem internet), o banco de dados, o backup e se cada
página abre sem erro. Cada teste usa um banco temporário: o seu `nutridata.db` nunca é alterado.

## Estrutura do projeto

```
dashboard.py        arquivo principal: configura o app, monta a barra lateral e abre a página
paginas/            uma tela por arquivo (dia, historico, pratos, exercicios, jejum, perfil, backup)
comum.py            partes usadas por várias páginas (refeições, cores, campo da meta)
db.py               banco de dados SQLite: tabelas, leitura, gravação e backup
api.py              busca de produtos por código de barras no Open Food Facts
taco.py             busca de alimentos na Tabela TACO
metas.py            cálculos de meta calórica, macros, água e valores diários
exercicios.py       atividades físicas, calorias gastas e sequência de dias
jejum.py            protocolos e cálculos do jejum intermitente
dados/taco.csv      Tabela TACO com os valores por 100 g
tests/              testes automáticos (pytest)
.streamlit/         tema visual do app
```

## Decisões do projeto

- **Banco local (SQLite):** simples e gratuito. No Streamlit Cloud o arquivo é apagado quando o
  servidor reinicia, por isso existe a página de **Backup**.
- **Sem serviços pagos:** nada de APIs de IA ou serviços cobrados por uso.
- **Exercícios e meta:** o nível de atividade do perfil já conta os treinos de costume, então somar
  as calorias dos exercícios à meta é opcional (senão elas seriam contadas duas vezes).

## Deploy no Streamlit Cloud

Arquivo principal: `dashboard.py`. O `packages.txt` instala o `libzbar0`, necessário para a câmera.

## Fontes dos dados

- **[Tabela TACO](https://nepa.unicamp.br/publicacoes/tabela-taco-pdf/)** (Tabela Brasileira de
  Composição de Alimentos), do NEPA/Unicamp, convertida a partir de
  [marcelosanto/tabela_taco](https://github.com/marcelosanto/tabela_taco) (licença MIT).
- **[Open Food Facts](https://world.openfoodfacts.org/)**, base colaborativa de produtos
  (licença ODbL).
- **Valores Diários de referência:** ANVISA, IN 75/2020.
- **Gasto calórico das atividades (MET):** Compêndio de Atividades Físicas (Ainsworth et al.).

> O NutriData é um projeto de estudo e não substitui o acompanhamento de um nutricionista.
