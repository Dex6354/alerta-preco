import os
import re
import time
import sys

try:
    from curl_cffi import requests as curl_requests
except ImportError:
    print("❌ Erro: A biblioteca 'curl_cffi' não está instalada.")
    print("Execute: pip install curl_cffi")
    sys.exit(1)

import requests

# ============================================================
# CONFIGURAÇÕES CENTAURO
# ============================================================
CENTAURO_API_BASE = "https://apigateway.centauro.com.br/centauro-bff/products"
CENTAURO_HEADERS = {
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

TITULO_ALERTA = "🔥👕 ALERTA CENTAURO!"

# ============================================================
# PRODUTOS MONITORADOS (Alvo, URL)
# ============================================================
PRODUTOS = [
    (300.00, "https://www.centauro.com.br/tenis-masculino-nike-revolution-8-995996.html?cor=31"),
    (70.00, "https://www.centauro.com.br/regata-oxer-regata-respirabilidade-mas-984829.html?cor=83"),
    (200.00, "https://www.centauro.com.br/conjunto-de-agasalho-oxer-replayer-981478.html?cor=05"),
]

# ============================================================
# TELEGRAM
# ============================================================
def enviar_telegram(token, chat_id, mensagem):
    if not token or not chat_id:
        print("⚠️ Telegram não enviado: Variáveis de ambiente faltando.")
        return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": mensagem, "parse_mode": "HTML"}
        requests.post(url, json=payload, timeout=20)
    except Exception as e:
        print(f"⚠️ Erro Telegram (texto): {e}")

def enviar_telegram_foto(token, chat_id, foto_url, caption, nome_arquivo):
    if not token or not chat_id:
        print("⚠️ Telegram não enviado: Variáveis de ambiente faltando.")
        return
    try:
        img_resp = requests.get(foto_url, timeout=20)
        if not img_resp.ok:
            raise Exception(f"Erro ao baixar imagem: {img_resp.status_code}")
        
        filename_limpo = re.sub(r'[\\/*?:"<>|]', "", nome_arquivo).strip()
        filename = f"{filename_limpo}.jpg"

        url = f"https://api.telegram.org/bot{token}/sendDocument"
        data = {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}
        files = {"document": (filename, img_resp.content)}
        
        resp = requests.post(url, data=data, files=files, timeout=30)
        if not resp.ok:
            raise Exception(f"sendDocument retornou {resp.status_code}")
    except Exception as e:
        print(f"⚠️ Erro Telegram (foto): {e} — enviando apenas texto.")
        enviar_telegram(token, chat_id, caption)

# ============================================================
# API SCRAPER
# ============================================================
def extrair_codigo_cor(url_produto):
    codigo_match = re.search(r'-(\d{6,7})\.html', url_produto)
    if not codigo_match:
        raise ValueError(f"Código não encontrado na URL")
    cor_match = re.search(r'[?&]cor=(\w+)', url_produto)
    if not cor_match:
        raise ValueError(f"Parâmetro 'cor' não encontrado")
    return codigo_match.group(1), cor_match.group(1)

def buscar_preco_centauro(url_produto, max_tentativas=3):
    codigo, cor = extrair_codigo_cor(url_produto)
    api_url = f"{CENTAURO_API_BASE}/{codigo}?color={cor}"
    print(f"   🔗 API Centauro: {api_url}")

    for tentativa in range(1, max_tentativas + 1):
        try:
            s = curl_requests.Session(impersonate="chrome")
            resp = s.get(api_url, headers=CENTAURO_HEADERS, timeout=30)

            if resp.status_code == 403:
                raise Exception("403 Forbidden (Akamai)")
            if resp.status_code != 200:
                raise Exception(f"Status {resp.status_code}")

            data = resp.json()
            product_data = data.get("product", {})
            nome_api = product_data.get("name") or "Produto Centauro"
            sizes = product_data.get("sizes", [])

            # Extração da imagem a partir do formato visualMedias
            visual_medias = product_data.get("visualMedias", [])
            imagem_url = None
            for media in visual_medias:
                if media.get("type") == "image" and media.get("url"):
                    imagem_url = media.get("url")
                    break

            if not sizes and product_data.get("priceInfos"):
                sizes = [{"priceInfos": product_data.get("priceInfos"), "hasStock": True}]

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
                return min(precos), nome_api, imagem_url

            raise Exception("Nenhum preço disponível encontrado")
        except Exception as e:
            print(f"   ❌ Tentativa {tentativa}/{max_tentativas}: {e}")
            if tentativa < max_tentativas:
                time.sleep(5 * tentativa)

    raise Exception(f"Falha total após {max_tentativas} tentativas")

# ============================================================
# MONITOR CORE
# ============================================================
def monitorar_url_unica(alvo, url, token, chat_id):
    print(f"\n🔍 Monitorando | Alvo: R$ {alvo:.2f} | {url}")
    try:
        preco, nome_real, imagem_url = buscar_preco_centauro(url)
        print(f"   💰 {nome_real} — R$ {preco:.2f}")

        if preco <= alvo:
            caption = (
                f"<b>{TITULO_ALERTA}</b>\n\n"
                f'👉<a href="{url}">{nome_real}</a>\n\n'
                f"💰Preço: <b>R$ {preco:.2f}</b>\n"
                f"🎯Alvo:  <b>R$ {alvo:.2f}</b>"
            )
            if imagem_url:
                enviar_telegram_foto(token, chat_id, imagem_url, caption, nome_real)
            else:
                enviar_telegram(token, chat_id, caption)
            print("   📤 Alerta enviado!")
        else:
            print("   ℹ️ Preço acima do alvo.")
    except Exception as e:
        print(f"   ❌ Erro ao processar link: {e}")
        return False
    return True

def main():
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    erros = 0

    print("\n🚀 INICIANDO MONITOR CENTAURO")
    for entrada in PRODUTOS:
        alvo = entrada[0]
        urls = entrada[1:]
        for url in urls:
            sucesso = monitorar_url_unica(alvo, url, token, chat_id)
            if not sucesso:
                erros += 1
            time.sleep(2)

    if erros == len(PRODUTOS):
        sys.exit(1)

if __name__ == "__main__":
    main()
