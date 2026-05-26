import os
import re
import json
import requests
from playwright.sync_api import sync_playwright

def enviar_telegram(token, chat_id, mensagem):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": mensagem}
        response = requests.post(url, json=payload, timeout=10)
        print(f"Status do Telegram: {response.status_code}")
    except Exception as e:
        print(f"Erro ao enviar mensagem para o Telegram: {e}")

def monitorar_preco():
    url = "https://www.centauro.com.br/conjunto-de-agasalho-oxer-replayer-981478.html?cor=05"
    alvo = 200.00
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('CHAT_ID')

    if not token or not chat_id:
        print("Erro: TELEGRAM_TOKEN ou CHAT_ID não configurados nas Secrets.")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            # Acessa a página sem esperar scripts pesados anti-bot
            page.goto(url, wait_until="commit", timeout=60000)
            
            # Busca os dados estruturados (NextJS) para evitar bloqueio visual
            script_tag = page.locator("script#__NEXT_DATA__")
            if script_tag.count() > 0:
                html_content = script_tag.inner_html()
                dados = json.loads(html_content)
                produto = dados['props']['pageProps']['initialState']['product']['currentProduct']
                preco = float(produto['skus'][0]['offers']['lowPrice'])
            else:
                # Alternativa via Regex se o script não carregar
                content = page.content()
                match = re.search(r'"lowPrice":\s*([0-9.]+)', content)
                if match:
                    preco = float(match.group(1))
                else:
                    raise Exception("A Centauro bloqueou o acesso ao preço estruturado.")
            
            print(f"Preço capturado: R$ {preco}")
            
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
