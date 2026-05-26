import os
import re
import requests
from urllib.parse import quote

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
    scrape_token = "3a23ea3810a04b16bccfac96a2c3b1af73c97a98ef5"

    try:
        print("🔄 Buscando via Scrape.do...")

        # Encoding correto da URL
        encoded_url = quote(url_produto)
        
        # URL da API com parâmetros essenciais
        api_url = (
            f"https://api.scrape.do/"
            f"?token={scrape_token}"
            f"&url={encoded_url}"
            f"&render=true"           # Ativa navegador para carregar JS
            f"&waitUntil=networkidle" # Espera carregar completamente
            f"&timeout=60000"
        )

        response = requests.get(api_url, timeout=90)
        
        print(f"Status Scrape.do: {response.status_code}")

        if response.status_code != 200:
            raise Exception(f"Scrape.do retornou {response.status_code} - Verifique o token ou limite de créditos")

        html = response.text

        # Extração melhorada do preço
        matches = re.findall(r'R\$\s*([\d.,]+)', html)
        
        preco = None
        if matches:
            for m in matches:
                try:
                    limpo = m.replace('.', '').replace(',', '.')
                    valor = float(limpo)
                    if 10 < valor < 10000:   # Preço realista
                        preco = valor
                        break
                except:
                    continue

        if preco is None:
            # Fallback: busca mais ampla
            matches = re.findall(r'(\d{2,4})[.,](\d{2})', html)
            if matches:
                m = matches[0]
                preco = float(m[0] + '.' + m[1])

        if preco is None:
            raise Exception("Preço não encontrado na resposta")

        print(f"✅ Preço capturado: R$ {preco:.2f}")

        if preco <= alvo:
            msg = f"🔥 <b>ALERTA CENTAURO!</b>\nPreço baixou para <b>R$ {preco:.2f}</b>\n\n{url_produto}"
            enviar_telegram(token, chat_id, msg)
        else:
            msg = f"✅ Monitor Centauro\nPreço atual: R$ {preco:.2f} (Alvo: R$ {alvo})"
            enviar_telegram(token, chat_id, msg)

    except Exception as e:
        erro = str(e)[:300]
        print(f"❌ Erro: {erro}")
        enviar_telegram(token, chat_id, f"❌ Erro Scrape.do Centauro:\n{erro}")

if __name__ == "__main__":
    monitor_scrapedo()
