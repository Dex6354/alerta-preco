import os
import re
import json
import time
import requests
from urllib.parse import quote

# ============================================================
# PRODUTOS MONITORADOS
# ============================================================
PRODUTOS = [
    {
        "nome": "Agasalho Oxer Replayer",
        "url": "https://www.centauro.com.br/conjunto-de-agasalho-oxer-replayer-981478.html?cor=05",
        "alvo": 180.00,
    },
    {
        "nome": "Regata Oxer Respirabilidade",
        "url": "https://www.centauro.com.br/regata-oxer-regata-respirabilidade-mas-984829.html?cor=83",
        "alvo": 80.00,
    },
]
# ============================================================

SCRAPE_TOKEN = "3a23ea3810a04b16bccfac96a2c3b1af73c97a98ef5"


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
    2. Preço próximo à palavra "Pix"
    3. Heurística: segundo menor preço válido
    """

    # --- Estratégia 1: JSON-LD ---
    for script in re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.DOTALL | re.IGNORECASE,
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
                valor = float(str(price).replace(",", "."))
                if 10 < valor < 1500:
                    print(f"   ✅ [JSON-LD] Preço encontrado: R$ {valor:.2f}")
                    return valor
        except Exception:
            continue

    # --- Estratégia 2: Preço próximo à palavra "Pix" ---
    pix_match = re.search(
        r'R\$\s*([\d.,]+)(?:[\s\S]{0,200}?)(?:no\s+)?[Pp]ix'
        r'|(?:no\s+)?[Pp]ix(?:[\s\S]{0,200}?)R\$\s*([\d.,]+)',
        html,
    )
    if pix_match:
        raw = pix_match.group(1) or pix_match.group(2)
        try:
            valor = float(raw.replace(".", "").replace(",", "."))
            if 10 < valor < 1500:
                print(f"   ✅ [Pix-regex] Preço encontrado: R$ {valor:.2f}")
                return valor
        except Exception:
            pass

    # --- Estratégia 3: Heurística ---
    matches = re.findall(r'R\$\s*([\d.,]+)', html)
    valid_prices = []
    for m in matches:
        try:
            valor = float(m.replace(".", "").replace(",", "."))
            if 10 < valor < 1500:
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
    print(f"   ✅ [Heurística] Preço estimado: R$ {preco:.2f}")
    return preco


def buscar_html(url):
    """Faz a requisição via Scrape.do com até 3 tentativas."""
    for tentativa in range(1, 4):
        try:
            print(f"   🔄 Tentativa {tentativa}/3...")
            encoded_url = quote(url)
            api_url = f"https://api.scrape.do/?token={SCRAPE_TOKEN}&url={encoded_url}&render=true"

            response = requests.get(api_url, timeout=90)
            print(f"      Status HTTP: {response.status_code}")

            if response.status_code == 200:
                print(f"      ✅ Página carregada ({len(response.text):,} chars)")
                return response.text
            elif response.status_code == 502:
                print("      ⚠️ 502 — aguardando antes de retry...")
                time.sleep(8 * tentativa)
                continue
            else:
                raise Exception(f"Scrape.do retornou {response.status_code}")

        except Exception as e:
            print(f"      ❌ Erro: {e}")
            if tentativa == 3:
                raise
            time.sleep(6)

    raise Exception("Falha ao carregar a página após 3 tentativas")


def monitorar_produto(produto, token, chat_id):
    nome = produto["nome"]
    url  = produto["url"]
    alvo = produto["alvo"]

    print(f"\n{'='*60}")
    print(f"📦 {nome}")
    print(f"   Alvo: R$ {alvo:.2f}")
    print(f"{'='*60}")

    html = buscar_html(url)

    preco = extrair_preco(html)
    if preco is None:
        raise Exception(f"Nenhum preço encontrado para: {nome}")

    print(f"\n💰 Preço final: R$ {preco:.2f} | Alvo: R$ {alvo:.2f}")

    if preco <= alvo:
        msg = (
            f"🔥 <b>ALERTA CENTAURO!</b>\n\n"
            f'<a href="{url}">{nome}</a>\n\n'
            f"Preço: <b>R$ {preco:.2f}</b>\n"
            f"Alvo: <b>R$ {alvo:.2f}</b>"
        )
        enviar_telegram(token, chat_id, msg)
        print("📤 Alerta enviado!")
    else:
        print(f"ℹ️ Preço acima do alvo — sem alerta.")


def main():
    token   = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")

    erros = []
    for produto in PRODUTOS:
        try:
            monitorar_produto(produto, token, chat_id)
        except Exception as e:
            print(f"\n❌ ERRO em '{produto['nome']}': {e}")
            erros.append((produto["nome"], str(e)))
        # Pequena pausa entre requisições para não sobrecarregar a API
        time.sleep(3)

    if erros:
        print(f"\n⚠️ {len(erros)} produto(s) com erro:")
        for nome, err in erros:
            print(f"   • {nome}: {err}")
    else:
        print("\n✅ Monitoramento concluído sem erros.")


if __name__ == "__main__":
    main()
