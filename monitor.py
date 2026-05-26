import os
import re
import requests
from urllib.parse import quote_plus

def enviar_telegram(token, chat_id, mensagem):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": mensagem, "parse_mode": "HTML"}
        requests.post(url, json=payload, timeout=15)
    except Exception as e:
        print(f"Erro Telegram: {e}")

def monitor_scrapedo():
    url_produto = "https://www.centauro.com.br/conjunto-de-agasalho-oxer-replayer-981478.html?cor=05"
    alvo = 200.00
    
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('CHAT_ID')
    scrape_token = "3a23ea3810a04b16bccfac96a2c3b1af73c97a98ef5"   # Sua chave

    try:
        print("🔄 Buscando via Scrape.do...")

        # Monta a URL da API
        encoded_url = quote_plus(url_produto)
        api_url = f"https://api.scrape.do/?token={scrape_token}&url={encoded_url}&render=true&waitUntil=networkidle"

        response = requests.get(api_url, timeout=60)
        
        if response.status_code != 200:
            raise Exception(f"Scrape.do retornou {response.status_code}")

        html = response.text

        # === EXTRAÇÃO DO PREÇO ===
        # Procura por R$ seguido de número
        matches = re.findall(r'R\$\s*([\d.,]+)', html)
        
        preco = None
        if matches:
            # Pega o primeiro preço válido (geralmente o principal)
            for match in matches:
                limpo = match.replace('.', '').replace(',', '.')
                try:
                    preco_temp = float(limpo)
                    if preco_temp > 10:  # Evita preços muito baixos (ex: frete)
                        preco = preco_temp
                        break
                except:
                    continue

        if preco is None:
            raise Exception("Não foi possível extrair o preço")

        print(f"✅ Preço capturado: R$ {preco:.2f}")

        if preco <= alvo:
            msg = f"🔥 <b>ALERTA CENTAURO!</b>\nPreço baixou para <b>R$ {preco:.2f}</b>\n\n{url_produto}"
            enviar_telegram(token, chat_id, msg)
        else:
            msg = f"✅ Monitor Centauro\nPreço atual: R$ {preco:.2f} (Alvo: R$ {alvo})"
            enviar_telegram(token, chat_id, msg)

    except Exception as e:
        erro = str(e)[:250]
        print(f"❌ Erro: {erro}")
        enviar_telegram(token, chat_id, f"❌ Erro Scrape.do Centauro:\n{erro}")

if __name__ == "__main__":
    monitor_scrapedo()
