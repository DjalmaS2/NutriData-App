r"""Copia a lógica compartilhada (raiz do repositório) para src/nucleo/ antes de gerar o APK.

O APK só leva o que está dentro de src/. Os arquivos continuam sendo editados SÓ na raiz;
src/nucleo/ é uma cópia descartável (está no .gitignore), refeita a cada build:
    .venv\Scripts\python preparar_build.py
    flet build apk
"""
import shutil
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
DESTINO = AQUI / 'src' / 'nucleo'

MODULOS = ['db.py', 'metas.py', 'taco.py', 'api.py', 'exercicios.py', 'jejum.py', 'horario.py', 'formatos.py']
DADOS = ['dados/taco.csv']


def preparar():
    shutil.rmtree(DESTINO, ignore_errors=True)
    (DESTINO / 'dados').mkdir(parents=True)
    for arquivo in MODULOS + DADOS:
        shutil.copy2(RAIZ / arquivo, DESTINO / arquivo)
    print(f'{len(MODULOS)} módulos e {len(DADOS)} arquivo(s) de dados copiados para {DESTINO}')


if __name__ == '__main__':
    preparar()
