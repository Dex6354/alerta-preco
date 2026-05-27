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
                print(f"   ✅ Página carregada ({len(html):,} caracteres)")
                break
            elif response.status_code == 502:
                print("   502 detectado, aguardando...")
                time.sleep(8 * tentativa)
                continue
            else:
                print(f"   Status inesperado: {response.status_code}")
                time.sleep(5)
        except Exception as e:
            print(f"   Erro: {e}")
            if tentativa == 3:
                raise
            time.sleep(6)

    if not html:
        raise Exception("Falha ao carregar página")

    # === EXTRAÇÃO MELHORADA DO PREÇO ===
    # Padrões mais específicos para Centauro
    matches = re.findall(r'R\$\s*([\d.,]+)', html)
    
    valid_prices = []
    for m in matches:
        try:
            limpo = m.replace('.', '').replace(',', '.')
            valor = float(limpo)
            if 50 < valor < 1500:  # faixa realista para esse produto
                valid_prices.append(valor)
        except:
            continue

    unique_prices = sorted(list(set(valid_prices)))

    print("\n" + "="*80)
    print("💰 TODOS OS PREÇOS ENCONTRADOS:")
    for i, p in enumerate(unique_prices, 1):
        print(f"   {i:2d}. R$ {p:8.2f}")
    print("="*80)

    if not unique_prices:
        raise Exception("Nenhum preço encontrado na página")

    # LÓGICA DE ESCOLHA DO PREÇO PRINCIPAL (melhorada)
    if len(unique_prices) >= 2:
        # Estratégia: 
        # 1. Procurar preço próximo a "Pix" (geralmente o mais vantajoso)
        # 2. Senão, pegar o segundo menor (evita preço muito baixo de parcela)
        # 3. Senão, pegar o menor preço razoável
        
        preco_principal = None
        
        # Tenta encontrar preço com "Pix" no contexto (melhor chance)
        pix_match = re.search(r'R\$\s*([\d.,]+).*?Pix|Pix.*?R\$\s*([\d.,]+)', html, re.IGNORECASE | re.DOTALL)
        if pix_match:
            for g in pix_match.groups():
                if g:
                    try:
                        valor_pix = float(g.replace('.', '').replace(',', '.'))
                        if 50 < valor_pix < 1500:
                            preco_principal = valor_pix
                            print(f"   ✅ Preço PIX encontrado: R$ {preco_principal:.2f}")
                            break
                    except:
                        continue
        
        if not preco_principal:
            # Se não encontrou PIX, pega o segundo menor preço (evita R$99,99 de parcela)
            if len(unique_prices) >= 2:
                preco_principal = unique_prices[1]  # segundo menor
                print(f"   → Usando segundo menor preço: R$ {preco_principal:.2f}")
            else:
                preco_principal = unique_prices[0]
    else:
        preco_principal = unique_prices[0]
        print(f"   → Apenas um preço encontrado: R$ {preco_principal:.2f}")

    print(f"\n🎯 Preço principal definido: R$ {preco_principal:.2f}")

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
