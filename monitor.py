"""
Monitor de Preço - Centauro (modo DEBUG)
Execute uma vez para ver o que o Tor está retornando da Centauro.
"""

import os
import re
import json
import requests
from collections import Counter

PRODUTO_URL = "https://www.centauro.com.br/conjunto-de-agasalho-oxer-replayer-981478.html?cor=05"
TOR_PROXY   = {"http": "socks5h://127.0.0.1:9050", "https": "socks5h://127.0.0.1:9050"}
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

def debug():
    session = requests.Session()
    session.proxies.update(TOR_PROXY)

    # ── 1. Confirma IP do Tor ─────────────────────────────────────────────────
    try:
        ip = session.get("https://api.ipify.org", timeout=30).text.strip()
        print(f"\n{'='*60}")
        print(f"[TOR] IP de saída: {ip}")
    except Exception as e:
        print(f"[TOR] ERRO ao obter IP — Tor pode não estar rodando: {e}")
        return

    # ── 2. Requisição para a Centauro ─────────────────────────────────────────
    try:
        session.get("https://www.centauro.com.br/", headers=HEADERS, timeout=30)
        r = session.get(PRODUTO_URL, headers=HEADERS, timeout=60)
    except Exception as e:
        print(f"[HTTP] ERRO na requisição: {e}")
        return

    html = r.text
    print(f"\n{'='*60}")
    print(f"[HTTP] Status:  {r.status_code}")
    print(f"[HTTP] Tamanho: {len(html):,} chars")
    print(f"[HTTP] Headers: {dict(r.headers)}")

    # ── 3. Primeiros 2000 chars do HTML ──────────────────────────────────────
    print(f"\n{'='*60}")
    print("[HTML] Primeiros 2000 chars:")
    print(html[:2000])

    # ── 4. Últimos 500 chars ──────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("[HTML] Últimos 500 chars:")
    print(html[-500:])

    # ── 5. Detecta proteção ───────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("[DETECÇÃO] Verificando bloqueios...")
    checks = {
        "Cloudflare":  "cloudflare" in html.lower() or "__cf_" in html,
        "Captcha":     "captcha" in html.lower() or "recaptcha" in html.lower(),
        "Akamai":      "akamai" in html.lower() or "_abck" in html,
        "DataDome":    "datadome" in html.lower(),
        "403/bloqueio": r.status_code == 403,
        "HTML vazio":  len(html) < 5000,
    }
    for nome, detectado in checks.items():
        status = "⚠️  DETECTADO" if detectado else "✅ ok"
        print(f"  {nome:20s} {status}")

    # ── 6. Busca por "R$" no HTML ─────────────────────────────────────────────
    print(f"\n{'='*60}")
    preco_matches = re.findall(r'R\$\s*[\d.,]+', html)
    print(f"[PREÇO] Ocorrências de 'R$' no HTML: {len(preco_matches)}")
    if preco_matches:
        print("  Primeiras 20:", preco_matches[:20])
    else:
        print("  ⚠️  Nenhuma ocorrência de R$ encontrada")

    # ── 7. Verifica __STATE__ ─────────────────────────────────────────────────
    print(f"\n{'='*60}")
    state_match = re.search(r'window\.__STATE__\s*=\s*(\{.+?\})\s*;?\s*</script', html, re.DOTALL)
    if state_match:
        print(f"[__STATE__] ✅ Encontrado! Tamanho: {len(state_match.group(1)):,} chars")
        try:
            state = json.loads(state_match.group(1))
            txt   = json.dumps(state)
            centavos = re.findall(r'"sellingPrice"\s*:\s*(\d+)', txt)
            spot     = re.findall(r'"spotPrice"\s*:\s*([\d.]+)', txt)
            print(f"  sellingPrice (centavos): {centavos[:10]}")
            print(f"  spotPrice    (reais):    {spot[:10]}")
        except Exception as e:
            print(f"  ⚠️  Erro ao parsear __STATE__: {e}")
            print(f"  Primeiros 500 chars do __STATE__: {state_match.group(1)[:500]}")
    else:
        print("[__STATE__] ⚠️  NÃO encontrado no HTML")

    # ── 8. Scripts presentes na página ───────────────────────────────────────
    print(f"\n{'='*60}")
    scripts = re.findall(r'<script[^>]*src=["\']([^"\']+)["\']', html)
    print(f"[SCRIPTS] {len(scripts)} scripts externos encontrados:")
    for s in scripts[:15]:
        print(f"  {s}")

    # ── 9. Salva HTML completo para análise ──────────────────────────────────
    with open("/tmp/centauro_debug.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n{'='*60}")
    print("[ARQUIVO] HTML completo salvo em: /tmp/centauro_debug.html")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    debug()
