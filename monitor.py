import os
import requests
from playwright.sync_api import sync_playwright

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
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            # Carrega a página aguardando o HTML principal carregar
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # Alvo exato com base no HTML que você enviou
            selector = '[data-testid="price-current"]'
            page.wait_for_selector(selector, timeout=20000)
            
            # Captura o texto de dentro da tag (ex: "R$ 189,99 no Pix-5%")
            texto_completo = page.locator(selector).first.inner_text()
            
            # Isola apenas a parte do preço pegando o que vem antes da palavra "no"
            texto_preco = texto_completo.split("no")[0]
            
            # Limpa o texto: remove "R$", pontos e troca vírgula por ponto
            limpo = texto_preco.replace("R$", "").replace(".", "").replace(",", ".").strip()
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
