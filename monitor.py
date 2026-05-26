"""
Monitor de Preço - Centauro
Roteia o request pelo Tor para contornar o bloqueio de IPs do GitHub Actions.
Nenhuma conta extra necessária — Tor é instalado direto no runner.
"""

import os
import re
import json
import requests
from collections import Counter

# ── Configuração ──────────────────────────────────────────────────────────────

PRODUTO_URL    = "https://www.centauro.com.br/conjunto-de-agasalho-oxer-replayer-981478.html?cor=05"
PRECO_ALVO     = 200.00
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID        = os.environ.get("CHAT_ID")

# Tor sobe na porta 9050 (SOCKS5)
TOR_PROXY = {"http": "socks5h://127.0.0.1:9050", "https": "socks5h://127.0.0.1:9050"}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}


# ── Telegram ──────────────────────────────────────────────────────────────────

def enviar_telegram(mensagem: str) -> None:
    try:
        # Telegram vai direto (não precisa de Tor)
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": mensagem, "parse_mode": "HTML"},
            timeout=10,
        )
        r.raise_for_status()
        print("[Telegram] ✅ Mensagem enviada.")
    except Exception as e:
        print(f"[Telegram] ❌ Erro: {e}")


# ── Extração de preço ─────────────────────────────────────────────────────────

def extrair_preco(html: str) -> float | None:

    # 1) window.__STATE__ — JSON da VTEX com sellingPrice em centavos
    match = re.search(r'window\.__STATE__\s*=\s*(\{.+?\})\s*;?\s*</script', html, re.DOTALL)
    if match:
        try:
            state = json.loads(match.group(1))
            txt   = json.dumps(state)
            centavos = [int(v) / 100 for v in re.findall(r'"sellingPrice"\s*:\s*(\d+)', txt) if int(v) > 0]
            reais    = [float(v)     for v in re.findall(r'"spotPrice"\s*:\s*([\d.]+)', txt)  if float(v) > 0]
            validos  = [v for v in centavos + reais if 10 < v < 100_000]
            if validos:
                preco = min(validos)
                print(f"[extração] via __STATE__: R$ {preco:.2f}")
                return preco
        except Exception as e:
            print(f"[extração] __STATE__ erro: {e}")

    # 2) Schema.org / meta tag
    m = re.search(r'itemprop=["\']price["\'][^>]+content=["\']?([\d.]+)', html, re.IGNORECASE)
    if m:
        v = float(m.group(1))
        if 10 < v < 100_000:
            print(f"[extração] via meta tag: R$ {v:.2f}")
            return v

    # 3) Texto "R$ X,XX" mais frequente
    raws = re.findall(r'R\$\s*([\d]{2,3}(?:[.,]\d{3})*[.,]\d{2})', html)
    candidatos = []
    for raw in raws:
        try:
            candidatos.append(float(raw.replace(".", "").replace(",", ".")))
        except ValueError:
            pass
    validos = [v for v in candidatos if 10 < v < 100_000]
    if validos:
        preco = Counter(validos).most_common(1)[0][0]
        print(f"[extração] via texto R$: R$ {preco:.2f}")
        return preco

    return None


# ── Requisição via Tor ────────────────────────────────────────────────────────

def buscar_html() -> str | None:
    session = requests.Session()
    session.proxies.update(TOR_PROXY)

    try:
        # Confirma que o Tor está funcionando
        ip = session.get("https://api.ipify.org", timeout=30).text.strip()
        print(f"[Tor] IP de saída: {ip}")

        # Visita a home primeiro para gerar cookies de sessão
        session.get("https://www.centauro.com.br/", headers=HEADERS, timeout=30)

        # Busca o produto
        r = session.get(PRODUTO_URL, headers=HEADERS, timeout=60)
        print(f"[Tor] status={r.status_code}  tamanho={len(r.text):,} chars")

        if r.status_code == 200 and len(r.text) > 5_000:
            return r.text

        print(f"[Tor] Resposta suspeita: {r.text[:300]}")
    except Exception as e:
        print(f"[Tor] Erro: {e}")

    return None


# ── Main ──────────────────────────────────────────────────────────────────────

def monitorar() -> None:
    print(f"Produto: {PRODUTO_URL}")
    print(f"Alvo:    R$ {PRECO_ALVO:.2f}\n")

    html  = buscar_html()
    preco = extrair_preco(html) if html else None

    if not preco:
        msg = (
            "❌ <b>Preço não capturado</b>\n\n"
            "Tor carregou a página mas o preço não foi encontrado.\n"
            "O layout do site pode ter mudado."
        )
        enviar_telegram(msg)
        return

    print(f"\n✅ Preço: R$ {preco:.2f}  |  Alvo: R$ {PRECO_ALVO:.2f}")

    if preco <= PRECO_ALVO:
        msg = (
            f"🔥 <b>Alerta de Preço!</b>\n\n"
            f"💰 Preço atual: <b>R$ {preco:.2f}</b>\n"
            f"🎯 Seu alvo:    R$ {PRECO_ALVO:.2f}\n\n"
            f'🔗 <a href="{PRODUTO_URL}">Ver na Centauro</a>'
        )
    else:
        msg = (
            f"✅ <b>Monitoramento ativo</b>\n\n"
            f"💰 Preço atual: R$ {preco:.2f}\n"
            f"🎯 Alvo:        R$ {PRECO_ALVO:.2f}"
        )

    enviar_telegram(msg)


if __name__ == "__main__":
    monitorar()
