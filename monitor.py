import os
import requests
from playwright.sync_api import sync_playwright

def monitorar_preco():
    url = "https://www.centauro.com.br/conjunto-de-agasalho-oxer-replayer-981478.html?cor=05"
    alvo = 200.00
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('CHAT_ID')

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=60000)
            
            # Seletor CSS atualizado para o preço principal
            selector = "span.price-best-price__final"
            page.wait_for_selector(selector, timeout=20000)
            texto_preco = page.locator(selector).first.inner_text()
            
            # Limpeza: remove "R$", espaços, substitui ponto por nada e vírgula por ponto
            limpo = texto_preco.replace("R$", "").replace(".", "").replace(",", ".").strip()
            preco = float(limpo)
            print(f"Preço capturado: {preco}")

            if preco <= alvo:
                msg = f"🔥 Alerta! Preço baixou para R$ {preco:.2f}. Link: {url}"
                requests.get(f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={msg}")
        
        except Exception as e:
            print(f"Erro na execução: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    monitorar_preco()
