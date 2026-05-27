import os
import re
import json
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

def extrair_preco(html):
    """
    Tenta extrair o preço principal em ordem de confiabilidade:
    1. JSON-LD (dado estruturado — mais confiável)
    2. Preço próximo à palavra "Pix" (segundo mais confiável)
    3. Heurística: segundo menor preço válido (ignora fretes/centavos)
    """

    # --- Estratégia 1: JSON-LD ---
    for script in re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.DOTALL | re.IGNORECASE):
        try:
            data = json.loads(script)
            # Pode ser uma lista ou um único objeto
            if isinstance(data, list):
                data = data[0]
            offers = data.get("offers", {})
            if isinstance(offers, list):
                offers = offers[0]
            price = offers.get("price") or offers.get("lowPrice")
            if price:
                valor = float(str(price).replace(',', '.'))
                if 50 < valor < 1500:
                    print(f"   ✅ [JSON-LD] Preço encontrado: R$ {valor:.2f}")
                    return valor
        except Exception as e:
            continue

    # --- Estratégia 2: Preço próximo à palavra "Pix" ---
    # Captura R$ XXX que aparece perto de "Pix" no HTML (até ~200 chars de distância)
    pix_match = re.search(
        r'R\$\s*([\d.,]+)(?:[\s\S]{0,200}?)(?:no\s+)?[Pp]ix|(?:no\s+)?[Pp]ix(?:[\s\S]{0,200}?)R\$\s*([\d.,]+)',
        html
    )
    if pix_match:
        raw = pix_match.group(1) or pix_match.group(2)
        try:
            valor = float(raw.replace('.', '').replace(',', '.'))
            if 50 < valor < 1500:
                print(f"   ✅ [Pix-regex] Preço encontrado: R$ {valor:.2f}")
                return valor
        except:
            pass

    # --- Estratégia 3: Heurística com todos os preços da página ---
    matches = re.findall(r'R\$\s*([\d.,]+)', html)
    valid_prices = []
    for m in matches:
        try:
            valor = float(m.replace('.', '').replace(',', '.'))
            if 50 < valor < 1500:
                valid_prices.append(valor)
        except:
            continue

    unique_prices = sorted(set(valid_prices))
    print(f"   ℹ️ [Heurística] Preços válidos encontrados: {unique_prices}")

    if not unique_prices:
        return None

    if len(unique_prices) == 1:
        return unique_prices[0]

    # Ignora o menor (frequentemente frete/acessório barato)
    # e o maior (frequentemente preço riscado/original)
    # Pega o segundo menor como preço atual de venda
    preco = unique_prices[1] if len(unique_prices) >= 2 else unique_prices[0]
    print(f"   ✅ [Heurística] Preço estimado: R$ {preco:.2f}")
    return preco


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
            print(f"   Status HTTP: {response.status_code}")

            if response.status_code == 200:
                html = response.text
                print(f"   ✅ Página carregada ({len(html):,} chars)")
                break
            elif response.status_code == 502:
                print("   ⚠️ 502 — aguardando antes de retry...")
                time.sleep(8 * tentativa)
                continue
            else:
                raise Exception(f"Scrape.do retornou {response.status_code}")

        except Exception as e:
            print(f"   ❌ Erro: {e}")
            if tentativa == 3:
                raise
            time.sleep(6)

    if not html:
        raise Exception("Falha ao carregar a página após 3 tentativas")

    print("\n" + "=" * 60)
    print("🔍 EXTRAINDO PREÇO...")
    preco = extrair_preco(html)
    print("=" * 60)

    if preco is None:
        raise Exception("Nenhum preço válido encontrado na página")

    print(f"\n💰 Preço final: R$ {preco:.2f} | Alvo: R$ {alvo:.2f}")

    if preco <= alvo:
        msg = (
            f"🔥 <b>ALERTA CENTAURO!</b>\n"
            f"Preço baixou para <b>R$ {preco:.2f}</b>\n\n"
            f"{url_produto}"
        )
    else:
        msg = (
            f"✅ Monitor Centauro\n"
            f"Preço atual: R$ {preco:.2f} (Alvo: R$ {alvo:.2f})"
        )

    enviar_telegram(token, chat_id, msg)
    print(f"📤 Mensagem enviada!")


if __name__ == "__main__":
    try:
        monitor_scrapedo()
    except Exception as e:
        print(f"\n❌ ERRO FATAL: {e}")
