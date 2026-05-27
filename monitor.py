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
        print(f"⚠️ Erro Telegram: {e}")

def monitor_scrapedo():
    url_produto = "https://www.centauro.com.br/conjunto-de-agasalho-oxer-replayer-981478.html?cor=05"
    alvo = 200.00
    
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('CHAT_ID')
    scrape_token = "3a23ea3810a04b16bccfac96a2c3b1af73c97a98ef5"

    # ... (mantendo a parte de requisição igual à última versão) ...

    html = None
    for tentativa in range(1, 4):
        try:
            print(f"🔄 Tentativa {tentativa}/3...")
            encoded_url = quote(url_produto)
            api_url = f"https://api.scrape.do/?token={scrape_token}&url={encoded_url}&render=true"
            
            response = requests.get(api_url, timeout=90)
            print(f"   Status: {response.status_code}")

            if response.status_code == 200:
                html = response.text
                print(f"   ✅ Página carregada ({len(html):,} chars)")
                break
            elif response.status_code == 502:
                time.sleep(8 * tentativa)
                continue
        except Exception as e:
            print(f"   Erro: {e}")
            if tentativa == 3:
                raise
            time.sleep(6)

    if not html:
        raise Exception("Falha ao carregar página")

    # === MELHOR EXTRAÇÃO DE PREÇOS ===
    matches = re.findall(r'R\$\s*([\d.,]+)', html)
    
    valid_prices = []
    for m in matches:
        try:
            limpo = m.replace('.', '').replace(',', '.')
            valor = float(limpo)
            if 30 < valor < 1500:
                valid_prices.append(valor)
        except:
            continue

    unique_prices = sorted(list(set(valid_prices)))

    print("\n" + "="*70)
    print("💰 TODOS OS PREÇOS ENCONTRADOS:")
    for i, p in enumerate(unique_prices, 1):
        print(f"   {i:2d}. R$ {p:8.2f}")
    
    print("\n🔍 ANÁLISE:")

    if len(unique_prices) >= 2:
        preco_venda = min(unique_prices)        # Geralmente o menor é o preço atual
        preco_antigo = max(unique_prices)
        print(f"   → Preço de VENDA estimado: R$ {preco_venda:.2f}")
        print(f"   → Preço antigo (riscado): R$ {preco_antigo:.2f}")
        preco_principal = preco_venda
    else:
        preco_principal = max(unique_prices) if unique_prices else None
        print(f"   → Apenas um preço encontrado: R$ {preco_principal:.2f}")

    print("="*70)

    if preco_principal is None:
        raise Exception("Nenhum preço encontrado")

    # Mensagem
    if preco_principal <= alvo:
        msg = f"🔥 <b>ALERTA CENTAURO!</b>\nPreço baixou para <b>R$ {preco_principal:.2f}</b>\n\n{url_produto}"
    else:
        msg = f"✅ Monitor Centauro\nPreço atual: R$ {preco_principal:.2f} (Alvo: R$ {alvo})"
    
    enviar_telegram(token, chat_id, msg)
    print(f"\n📤 Mensagem enviada com preço: R$ {preco_principal:.2f}")

if __name__ == "__main__":
    try:
        monitor_scrapedo()
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
