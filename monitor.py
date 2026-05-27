import os
import re
import time
import requests
from urllib.parse import quote

def enviar_telegram(token, chat_id, mensagem):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": mensagem, "parse_mode": "HTML"}
        requests.post(url, json=payload, timeout=20)
    except Exception as e:
        print(f"⚠️ Erro ao enviar Telegram: {e}")

def monitor_scrapedo():
    url_produto = "https://www.centauro.com.br/conjunto-de-agasalho-oxer-replayer-981478.html?cor=05"
    alvo = 200.00
    
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('CHAT_ID')
    scrape_token = "3a23ea3810a04b16bccfac96a2c3b1af73c97a98ef5"

    html = None

    for tentativa in range(1, 4):
        try:
            print(f"🔄 Tentativa {tentativa}/3 via Scrape.do...")
            
            encoded_url = quote(url_produto)
            api_url = f"https://api.scrape.do/?token={scrape_token}&url={encoded_url}&render=true"

            response = requests.get(api_url, timeout=90)
            print(f"   Status: {response.status_code}")

            if response.status_code == 200:
                html = response.text
                print(f"   ✅ Sucesso! Tamanho da página: {len(html):,} caracteres")
                break
            elif response.status_code == 502:
                print("   502 detectado, aguardando...")
                time.sleep(8 * tentativa)
                continue
            else:
                print(f"   ❌ Status inesperado: {response.status_code}")
                if tentativa == 3:
                    raise Exception(f"Scrape.do retornou {response.status_code}")

        except requests.exceptions.ConnectionError:
            print("   ❌ Erro de conexão com Scrape.do (pode estar temporariamente indisponível)")
            if tentativa == 3:
                raise
            time.sleep(7)
        except Exception as e:
            print(f"   ❌ Erro: {e}")
            if tentativa == 3:
                raise
            time.sleep(5)

    if html is None:
        raise Exception("Não foi possível obter a página após 3 tentativas")

    # === EXTRAÇÃO DE TODOS OS PREÇOS ===
    matches = re.findall(r'R\$\s*([\d.,]+)', html)

    valid_prices = []
    for m in matches:
        try:
            limpo = m.replace('.', '').replace(',', '.')
            valor = float(limpo)
            if 30 < valor < 1500:   # faixa ampliada
                valid_prices.append(valor)
        except:
            continue

    unique_prices = sorted(list(set(valid_prices)))

    print("\n" + "="*60)
    print("💰 PREÇOS ENCONTRADOS NA PÁGINA:")
    if unique_prices:
        for i, p in enumerate(unique_prices, 1):
            print(f"   {i:2d}. R$ {p:8.2f}")
        
        preco_principal = max(unique_prices)
        print(f"\n✅ Preço principal (maior): R$ {preco_principal:.2f}")
    else:
        print("   Nenhum preço encontrado!")
        print("   HTML preview (primeiros 500 chars):")
        print(html[:500])
        raise Exception("Preço não encontrado")

    print("="*60)

    # Envio da mensagem
    if preco_principal <= alvo:
        msg = f"🔥 <b>ALERTA CENTAURO!</b>\nPreço baixou para <b>R$ {preco_principal:.2f}</b>\n\n{url_produto}"
    else:
        msg = f"✅ Monitor Centauro\nPreço atual: R$ {preco_principal:.2f} (Alvo: R$ {alvo})"
    
    enviar_telegram(token, chat_id, msg)

if __name__ == "__main__":
    try:
        monitor_scrapedo()
    except Exception as e:
        print(f"\n❌ ERRO FINAL: {e}")
        # Opcional: enviar erro por telegram
