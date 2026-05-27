import os
import re
import json
import time
import requests
from urllib.parse import quote

# ─── Produtos monitorados ────────────────────────────────────────────────────
PRODUTOS = [
    {
        "nome": "Conjunto Agasalho Oxer Replayer",
        "url": "https://www.centauro.com.br/conjunto-de-agasalho-oxer-replayer-981478.html?cor=05",
        "alvo": 200.00,
    },
    {
        "nome": "Regata Oxer Respirabilidade",
        "url": "https://www.centauro.com.br/regata-oxer-regata-respirabilidade-mas-984829.html?cor=83",
        "alvo": 80.00,
    },
]

SCRAPE_TOKEN = "3a23ea3810a04b16bccfac96a2c3b1af73c97a98ef5"

HEADERS_DIRETO = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

MAX_SCRAPE_CALLS = 5   # limite de chamadas pagas por item


# ─── Telegram ────────────────────────────────────────────────────────────────
def enviar_telegram(token, chat_id, mensagem):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": mensagem, "parse_mode": "HTML"}
        requests.post(url, json=payload, timeout=20)
    except Exception as e:
        print(f"⚠️ Erro Telegram: {e}")


# ─── Extração de preço ───────────────────────────────────────────────────────
def extrair_preco(html):
    """
    1. JSON-LD  (mais confiável)
    2. Regex próximo a "Pix"
    3. Heurística: segundo menor preço válido
    """
    # Estratégia 1: JSON-LD
    for script in re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.DOTALL | re.IGNORECASE
    ):
        try:
            data = json.loads(script)
            if isinstance(data, list):
                data = data[0]
            offers = data.get("offers", {})
            if isinstance(offers, list):
                offers = offers[0]
            price = offers.get("price") or offers.get("lowPrice")
            if price:
                valor = float(str(price).replace(',', '.'))
                if 10 < valor < 5000:
                    print(f"   ✅ [JSON-LD] R$ {valor:.2f}")
                    return valor
        except Exception:
            continue

    # Estratégia 2: Pix
    pix_match = re.search(
        r'R\$\s*([\d.,]+)(?:[\s\S]{0,200}?)(?:no\s+)?[Pp]ix'
        r'|(?:no\s+)?[Pp]ix(?:[\s\S]{0,200}?)R\$\s*([\d.,]+)',
        html
    )
    if pix_match:
        raw = pix_match.group(1) or pix_match.group(2)
        try:
            valor = float(raw.replace('.', '').replace(',', '.'))
            if 10 < valor < 5000:
                print(f"   ✅ [Pix-regex] R$ {valor:.2f}")
                return valor
        except Exception:
            pass

    # Estratégia 3: Heurística
    matches = re.findall(r'R\$\s*([\d.,]+)', html)
    valid_prices = []
    for m in matches:
        try:
            valor = float(m.replace('.', '').replace(',', '.'))
            if 10 < valor < 5000:
                valid_prices.append(valor)
        except Exception:
            continue

    unique_prices = sorted(set(valid_prices))
    print(f"   ℹ️ [Heurística] Preços válidos: {unique_prices}")

    if not unique_prices:
        return None
    if len(unique_prices) == 1:
        return unique_prices[0]

    preco = unique_prices[1] if len(unique_prices) >= 2 else unique_prices[0]
    print(f"   ✅ [Heurística] R$ {preco:.2f}")
    return preco


