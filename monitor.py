import os
import requests
from playwright.sync_api import sync_playwright

def monitorar_preco():
    url = "https://www.centauro.com.br/conjunto-de-agasalho-oxer-replayer-981478.html?cor=05"
    alvo = 200.00
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('CHAT_ID')

    with sync_playwright() as p:
        # Lança o navegador em modo "headless"
        browser = p.chromium.launch(headless=True)
        
        # Define um User-Agent comum para evitar bloqueios
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # Novo seletor baseado na estrutura atual da Centauro
            selector = 'div[class*="Price_bestPrice"]'
            page.wait_for_selector(selector, timeout=20000)
            texto_preco = page.locator(selector).first.inner_text()
            
            # Limpeza e conversão do preço
            limpo = texto_preco.replace("R$", "").replace(".", "").replace(",", ".").strip()
            preco = float(limpo)
            print(f"Preço capturado com sucesso: R$ {preco}")

            if preco <= alvo:
                msg = f"🔥 Alerta! Preço baixou para R$ {preco:.2f}. Link: {url}"
                response = requests.get(f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={msg}")
                print(f"Resposta do Telegram: {response.status_code} - {response.text}")
            else:
                print(f"Preço atual (R$ {preco}) é maior ou igual ao alvo (R$ {alvo}).")
        
        except Exception as e:
            print(f"Erro na execução: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    monitorar_preco()
