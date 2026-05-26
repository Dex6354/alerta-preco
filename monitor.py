import os
import re
import requests
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

def enviar_telegram(token, chat_id, mensagem):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": mensagem}
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Erro ao enviar mensagem para o Telegram: {e}")

def monitorar_preco():
    url = "https://www.centauro.com.br/conjunto-de-agasalho-oxer-replayer-981478.html?cor=05"
    alvo = 200.00
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('CHAT_ID')
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--window-size=1920,1080"
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="pt-BR"
        )
        page = context.new_page()
        
        # Aplica as técnicas de evasão anti-bot
        stealth_sync(page)

        try:
            page.goto(url, wait_until="load", timeout=60000)
            page.wait_for_timeout(5000) 

            titulo = page.title().lower()
            if "access denied" in titulo or "cloudflare" in titulo or "just a moment" in titulo:
                raise Exception("Bloqueado pelo sistema Anti-Bot da loja.")

            seletores = [
                '[data-testid="price-current"]',
                '.price-current',
                '[class*="Price"]',
                'span:has-text("R$")'
            ]
            
            texto_completo = None
            for seletor in seletores:
                try:
                    if page.locator(seletor).first.is_visible():
                        texto_completo = page.locator(seletor).first.inner_text()
                        break
                except:
                    continue

            if not texto_completo:
                raise Exception("Não foi possível localizar o elemento de preço na página.")

            match = re.search(r'(?:R\$\s*)?([\d\.]+,\d{2})', texto_completo)
            if not match:
                raise Exception(f"Padrão de preço não encontrado no texto: {texto_completo}")
                
            texto_preco = match.group(1)
            limpo = texto_preco.replace(".", "").replace(",", ".").strip()
            preco = float(limpo)
            
            print(f"Preço capturado com sucesso: R$ {preco}")
            
            if preco <= alvo:
                msg = f"🔥 Alerta! Preço baixou para R$ {preco:.2f}.\nLink: {url}"
                enviar_telegram(token, chat_id, msg)
            else:
                msg_OK = f"✅ Monitoramento ativo. Preço atual: R$ {preco:.2f} (Alvo: R$ {alvo:.2f})"
                enviar_telegram(token, chat_id, msg_OK)
        
        except Exception as e:
            erro_msg = f"❌ Erro na automação Centauro:\n{str(e)[:150]}"
            print(erro_msg)
            enviar_telegram(token, chat_id, erro_msg)
        finally:
            browser.close()

if __name__ == "__main__":
    monitorar_preco()