# ─── Busca de HTML com fallback em camadas ────────────────────────────────────
def buscar_html(url_produto):
    """
    Camada 0: requisição direta (gratuita, sem scrape.do).
    Camada 1: scrape.do sem render (barata).
    Camada 2: scrape.do com render=true (cara).

    Cada camada tenta até 2 vezes antes de avançar.
    Total máximo de chamadas pagas: MAX_SCRAPE_CALLS.
    Retorna (html, scrape_calls_usadas) ou lança exceção.
    """
    encoded_url = quote(url_produto)
    scrape_calls = 0

    # ── Camada 0: requisição direta ──────────────────────────────────────────
    print("🌐 Camada 0: requisição direta (sem scrape.do)...")
    for tentativa in range(1, 3):
        try:
            resp = requests.get(url_produto, headers=HEADERS_DIRETO, timeout=30)
            print(f"   Status: {resp.status_code} | {len(resp.text):,} chars")
            if resp.status_code == 200 and len(resp.text) > 5_000:
                preco = extrair_preco(resp.text)
                if preco is not None:
                    print("   ✅ Preço obtido na camada 0 (gratuita)")
                    return resp.text, scrape_calls
                print("   ⚠️ Página carregada mas sem preço — avançando camada")
                break   # não adianta tentar de novo sem JS
        except Exception as e:
            print(f"   ❌ Tentativa {tentativa}: {e}")
            time.sleep(3)

    # ── Camada 1: scrape.do sem render ───────────────────────────────────────
    print("\n🔧 Camada 1: scrape.do sem render...")
    for tentativa in range(1, 3):
        if scrape_calls >= MAX_SCRAPE_CALLS:
            break
        try:
            api_url = f"https://api.scrape.do/?token={SCRAPE_TOKEN}&url={encoded_url}"
            resp = requests.get(api_url, timeout=60)
            scrape_calls += 1
            print(f"   Status: {resp.status_code} | chamadas pagas: {scrape_calls}")
            if resp.status_code == 200 and len(resp.text) > 5_000:
                preco = extrair_preco(resp.text)
                if preco is not None:
                    print("   ✅ Preço obtido na camada 1")
                    return resp.text, scrape_calls
                print("   ⚠️ Sem preço sem render — avançando camada")
                break
            elif resp.status_code == 502:
                print(f"   ⚠️ 502 — aguardando {6 * tentativa}s...")
                time.sleep(6 * tentativa)
        except Exception as e:
            print(f"   ❌ Tentativa {tentativa}: {e}")
            time.sleep(4)

    # ── Camada 2: scrape.do com render=true ──────────────────────────────────
    print("\n🚀 Camada 2: scrape.do com render=true...")
    for tentativa in range(1, MAX_SCRAPE_CALLS + 1):
        if scrape_calls >= MAX_SCRAPE_CALLS:
            break
        try:
            api_url = (
                f"https://api.scrape.do/?token={SCRAPE_TOKEN}"
                f"&url={encoded_url}&render=true"
            )
            resp = requests.get(api_url, timeout=90)
            scrape_calls += 1
            print(f"   Status: {resp.status_code} | chamadas pagas: {scrape_calls}")
            if resp.status_code == 200:
                print(f"   ✅ Página renderizada ({len(resp.text):,} chars)")
                return resp.text, scrape_calls
            elif resp.status_code == 502:
                print(f"   ⚠️ 502 — aguardando {8 * tentativa}s...")
                time.sleep(8 * tentativa)
            else:
                raise Exception(f"scrape.do retornou {resp.status_code}")
        except Exception as e:
            print(f"   ❌ Tentativa {tentativa}: {e}")
            if scrape_calls < MAX_SCRAPE_CALLS:
                time.sleep(6)

    raise Exception(
        f"Falha ao carregar a página após {scrape_calls} chamada(s) pagas"
    )


# ─── Monitor principal ────────────────────────────────────────────────────────
def monitor_produto(produto, token, chat_id):
    nome = produto["nome"]
    url  = produto["url"]
    alvo = produto["alvo"]

    print(f"\n{'=' * 60}")
    print(f"📦 {nome}")
    print(f"🎯 Alvo: R$ {alvo:.2f}")
    print(f"{'=' * 60}")

    html, scrape_calls = buscar_html(url)

    print(f"\n🔍 EXTRAINDO PREÇO... (chamadas pagas usadas: {scrape_calls})")
    preco = extrair_preco(html)

    if preco is None:
        raise Exception("Nenhum preço válido encontrado na página")

    print(f"\n💰 Preço final: R$ {preco:.2f} | Alvo: R$ {alvo:.2f}")

    if preco <= alvo:
        msg = (
            f"🔥 <b>ALERTA CENTAURO!</b>\n"
            f"<b>{nome}</b>\n"
            f"Preço baixou para <b>R$ {preco:.2f}</b> (alvo: R$ {alvo:.2f})\n\n"
            f"{url}"
        )
    else:
        msg = (
            f"✅ Monitor Centauro — {nome}\n"
            f"Preço atual: R$ {preco:.2f} (Alvo: R$ {alvo:.2f})"
        )

    enviar_telegram(token, chat_id, msg)
    print(f"📤 Mensagem enviada!")


def main():
    token   = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('CHAT_ID')

    erros = []
    for produto in PRODUTOS:
        try:
            monitor_produto(produto, token, chat_id)
        except Exception as e:
            print(f"\n❌ ERRO em '{produto['nome']}': {e}")
            erros.append((produto["nome"], str(e)))

    if erros:
        print(f"\n⚠️ {len(erros)} produto(s) com erro:")
        for nome, err in erros:
            print(f"   • {nome}: {err}")


if __name__ == "__main__":
    main()
