import os
import requests
from playwright.sync_api import sync_playwright

def monitorar_preco():
    url = "https://www.centauro.com.br/conjunto-de-agasalho-oxer-replayer-981478.html?cor=05"
    alvo = 200.00
    token = os.environ['TELEGRAM_TOKEN']
    chat_id = os.environ['CHAT_ID']

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        
        # Seletor do preço na Centauro
        element = page.locator(".price-best-price").first
        texto_preco = element.inner_text()
        
        # Limpeza do texto: "R$ 189,99" -> 189.99
        preco = float(texto_preco.replace("R$", "").replace(".", "").replace(",", ".").strip())
        browser.close()

        if preco <= alvo:
            msg = f"🔥 Alerta! Preço baixou para R$ {preco}. Link: {url}"
            requests.get(f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={msg}")

if __name__ == "__main__":
    monitorar_preco()
