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

def debug_stealth_v2():
    url = "https://www.centauro.com.br/conjunto-de-agasalho-oxer-replayer-981478.html?cor=05"
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('CHAT_ID')

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--disable-extensions',
                '--disable-gpu',
                '--disable-setuid-sandbox',
            ]
        )

        context = browser.new_context(
            user_agent=random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
            ]),
            viewport={"width": random.randint(1200, 1400), "height": random.randint(700, 900)},
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            permissions=["geolocation"]
        )

        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['pt-BR', 'pt', 'en']});
            Object.defineProperty(window, 'chrome', {get: () => ({ runtime: {} })});
        """)

        page = context.new_page()

        try:
            print("🔄 Tentando acessar com stealth máximo...")
            page.goto(url, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(random.randint(8000, 15000))

            title = page.title()
            print(f"Título: {title}")

            # Captura mais agressiva de textos
            price_texts = page.evaluate('''
                () => Array.from(document.querySelectorAll('*'))
                    .map(el => el.textContent.trim())
                    .filter(t => /R\$\s*\d|[Pp]reço|price/i.test(t))
                    .slice(0, 15)
            ''')

            print("\n💰 Textos encontrados:")
            for i, text in enumerate(price_texts, 1):
                print(f"{i}. {text[:100]}")

            if title == "Access Denied" or "cloudflare" in title.lower():
                raise Exception("Ainda bloqueado pelo Cloudflare")

            # Se chegou aqui, tenta extrair preço
            match = re.search(r'R\$\s*([\d.,]+)', ' '.join(price_texts))
            if match:
                preco_str = match.group(1).replace('.', '').replace(',', '.')
                preco = float(preco_str)
                print(f"✅ Preço encontrado: R$ {preco}")
            else:
                preco = None

            # Envia resultado
            msg = f"""
🛠️ <b>DEBUG STEALTH V2</b>

Título: {title}

Textos com preço:
{chr(10).join([f"{i}. {t[:80]}" for i,t in enumerate(price_texts[:6],1)]) if price_texts else "Nenhum"}
            """.strip()
            enviar_telegram(token, chat_id, msg)

        except Exception as e:
            erro = str(e)[:500]
            print(f"Erro: {erro}")
            enviar_telegram(token, chat_id, f"❌ Ainda bloqueado:\n{erro}")
        finally:
            browser.close()

if __name__ == "__main__":
    debug_stealth_v2()
