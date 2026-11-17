# NutriData Mobile (Android)

App de celular do NutriData, feito em Python com [Flet](https://flet.dev) 1.1.
Os dados ficam no próprio celular (SQLite) e o app funciona sem internet.

A lógica é a mesma do app web: `db.py`, `metas.py`, `taco.py`, `exercicios.py`, `jejum.py`,
`horario.py` e `formatos.py` ficam na **raiz do repositório** e são usados pelos dois apps.
Altere esses arquivos só lá.

## Pastas

```
mobile/
  pyproject.toml         configuração do app e do APK (nome, dependências)
  criar_banco_teste.py   cria um banco com dados de exemplo
  preparar_build.py      copia a lógica da raiz para src/nucleo/ antes de gerar o APK
  src/
    main.py              abre o app: banco, tema e barra de navegação
    tema.py              cores e fontes da identidade visual
    logica.py            regras sem Flet (testadas em tests/test_mobile.py)
    telas/hoje.py        tela Hoje
    telas/adicionar.py   Adicionar alimento (TACO, código de barras, Meus pratos) e Novo prato
    telas/historico.py   Histórico: calorias por dia, peso e previsão da meta de peso
    telas/treino.py      Treino: atividade + tempo -> calorias (dá para trocar a estimativa)
    telas/perfil.py      Perfil: dados da pessoa, metas calculadas e atalhos para Jejum e Backup
    telas/jejum.py       Jejum intermitente: começar, acompanhar até a meta e histórico
    telas/backup.py      Backup: salvar e restaurar o banco (.db)
    telas/componentes.py peças repetidas: busca na TACO, porção com prévia, botões
    telas/graficos.py    gráficos de barras e de linha desenhados com o próprio Flet
    assets/fonts/        Fraunces e DM Sans (licença OFL, arquivos .txt ao lado)
```

## Rodar no computador

No PowerShell, dentro da pasta `mobile`:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install "flet[all]==1.1.2" pandas requests tzdata
.venv\Scripts\flet run
```

O app abre numa janela com o banco dele, em `mobile\.flet\storage\data\nutridata.db`
(nunca o `nutridata.db` do app web).

### Ver com dados de exemplo

```powershell
.venv\Scripts\python criar_banco_teste.py
$env:NUTRIDATA_BANCO = "dados_teste\nutridata-teste.db"; .venv\Scripts\flet run
```

Para voltar ao banco normal, feche o PowerShell (ou rode `Remove-Item Env:NUTRIDATA_BANCO`).

## Onde fica o banco no celular

O Flet cria uma pasta privada para o app (`FLET_APP_STORAGE_DATA`). O banco fica lá e
não some ao atualizar o APK, mas some se o app for desinstalado. Por isso existe a tela
Perfil > Backup: ela salva um `.db` onde você escolher (Downloads, Google Drive...) e restaura
a partir dele. O mesmo arquivo funciona no app web (página Backup).

## Gerar o APK (etapa 5)

```powershell
.venv\Scripts\python preparar_build.py
.venv\Scripts\flet build apk
```

O passo a passo completo (Flutter, Android SDK e instalação no celular) vem na etapa 5.
