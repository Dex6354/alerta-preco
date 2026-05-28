import os
import re
import sys
import time
from urllib.parse import quote
import requests

try:
    from curl_cffi import requests as curl_requests
except ImportError:
    print("❌ Erro: A biblioteca 'curl_cffi' não está instalada.")
    print("Execute: pip install curl_cffi")
    sys.exit(1)

# ============================================================
# CONFIGURAÇÃO DE PRODUTOS (Suporta 1 ou múltiplas URLs por alvo)
# ============================================================
PRODUTOS = [
    {
        "nome": "Tênis Masculino Nike Revolution 8",
        "urls": [
            "https://www.centauro.com.br/tenis-masculino-nike-revolution-8-995996.html?cor=31"
        ],
        "alvo": 300.00,
    },
    {
        "nome": "Sorvete Bombom Jundiaí Pote 2L",
        "urls": [
            "https://www.loja.shibata.com.br/produto/11622/sorvete-bombom-jundia-pote-2l"
        ],
        "alvo": 40.00,
    },
    {
        "nome": "Exemplo Multi-Links (Mesmo Alvo)",
        "urls": [
            "https://www.centauro.com.br/regata-oxer-regata-respirabilidade-mas-984829.html?cor=83",
            "https://www.centauro.com.br/conjunto-de-agasalho-oxer-replayer-981478.html?cor=05"
        ],
        "alvo": 150.00,
    }
]

# ============================================================
# CONFIGURAÇÕES DA API
# ============================================================
CENTAURO_API_BASE = "https://apigateway.centauro.com.br/centauro-bff/products"
HEADERS_CENTAURO = {
    "authority": "apigateway.centauro.com.br",
    "accept": "application/json, text/plain, */*",
    "accept-language": "pt-BR,pt;q=0.9",
    "origin": "https://www.centauro.com.br",
    "referer": "https://www.centauro.com.br/",
    "sec-ch-ua": '"Chromium";v="148", "Brave";v="148", "Not/A)Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
}

SHIBATA_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJ2aXBjb21tZXJjZSIsImF1ZCI6ImFwaS1hZG1pbiIsInN1YiI6IjZiYzQ4NjdlLWRjYTktMTFlOS04NzQyLTAyMGQ3OTM1OWNhMCIsInZpcGNvbW1lcmNlQ2xpZW50ZUlkIjpudWxsLCJpYXQiOjE3NTE5MjQ5MjgsInZlciI6MSwiY2xpVENTIjpudWxsLCJvcGVyYXRvciI6bnVsbCwib3JnIjoiMTYxIn0.yDCjqkeJv7D3wJ0T_fu3AaKlX9s5PQYXD19cESWpH-j3F_Is-Zb-bDdUvduwoI_RkOeqbYCuxN0ppQQXb1ArVg"
SHIBATA_ORG_ID = "161"
HEADERS_SHIBATA = {
    "Authorization": f"Bearer {SHIBATA_TOKEN}",
    "organizationid": SHIBATA_ORG_ID,
    "sessao-id": "4ea572793a132ad95d7e758a4eaf6b09",
    "domainkey": "loja.shibata.com.br",
    "User-Agent": "Mozilla/5.0",
}

# ------------------------------------------------------------
# TELEGRAM
# ------------------------------------------------------------
def enviar_telegram(token, chat_id, mensagem):
    if not token or not chat_id:
        print("⚠️ Telegram não enviado: Variáveis de ambiente faltando.")
        return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": mensagem, "parse_mode": "HTML"}
        requests.post(url, json=payload, timeout=20)
    except Exception as e:
        print(f"⚠️ Erro Telegram: {e}")

# ------------------------------------------------------------
# PARSERS E BUSCA CENTAURO
# ------------------------------------------------------------
def extrair_codigo_cor_centauro(url_produto):
    codigo_match = re.search(r'-(\d{6,7})\.html', url_produto)
    if not codigo_match:
        raise ValueError(f"Código não encontrado na URL: {url_produto}")
    cor_match = re.search(r'[?&]cor=(\w+)', url_produto)
    if not cor_match:
        raise ValueError(f"Parâmetro 'cor' não encontrado na URL: {url_produto}")
    return codigo_match.group(1), cor_match.group(1)

def buscar_preco_centauro(url_produto, max_tentativas=3):
    codigo, cor = extrair_codigo_cor_centauro(url_produto)
    api_url = f"{CENTAURO_API_BASE}/{codigo}?color={cor}"
    print(f"   🔗 API Centauro: {api_url}")

    for tentativa in range(1, max_tentativas + 1):
        try:
            s = curl_requests.Session(impersonate="chrome")
            resp = s.get(api_url, headers=HEADERS_CENTAURO, timeout=30)

            if resp.status_code == 403:
                raise Exception("403 Forbidden (Bloqueio Akamai)")
            if resp.status_code != 200:
                raise Exception(f"API retornou status {resp.status_code}")

            data = resp.json()
            product_data = data.get("product", {})
            sizes = product_data.get("sizes", [])

            if not sizes and product_data.get("priceInfos"):
                sizes = [{"priceInfos": product_data.get("priceInfos"), "hasStock": True, "description": "Único"}]

            precos = []
            for item in sizes:
                if not item.get("hasStock", False):
                    continue
                pi = item.get("priceInfos", {})
                if not pi:
                    continue

                pix = pi.get("pixDiscount", {})
                if pix and pix.get("price"):
                    precos.append(float(pix["price"]))
                elif pi.get("promotionalPrice"):
                    precos.append(float(pi["promotionalPrice"]))
                elif pi.get("price"):
                    precos.append(float(pi["price"]))

            if precos:
                return min(precos)
            raise Exception("Nenhum preço disponível encontrado no JSON")
        except Exception as e:
            print(f"   ❌ Tentativa {tentativa}/{max_tentativas}: {e}")
            if tentativa < max_tentativas:
                time.sleep(5 * tentativa)
    raise Exception(f"Falha total na Centauro após {max_tentativas} tentativa(s)")

# ------------------------------------------------------------
# PARSERS E BUSCA SHIBATA
# -----------------------------------------------------------
