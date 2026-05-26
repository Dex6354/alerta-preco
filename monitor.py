import os
import re
import requests
from playwright.sync_api import sync_playwright, TimeoutError

def enviar_telegram(token, chat_id, mensagem):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": mensagem, "parse_mode": "HTML"}
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Erro ao enviar Telegram: {e}")

def monitorar_preco():
    url = "https://www.centauro.com.br/conjunto-de-agasalho-oxer-replayer-981478.html?cor=05"
    alvo = 200.00
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('CHAT_ID')

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            # === MELHORIAS IMPORTANTES ===
            page.goto(url, wait_until="networkidle", timeout=60000)  # networkidle é melhor que domcontentloaded
            page.wait_for_load_state("domcontentloaded")

            # Espera um pouco mais para o React hidratar
            page.wait_for_timeout(5000)

            # Múltiplos seletores possíveis (Centauro muda bastante)
            selectors = [
                '[data-testid="price-current"]',
                '[data-testid*="price"]',
                'span[class*="Price"]',           # comum
                'div[class*="price"]', 
                'strong[class*="price"]',
                '.price__value',                  # classe antiga
                '.product-price', 
                'span[class*="current-price"]'
            ]

            preco = None
            texto_completo = None

            for selector in selectors:
                try:
                    element = page.locator(selector).first
                    element.wait_for(timeout=8000)
                    texto_completo = element.inner_text(timeout=5000)
                    print(f"✅ Encontrado com selector: {selector}")
                    break
                except:
                    continue

            if not texto_completo:
                # Última tentativa: pegar qualquer texto com R$ próximo
                texto_completo = page.evaluate('''
                    () => {
                        const texts = Array.from(document.querySelectorAll('*'))
                            .map(el => el.textContent)
                            .filter(t => t && /R\$\s*\d/.test(t));
                        return texts[0] || '';
                    }
                ''')
                print("⚠️ Usando fallback com evaluate")

            # === EXTRAÇÃO DO PREÇO (melhorada) ===
            if texto_completo:
                # Pega o primeiro valor no formato R$ XXX,XX
                match = re.search(r'R\$\s*([\d.,]+)', texto_completo.replace('\xa0', ' '))
                if match:
                    limpo = match.group(1).replace('.', '').replace(',', '.').strip()
                    preco = float(limpo)
                else:
                    # Tenta pegar qualquer número grande (preço)
                    match = re.search(r'(\d{2,4})[.,](\d{2})', texto_completo)
                    if match:
                        limpo = match.group(1) + '.' + match.group(2)
                        preco = float(limpo)

            if preco is None:
                raise Exception("Não foi possível encontrar o preço na página.")

            print(f"Preço capturado: R$ {preco:.2f}")

            if preco <= alvo:
                msg = f"🔥 <b>Alerta Centauro!</b>\nPreço baixou para <b>R$ {preco:.2f}</b>\n\n{url}"
                enviar_telegram(token, chat_id, msg)
            else:
                msg_OK = f"✅ Monitoramento Centauro\nPreço atual: R$ {preco:.2f}\nAlvo: R$ {alvo:.2f}"
                enviar_telegram(token, chat_id, msg_OK)

        except TimeoutError:
            erro_msg = "❌ Timeout ao carregar a página da Centauro (pode estar lenta ou com proteção)"
            print(erro_msg)
            enviar_telegram(token, chat_id, erro_msg)
        except Exception as e:
            erro_msg = f"❌ Erro na automação Centauro:\n{str(e)[:200]}"
            print(erro_msg)
            enviar_telegram(token, chat_id, erro_msg)
        finally:
            browser.close()

if __name__ == "__main__":
    monitorar_preco()
