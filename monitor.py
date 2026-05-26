import os
import re
import requests
from playwright.sync_api import sync_playwright

def enviar_telegram(token, chat_id, mensagem):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": mensagem, "parse_mode": "HTML"}
        requests.post(url, json=payload, timeout=15)
    except Exception as e:
        print(f"Erro Telegram: {e}")

def debug_preco_stealth():
    url = "https://www.centauro.com.br/conjunto-de-agasalho-oxer-replayer-981478.html?cor=05"
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('CHAT_ID')

    with sync_playwright() as p:
        # === STEALTH CONFIGURAÇÕES ===
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--disable-infobars',
                '--disable-extensions',
                '--disable-gpu',
            ]
        )

        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768},
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
        )

        # Remover flags de automação
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['pt-BR', 'pt']});
        """)

        page = context.new_page()

        try:
            print("🔄 Acessando com Stealth...")
            page.goto(url, wait_until="networkidle", timeout=90000)
            page.wait_for_timeout(10000)  # Mais tempo para passar desafio

            print("\n📋 === DEBUGGER STEALTH ===")
            
            title = page.title()
            print(f"Título: {title}")

            # Textos com preço
            price_texts = page.evaluate('''
                () => Array.from(document.querySelectorAll('*'))
                    .map(el => el.textContent.trim())
                    .filter(t => /R\$\s*\d/.test(t))
                    .slice(0, 12)
            ''')
            
            print("\n💰 Textos com R$ encontrados:")
            for i, text in enumerate(price_texts, 1):
                print(f"{i:2d}. {text}")

            # Elementos price
            elements = page.evaluate('''
                () => {
                    const els = document.querySelectorAll('[class*="price"], [class*="Price"], [data-testid*="price"]');
                    return Array.from(els).slice(0, 10).map(el => ({
                        tag: el.tagName,
                        class: el.className.substring(0, 100),
                        text: el.textContent.trim().substring(0, 60)
                    }));
                }
            ''')

            print(f"\n🏷️ Elementos com 'price': {len(elements)} encontrados")

            # Envia relatório
            debug_msg = f"""
🛠️ <b>DEBUG STEALTH Centauro</b>

Título: {title}

Preços encontrados:
{chr(10).join([f"{i}. {t}" for i,t in enumerate(price_texts[:8],1)]) if price_texts else "Nenhum"}

Elementos price: {len(elements)}
            """.strip()

            enviar_telegram(token, chat_id, debug_msg)
            print("✅ Debug enviado!")

        except Exception as e:
            erro = str(e)[:400]
            print(f"Erro: {erro}")
            enviar_telegram(token, chat_id, f"❌ Erro no Stealth Debug:\n{erro}")
        finally:
            browser.close()

if __name__ == "__main__":
    debug_preco_stealth()
