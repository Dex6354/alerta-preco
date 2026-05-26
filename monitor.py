import os
import re
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

    try:
        encoded_url = quote(url_produto)
        api_url = f"https://api.scrape.do/?token={scrape_token}&url={encoded_url}&render=true"

        response = requests.get(api_url, timeout=90)
        
        if response.status_code != 200:
            raise Exception(f"Scrape.do retornou {response.status_code}")

        html = response.text

        # === EXTRAÇÃO MELHORADA ===
        # Prioriza preços principais (geralmente maiores e com "no Pix" ou sem "x")
        # Evita preços de parcelamento

        # Padrão 1: Preço principal com "no Pix" ou logo após R$
        match = re.search(r'R\$\s*([\d.,]+).*?(no Pix|à vista|atual)', html, re.I)
        if match:
            preco_str = match.group(1)
        else:
            # Padrão 2: Maior preço encontrado (geralmente o principal)
            matches = re.findall(r'R\$\s*([\d.,]+)', html)
            valid_prices = []
            for m in matches:
                try:
                    limpo = m.replace('.', '').replace(',', '.')
                    valor = float(limpo)
                    if 50 < valor < 1000:
                        valid_prices.append(valor)
                except:
                    continue
            preco = max(valid_prices) if valid_prices else None

        # Se encontrou via regex específico
        if 'preco_str' in locals():
            limpo = preco_str.replace('.', '').replace(',', '.')
            preco = float(limpo)

        if preco is None:
            raise Exception("Preço não encontrado")

        print(f"✅ Preço capturado: R$ {preco:.2f}")

        if preco <= alvo:
            msg = f"🔥 <b>ALERTA CENTAURO!</b>\nPreço baixou para <b>R$ {preco:.2f}</b>\n\n{url_produto}"
        else:
            msg = f"✅ Monitor Centauro\nPreço atual: R$ {preco:.2f} (Alvo: R$ {alvo})"
        
        enviar_telegram(token, chat_id, msg)

    except Exception as e:
        erro = str(e)[:350]
        print(f"❌ Erro: {erro}")
        enviar_telegram(token, chat_id, f"❌ Erro Scrape.do:\n{erro}")

if __name__ == "__main__":
    monitor_scrapedo()
