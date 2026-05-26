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

def debug_preco():
    url = "https://www.centauro.com.br/conjunto-de-agasalho-oxer-replayer-981478.html?cor=05"
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('CHAT_ID')

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            print("🔄 Acessando a página...")
            page.goto(url, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(8000)  # Espera hidratação do React

            print("\n📋 === DEBUGGER - INFORMAÇÕES DA PÁGINA ===")

            # 1. Título da página
            title = page.title()
            print(f"Título: {title}")

            # 2. Busca por textos com preço
            print("\n💰 Textos com R$ encontrados:")
            price_texts = page.evaluate('''
                () => {
                    return Array.from(document.querySelectorAll('*'))
                        .map(el => el.textContent.trim())
                        .filter(text => text.includes('R$') && /\d/.test(text))
                        .slice(0, 15);
                }
            ''')
            for i, text in enumerate(price_texts, 1):
                print(f"{i:2d}. {text}")

            # 3. Elementos com "price" no nome da classe ou data-testid
            print("\n🏷️ Elementos com 'price' ou 'preco' no atributo:")
            elements = page.evaluate('''
                () => {
                    const els = document.querySelectorAll('[class*="price"], [class*="Price"], [data-testid*="price"], [data-testid*="Price"]');
                    return Array.from(els).map(el => ({
                        tag: el.tagName,
                        class: el.className,
                        dataTestId: el.getAttribute('data-testid'),
                        text: el.textContent.trim().substring(0, 80)
                    }));
                }
            ''')
            for el in elements:
                print(f"• <{el['tag']}> | class: {el['class'][:80]} | data-testid: {el['dataTestId']} | text: {el['text']}")

            # 4. Tentativa automática de extrair preço
            print("\n🔍 Tentando extrair preço...")
            body_text = page.content()
            matches = re.findall(r'R\$\s*[\d.,]+', body_text)
            if matches:
                print(f"✅ Matches encontrados: {matches[:5]}")
            else:
                print("❌ Nenhum R$ encontrado no HTML")

            # Envia tudo no Telegram para você analisar
            debug_msg = f"""
🛠️ <b>DEBUG Centauro</b>

Título: {title}

Preços encontrados:
{chr(10).join([f"{i}. {t}" for i,t in enumerate(price_texts[:8],1)])}

Elementos price: {len(elements)} encontrados
            """.strip()

            enviar_telegram(token, chat_id, debug_msg)
            print("\n✅ Debug enviado para o Telegram!")

        except Exception as e:
            print(f"Erro: {e}")
            enviar_telegram(token, chat_id, f"❌ Erro no Debugger:\n{str(e)[:300]}")
        finally:
            browser.close()

if __name__ == "__main__":
    debug_preco()
