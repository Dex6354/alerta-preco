import json
import requests

url = "https://www.nagumo.com.br/on/demandware.store/Sites-Nagumo-Site/pt_BR/Product-Variation"
params = {"pid": "13772"}

# O cookie 'dw_store' força a filial 22.
cookies = {
    "dw_store": "22",
    "dw_consent": "tracking=false",
    "__cq_dnt": "1",
    "dw_dnt": "1"
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest"
}

response = requests.get(url, params=params, cookies=cookies, headers=headers)

if response.status_code == 200:
    dados = response.json()
    # Exibe o JSON inteiro com indentação organizada
    print(json.dumps(dados, indent=4, ensure_ascii=False))
else:
    print(f"Erro na requisição: {response.status_code}")