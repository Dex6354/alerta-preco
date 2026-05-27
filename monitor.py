import os
import re
import time
import sys

# Garante a importação correta da biblioteca necessária para burlar o 403
try:
    from curl_cffi import requests
except ImportError:
    print("❌ Erro: A biblioteca 'curl_cffi' não está instalada.")
    print("Execute: pip install curl_cffi")
    sys.exit(1)

# ─── Produtos monitorados ────────────────────────────────────────────────────
PRODUTOS = [
    {
        "nome": "Tênis Masculino Nike Revolution 8",
        "url": "https://www.centauro.com.br/tenis-masculino-nike-revolution-8-995996.html?cor=31",
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

# ─── Telegram ────────────────────────────────────────────────────────────────
def enviar_telegram(token, chat_id, mensagem):
    if not token or not chat_id:
        print("⚠️ Telegram não enviado: Variáveis de ambiente faltando.")
        return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": mensagem, "parse_mode": "HTML"}
        
        # Import local para evitar overhead
        import requests as req
        req.post(url, json=payload, timeout=20)
    except Exception as e:
        print(f"⚠️ Erro Telegram: {e}")

# ─── Extração de código e cor da URL ─────────────────────────────────────────
def extrair_codigo_cor(url_produto):
    codigo_match = re.search(r'-(\d{6,7})\.html', url_produto)
    if not codigo_match:
        raise ValueError(f"Código do produto não encontrado na URL: {url_produto}")
    codigo = codigo_match.group(1)

    cor_match = re.search(r'[?&]cor=(\w+)', url_produto)
    if not cor_match:
        raise ValueError(f"Parâmetro 'cor' não encontrado na URL: {url_produto}")
    cor = cor_match.group(1)

    return codigo, cor

# ─── Consulta à API da Centauro ───────────────────────────────────────────────
def buscar_preco_api(url_produto, max_tentativas=3):
    codigo, cor = extrair_codigo_cor(url_produto)
    api_url = f"{CENTAURO_API_BASE}/{codigo}?color={cor}"

    print(f"   🔗 API: {api_url}")

    for tentativa in range(1, max_tentativas + 1):
        try:
            # impersonate="chrome" força o uso de HTTP/2 e as assinaturas TLS corretas contra o Akamai
            s = requests.Session(impersonate="chrome")
            resp = s.get(api_url, headers=HEADERS_API, timeout=30)
            
            print(f"   Status: {resp.status_code}")

            if resp.status_code == 403:
                raise Exception("403 Forbidden (Bloqueio Akamai)")

            if resp.status_code != 200:
                raise Exception(f"API retornou status {resp.status_code}")

            data = resp.json()

            precos_pix = []
            precos_promo = []
            precos_cheios = []

            skus = data.get("skus", [])
            if not skus and data.get("priceInfos"):
                skus = [{"priceInfos": data.get("priceInfos"), "hasStock": True, "description": "Único"}]

            for sku in skus:
                if not sku.get("hasStock", False):
                    continue

                # Lê dinamicamente o tamanho (ex: "43" ou "M")
                tamanho = sku.get("description", "N/A")
                pi = sku.get("priceInfos", {})
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

            raise Exception("Nenhum campo de preço encontrado no JSON")

        except Exception as e:
            print(f"   ❌ Tentativa {tentativa}/{max_tentativas}: {e}")
            if tentativa < max_tentativas:
                time.sleep(5 * tentativa)

    raise Exception(f"Falha total após {max_tentativas} tentativa(s)")

# ─── Monitor principal ────────────────────────────────────────────────────────
def monitor_produto(produto, token, chat_id):
    nome = produto["nome"]
    url  = produto["url"]
    alvo = produto["alvo"]

    print(f"\n{'=' * 60}")
    print(f"📦 {nome}")
    print(f"🎯 Alvo: R$ {alvo:.2f}")
    print(f"{'=' * 60}")

    preco = buscar_preco_api(url)

    print(f"\n💰 Preço final encontrado: R$ {preco:.2f} | Alvo: R$ {alvo:.2f}")

    if preco <= alvo:
        msg = (
            f"🔥 <b>ALERTA CENTAURO!</b>\n"
            f"<b>{nome}</b>\n"
            f"Preço baixou para <b>R$ {preco:.2f}</b> (alvo: R$ {alvo:.2f})\n\n"
            f"{url}"
        )
        enviar_telegram(token, chat_id, msg)
        print(f"📤 Mensagem de alerta enviada!")
    else:
        print(f"✅ Preço acima do alvo. Alerta não enviado.")

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

    if erros:
        print(f"\n⚠️ {len(erros)} produto(s) com erro.")
        # Se houve falha crítica em todos os produtos, força encerramento controlado
        if len(erros) == len(PRODUTOS):
            sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"💥 Erro fatal não tratado no main: {e}")
        sys.exit(1)
