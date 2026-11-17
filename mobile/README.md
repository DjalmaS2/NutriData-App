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
    telas/hoje.py        tela Hoje
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
não some ao atualizar o APK. O backup (exportar/importar o `.db`) chega na etapa 4.

## Gerar o APK (etapa 5)

```powershell
.venv\Scripts\python preparar_build.py
.venv\Scripts\flet build apk
```

O passo a passo completo (Flutter, Android SDK e instalação no celular) vem na etapa 5.
