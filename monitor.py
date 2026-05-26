import os
import re
import time
import requests
from urllib.parse import quote

def enviar_telegram(token, chat_id, mensagem):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": mensagem, "parse_mode": "HTML"}
        requests.post(url, json=payload, timeout=20)
    except:
        pass

def monitor_scrapedo():
    url_produto = "https://www.centauro.com.br/conjunto-de-agasalho-oxer-replayer-981478.html?cor=05"
    alvo = 200.00
    
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('CHAT_ID')
    scrape_token = "3a23ea3810a04b16bccfac96a2c3b1af73c97a98ef5"

    for tentativa in range(1, 4):  # 3 tentativas
        try:
            print(f"🔄 Tentativa {tentativa}/3 via Scrape.do...")

            encoded_url = quote(url_produto)
            api_url = f"https://api.scrape.do/?token={scrape_token}&url={encoded_url}&render=true"

            response = requests.get(api_url, timeout=90)
            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                html = response.text
                break
            elif response.status_code == 502:
                print("502 detectado, aguardando antes de retry...")
                time.sleep(8 * tentativa)  # Espera progressiva
                continue
            else:
                raise Exception(f"Scrape.do retornou {response.status_code}")

        except Exception as e:
            if tentativa == 3:
                raise
            time.sleep(5)

    # === EXTRAÇÃO INTELIGENTE DO PREÇO ===
    # Prioriza o preço principal (geralmente o maior + "no Pix")
    matches = re.findall(r'R\$\s*([\d.,]+)', html)

    preco = None
    valid_prices = []
    for m in matches:
        try:
            limpo = m.replace('.', '').replace(',', '.')
            valor = float(limpo)
            if 50 < valor < 1000:          # faixa realista do agasalho
                valid_prices.append(valor)
        except:
            continue

    if valid_prices:
        # Pega o maior preço (geralmente o preço à vista/principal)
        preco = max(valid_prices)

    if preco is None:
        raise Exception("Preço não encontrado")

    print(f"✅ Preço capturado: R$ {preco:.2f}")

    if preco <= alvo:
        msg = f"🔥 <b>ALERTA CENTAURO!</b>\nPreço baixou para <b>R$ {preco:.2f}</b>\n\n{url_produto}"
    else:
        msg = f"✅ Monitor Centauro\nPreço atual: R$ {preco:.2f} (Alvo: R$ {alvo})"
    
    enviar_telegram(token, chat_id, msg)

if __name__ == "__main__":
    monitor_scrapedo()
