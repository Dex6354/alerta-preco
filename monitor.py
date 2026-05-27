import os
import re
import time
import requests
from urllib.parse import quote

def enviar_telegram(token, chat_id, mensagem):
    try:
        if not token or not chat_id:
            print("⚠️ Token ou Chat ID do Telegram ausentes nas variáveis de ambiente.")
            return
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

    # === EXTRAÇÃO INTELIGENTE DO PREÇO ===
    preco_principal = None

    # 1. Tenta extrair da tag meta oficial (Schema/OpenGraph)
    meta_price = re.search(r'(?:property|itemprop)="?(?:product:)?price:?amount"?\s+content="?([\d.]+)"?', html, re.IGNORECASE)
    if meta_price:
        try:
            preco_principal = float(meta_price.group(1))
            print("   → Preço encontrado na meta tag.")
        except:
            pass

    # 2. Busca contextual: verifica se a palavra "pix" está próxima do valor
    if not preco_principal:
        for match in re.finditer(r'R\$\s*([\d.,]+)', html):
            fim = match.end()
            contexto = html[fim:fim+80].lower()
            if 'pix' in contexto:
                try:
                    preco_principal = float(match.group(1).replace('.', '').replace(',', '.'))
                    print("   → Preço encontrado com contexto 'Pix'.")
                    break
                except:
                    continue

    # 3. Busca contextual: preço total antes das parcelas (ex: "ou R$ X em Yx")
    if not preco_principal:
        for match in re.finditer(r'R\$\s*([\d.,]+)', html):
            fim = match.end()
            contexto = html[fim:fim+80].lower()
            if 'em ' in contexto and 'x' in contexto:
                try:
                    preco_principal = float(match.group(1).replace('.', '').replace(',', '.'))
                    print("   → Preço encontrado com contexto de parcelamento.")
                    break
                except:
                    continue

    # 4. Busca em JSON-LD (Schema interno)
    if not preco_principal:
        json_match = re.search(r'"price":\s*"?(\d+\.\d{2})"?', html)
        if json_match:
            preco_principal = float(json_match.group(1))
            print("   → Preço encontrado no JSON-LD.")

    # 5. Último recurso: filtra extremos (ignora preço original de 299 e parcelas pequenas)
    if not preco_principal:
        matches = re.findall(r'R\$\s*([\d.,]+)', html)
        valid_prices = []
        for m in matches:
            try:
                v = float(m.replace('.', '').replace(',', '.'))
                if 120 < v < 290:  # Faixa lógica para o preço atual
                    valid_prices.append(v)
            except:
                continue
        if valid_prices:
            preco_principal = min(set(valid_prices))
            print("   → Preço estimado por filtragem lógica.")

    if preco_principal is None:
        raise Exception("Nenhum preço válido encontrado no HTML.")

    print("\n" + "="*70)
    print(f"✅ PREÇO FINAL DETECTADO: R$ {preco_principal:.2f}")
    print("="*70)

    # Mensagem
    if preco_principal <= alvo:
        msg = f"🔥 <b>ALERTA CENTAURO!</b>\nPreço baixou para <b>R$ {preco_principal:.2f}</b>\n\n{url_produto}"
    else:
        msg = f"✅ Monitor Centauro\nPreço atual: R$ {preco_principal:.2f} (Alvo: R$ {alvo})"
    
    enviar_telegram(token, chat_id, msg)
    print(f"\n📤 Mensagem enviada com sucesso.")

if __name__ == "__main__":
    try:
        monitor_scrapedo()
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
