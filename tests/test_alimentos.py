import pytest
import requests

import api
import taco


# --- Tabela TACO ---

def test_busca_ignora_acentos_e_maiusculas():
    nomes = taco.buscar('FEIJAO carioca')['nome'].tolist()
    assert 'Feijão, carioca, cozido' in nomes


def test_busca_aceita_palavras_fora_de_ordem():
    assert 'Arroz, tipo 1, cozido' in taco.buscar('cozido arroz tipo 1')['nome'].tolist()


@pytest.mark.parametrize('termo', ['', '   ', ', ,'])
def test_busca_vazia_nao_quebra(termo):
    resultado = taco.buscar(termo)
    assert resultado.empty
    assert 'nome' in resultado.columns


def test_valores_batem_com_a_taco_oficial():
    # Feijão carioca cozido, por 100 g, na TACO (Unicamp)
    linha = taco.buscar('feijao carioca cozido').iloc[0]
    produto = taco.como_produto(linha)
    assert produto['calorias_100g'] == pytest.approx(76, abs=1)
    assert produto['fibras_100g'] == pytest.approx(8.5, abs=0.1)
    assert produto['sodio_100g'] == pytest.approx(linha['sodio_mg_100g'] / 1000)  # mg -> g


# --- Porção ---

def test_porcao_proporcional_ao_peso():
    produto = {'nome': 'X', 'calorias_100g': 200, 'ferro_100g': 3}
    assert api.calcular_porcao(produto, 50) == {'calorias': 100, 'ferro': 1.5}


# --- Open Food Facts (sem internet: as respostas são simuladas) ---

class RespostaFalsa:
    def __init__(self, status_code, dados=None):
        self.status_code = status_code
        self._dados = dados or {}

    def json(self):
        return self._dados


def test_produto_encontrado(monkeypatch):
    dados = {'status': 1, 'product': {'product_name': 'Teste', 'nutriments': {
        'energy-kcal_100g': 500, 'calcium_100g': 0.12, 'proteins_100g': None}}}
    monkeypatch.setattr(requests, 'get', lambda *a, **k: RespostaFalsa(200, dados))
    produto = api.buscar_produto('7891000370643')
    assert produto['nome'] == 'Teste'
    assert produto['calorias_100g'] == 500
    assert produto['calcio_100g'] == pytest.approx(120)  # g -> mg
    assert produto['proteinas_100g'] == 0                 # None vira 0


def test_produto_inexistente(monkeypatch):
    monkeypatch.setattr(requests, 'get', lambda *a, **k: RespostaFalsa(404, {'status': 0}))
    assert api.buscar_produto('0000000000000') is None


def test_codigo_com_letras_nem_consulta_a_api(monkeypatch):
    def nao_chamar(*a, **k):
        raise AssertionError("não deveria chamar a API")
    monkeypatch.setattr(requests, 'get', nao_chamar)
    assert api.buscar_produto('abc123') is None


def test_sem_internet_vira_erro_amigavel(monkeypatch):
    def sem_rede(*a, **k):
        raise requests.ConnectionError()
    monkeypatch.setattr(requests, 'get', sem_rede)
    with pytest.raises(api.ErroAPI):
        api.buscar_produto('7891000370643')


# --- Busca com erros de digitação ---

@pytest.mark.parametrize('digitado, esperado', [
    ('feisao', 'feijão'),
    ('feizao', 'feijão'),
    ('arros cosido', 'arroz cozido'),
    ('frango gralhado', 'frango grelhado'),
])
def test_corrige_erros_de_digitacao(digitado, esperado):
    resultados, correcao = taco.buscar_aproximado(digitado)
    assert correcao == esperado
    assert not resultados.empty


def test_feisao_encontra_feijao_carioca():
    resultados, _ = taco.buscar_aproximado('feisao carioca')
    assert 'Feijão, carioca, cozido' in resultados['nome'].tolist()


@pytest.mark.parametrize('termo', ['feijao', 'fei', 'banana prat'])
def test_busca_certa_nao_e_corrigida(termo):
    resultados, correcao = taco.buscar_aproximado(termo)
    assert correcao is None
    assert not resultados.empty


def test_texto_sem_sentido_nao_inventa_resultado():
    resultados, correcao = taco.buscar_aproximado('xyzabc')
    assert correcao is None
    assert resultados.empty


def test_nomes_que_comecam_com_a_palavra_vem_primeiro():
    nomes = taco.buscar('feijao')['nome'].tolist()
    assert nomes[0].startswith('Feijão')
    assert all(n.startswith('Feijão') for n in nomes[:10])
