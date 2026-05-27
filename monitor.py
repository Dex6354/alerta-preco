import os
import re
import time
import sys

try:
    from curl_cffi import requests
except ImportError:
    print("❌ Erro: A biblioteca 'curl_cffi' não está instalada.")
    print("Execute: pip install curl_cffi")
    sys.exit(1)

PRODUTOS = [
    {
        "nome": "Tênis Masculino Nike Revolution 8",
        "url": "https://www.centauro.com.br/tenis-masculino-nike-revolution-8-995996.html?cor=31",
        "alvo": 300.00,
    },
    {
        "nome": "Regata",
        "url": "https://www.centauro.com.br/regata-oxer-regata-respirabilidade-mas-984829.html?cor=83",
        "alvo": 300.00,
    },
    {
        "nome": "Conjunto Agasalho Oxer Replayer",
        "url": "https://www.centauro.com.br/conjunto-de-agasalho-oxer-replayer-981478.html?cor=05",
        "alvo": 200.00,
    }
]

CENTAURO_API_BASE = "https://apigateway.centauro.com.br/centauro-bff/products"

HEADERS_API = {
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

def enviar_telegram(token, chat_id, mensagem):
    if not token or not chat_id:
        print("⚠️ Telegram não enviado: Variáveis de ambiente faltando.")
        return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": mensagem, "parse_mode": "HTML"}
        import requests as req
        req.post(url, json=payload, timeout=20)
    except Exception as e:
        print(f"⚠️ Erro Telegram: {e}")

def extrair_codigo_cor(url_produto):
    codigo_match = re.search(r'-(\d{6,7})\.html', url_produto)
    if not codigo_match:
        raise ValueError(f"Código não encontrado na URL: {url_produto}")
    cor_match = re.search(r'[?&]cor=(\w+)', url_produto)
    if not cor_match:
        raise ValueError(f"Parâmetro 'cor' não encontrado na URL: {url_produto}")
    return codigo_match.group(1), cor_match.group(1)

def buscar_preco_api(url_produto, max_tentativas=3):
    codigo, cor = extrair_codigo_cor(url_produto)
    api_url = f"{CENTAURO_API_BASE}/{codigo}?color={cor}"
    print(f"   🔗 API: {api_url}")

    for tentativa in range(1, max_tentativas + 1):
        try:
            s = requests.Session(impersonate="chrome")
            resp = s.get(api_url, headers=HEADERS_API, timeout=30)
            print(f"   Status: {resp.status_code}")

            if resp.status_code == 403:
                raise Exception("403 Forbidden (Bloqueio Akamai)")
            if resp.status_code != 200:
                raise Exception(f"API retornou status {resp.status_code}")

            data = resp.json()
            
            product_data = data.get("product", {})
            sizes = product_data.get("sizes", [])
            
            if not sizes and product_data.get("priceInfos"):
                sizes = [{"priceInfos": product_data.get("priceInfos"), "hasStock": True, "description": "Único"}]

            precos_pix = []
            precos_promo = []
            precos_cheios = []

            for item in sizes:
                if not item.get("hasStock", False):
                    continue

                tamanho = item.get("description", "N/A")
                pi = item.get("priceInfos", {})
                if not pi:
                    continue

                pix = pi.get("pixDiscount", {})
                if pix and pix.get("price"):
                    v_pix = float(pix["price"])
                    precos_pix.append(v_pix)
                    print(f"   [Disponível] Tam: {tamanho} | Pix: R$ {v_pix:.2f}")

                promo = pi.get("promotionalPrice")
                if promo:
                    precos_promo.append(float(promo))

                cheio = pi.get("price")
                if cheio:
                    precos_cheios.append(float(cheio))

            if precos_pix:
                return min(precos_pix)
            if precos_promo:
                return min(precos_promo)
            if precos_cheios:
                return min(precos_cheios)

            raise Exception("Nenhum preço disponível encontrado no JSON")

        except Exception as e:
            print(f"   ❌ Tentativa {tentativa}/{max_tentativas}: {e}")
            if tentativa < max_tentativas:
                time.sleep(5 * tentativa)

    raise Exception(f"Falha total após {max_tentativas} tentativa(s)")

def monitor_produto(produto, token, chat_id):
    nome = produto["nome"]
    url  = produto["url"]
    alvo = produto["alvo"]

    print(f"\n{'=' * 60}\n📦 {nome}\n🎯 Alvo: R$ {alvo:.2f}\n{'=' * 60}")
    preco = buscar_preco_api(url)
    print(f"\n💰 Preço final encontrado: R$ {preco:.2f}")

    if preco <= alvo:
        msg = (
            f"🔥 <b>ALERTA CENTAURO!</b>\n\n"
            f'<a href="{url}">{nome}</a>\n\n'
            f"Preço: R$ {preco:.2f}\n"
            f"Alvo: R$ {alvo:.2f}"
        )
        enviar_telegram(token, chat_id, msg)
        print(f"📤 Alerta enviado!")
    else:
        print(f"✅ Preço acima do alvo.")

def main():
    token   = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('CHAT_ID')

    erros = []
    for produto in PRODUTOS:
        try:
            monitor_produto(produto, token, chat_id)
        except Exception as e:
            print(f"\n❌ ERRO em '{produto['nome']}': {e}")
            erros.append((produto["nome"], str(e)))

    if erros and len(erros) == len(PRODUTOS):
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"💥 Erro fatal: {e}")
        sys.exit(1)
