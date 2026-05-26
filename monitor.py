import os
import requests

def enviar_telegram(token, chat_id, mensagem):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": mensagem}
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Erro ao enviar mensagem para o Telegram: {e}")

def monitorar_preco():
    # URL do produto para o alerta e ID do produto na API da Centauro
    url_produto = "https://www.centauro.com.br/conjunto-de-agasalho-oxer-replayer-981478.html?cor=05"
    id_produto = "981478"
    
    alvo = 200.00
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('CHAT_ID')

    # Endpoint da API interna que a Centauro usa para renderizar os preços
    api_url = f"https://api.centauro.com.br/v2/products/{id_produto}"
    
    # Headers para simular uma requisição limpa do navegador
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }

    try:
        response = requests.get(api_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            dados = response.json()
            
            # Navega pelo JSON para encontrar o menor preço disponível (geralmente o preço à vista/Pix)
            preco = float(dados['offers']['lowPrice'])
            print(f"Preço capturado via API: R$ {preco}")
            
            if preco <= alvo:
                msg = f"🔥 Alerta! Preço baixou para R$ {preco:.2f}.\nLink: {url_produto}"
                enviar_telegram(token, chat_id, msg)
            else:
                msg_OK = f"✅ Monitoramento ativo. Preço atual: R$ {preco:.2f} (Alvo: R$ {alvo:.2f})"
                enviar_telegram(token, chat_id, msg_OK)
        else:
            raise Exception(f"API da Centauro retornou status {response.status_code}")

    except Exception as e:
        erro_msg = f"❌ Erro na automação Centauro:\n{str(e)[:150]}"
        print(erro_msg)
        enviar_telegram(token, chat_id, erro_msg)

if __name__ == "__main__":
    monitorar_preco()
