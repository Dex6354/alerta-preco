import os
import re
import random
import requests
from playwright.sync_api import sync_playwright

def enviar_telegram(token, chat_id, mensagem):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": mensagem, "parse_mode": "HTML"}
        requests.post(url, json=payload, timeout=15)
    except:
        pass

# Lista de proxies gratuitos (atualizada manualmente - substitua quando morrerem)
FREE_PROXIES = [
    "http://168.205.255.238:80",      # BR
    "http://177.93.72.82:4153",       # BR
    "http://201.71.24.65:8082",       # BR
    # Adicione mais de https://databay.com/free-proxy-list/brazil se quiser
]

def get_random_proxy():
    return random.choice(FREE_PROXIES) if FREE_PROXIES else None

def monitor_com_proxy_gratis():
    url = "https://www.centauro.com.br/conjunto-de-agasalho-oxer-replayer-981478.html?cor=05"
    alvo = 200.00
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('CHAT_ID')

    proxy = get_random_proxy()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])

        context_options = {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
            "viewport": {"width": 1366, "height": 768},
            "locale": "pt-BR",
        }

        if proxy:
            context_options["proxy"] = {"server": proxy}

        context = browser.new_context(**context_options)

        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)

        page = context.new_page()

        try:
            print(f"🔄 Usando proxy: {proxy}")
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(12000)

            title = page.title()
            print(f"Título: {title}")

            if "Access Denied" in title or "Cloudflare" in title:
                raise Exception("Bloqueado pelo Cloudflare")

            # Extrai preço
            price_texts = page.evaluate('''
                () => Array.from(document.querySelectorAll('*'))
                    .map(el => el.textContent.trim())
                    .filter(t => /R\$\s*\d/.test(t))
                    .slice(0, 10)
            ''')

            full_text = " ".join(price_texts)
            match = re.search(r'R\$\s*([\d.,]+)', full_text)

            if match:
                limpo = match.group(1).replace('.', '').replace(',', '.')
                preco = float(limpo)
                print(f"✅ Preço encontrado: R$ {preco}")

                if preco <= alvo:
                    msg = f"🔥 <b>ALERTA!</b> Preço baixou para R$ {preco:.2f}\n\n{url}"
                else:
                    msg = f"✅ Preço atual: R$ {preco:.2f} (Alvo: R$ {alvo})"
                enviar_telegram(token, chat_id, msg)
            else:
                raise Exception("Preço não encontrado na página")

        except Exception as e:
            erro = str(e)[:250]
            print(f"Erro: {erro}")
            enviar_telegram(token, chat_id, f"❌ Erro com proxy gratuito:\n{erro}\nProxy usado: {proxy}")
        finally:
            browser.close()

if __name__ == "__main__":
    monitor_com_proxy_gratis()
