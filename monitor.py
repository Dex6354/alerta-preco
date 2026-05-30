import os
import re
import time
import sys
from urllib.parse import quote

try:
    from curl_cffi import requests as curl_requests
except ImportError:
    print("❌ Erro: A biblioteca 'curl_cffi' não está instalada.")
    print("Execute: pip install curl_cffi")
    sys.exit(1)

import requests

# ============================================================
# CREDENCIAIS SHIBATA
# ============================================================
SHIBATA_TOKEN  = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJ2aXBjb21tZXJjZSIsImF1ZCI6ImFwaS1hZG1pbiIsInN1YiI6IjZiYzQ4NjdlLWRjYTktMTFlOS04NzQyLTAyMGQ3OTM1OWNhMCIsInZpcGNvbW1lcmNlQ2xpZW50ZUlkIjpudWxsLCJpYXQiOjE3NTE5MjQ5MjgsInZlciI6MSwiY2xpZW50IjpudWxsLCJvcGVyYXRvciI6bnVsbCwib3JnIjoiMTYxIn0.yDCjqkeJv7D3wJ0T_fu3AaKlX9s5PQYXD19cESWpH-j3F_Is-Zb-bDdUvduwoI_RkOeqbYCuxN0ppQQXb1ArVg"
SHIBATA_ORG_ID = "161"
SHIBATA_HEADERS = {
    "Authorization": f"Bearer {SHIBATA_TOKEN}",
    "organizationid": SHIBATA_ORG_ID,
    "sessao-id": "4ea572793a132ad95d7e758a4eaf6b09",
    "domainkey": "loja.shibata.com.br",
    "User-Agent": "Mozilla/5.0",
}

# ============================================================
# HEADERS CENTAURO
# ============================================================
CENTAURO_API_BASE = "https://apigateway.centauro.com.br/centauro-bff/products"
CENTAURO_HEADERS = {
    "authority": "apigateway.centauro.com.br",
    "accept": "application/json, text/plain, */*",
    "accept-language": "pt-BR,pt;q=0.9",
    "origin": "https://www.centauro.com.br",
    "referer": "https://www.centauro.com.br/",
    "sec-ch-ua": '"Chromium";v="148", "Brave";v="148", "Not/A)Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
}

# ============================================================
# SITES MONITORADOS
# ============================================================
SITES = [
    {
        "loja": "centauro",
        "titulo_alerta": "🔥 ALERTA CENTAURO!",
        "produtos": [
            {
                "nome": "Tênis Masculino Nike Revolution 8",
                "url": "https://www.centauro.com.br/tenis-masculino-nike-revolution-8-995996.html?cor=31",
                "alvo": 300.00,
            },
            {
                "nome": "Regata",
                "url": "https://www.centauro.com.br/regata-oxer-regata-respirabilidade-mas-984829.html?cor=83",
                "alvo": 70.00,
            },
            {
                "nome": "Conjunto Agasalho Oxer Replayer",
                "url": "https://www.centauro.com.br/conjunto-de-agasalho-oxer-replayer-981478.html?cor=05",
                "alvo": 200.00,
            },
        ],
    },
    {
        "loja": "shibata",
        "titulo_alerta": "🔥 ALERTA SHIBATA!",
        "produtos": [
            {
                "nome": "Sorvete Bombom Jundiaí Pote 2L",
                "url": "https://www.loja.shibata.com.br/produto/11622/sorvete-bombom-jundia-pote-2l",
                "alvo": 40.00,
            },
        ],
    },
]

# ============================================================
# TELEGRAM
# ============================================================
def enviar_telegram(token, chat_id, mensagem):
    if not token or not chat_id:
        print("⚠️ Telegram não enviado: Variáveis de ambiente faltando.")
        return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": mensagem, "parse_mode": "HTML"}
        requests.post(url, json=payload, timeout=20)
    except Exception as e:
        print(f"⚠️ Erro Telegram: {e}")

# ============================================================
# CENTAURO — busca de preço via API
# ============================================================
def extrair_codigo_cor(url_produto):
    codigo_match = re.search(r'-(\d{6,7})\.html', url_produto)
    if not codigo_match:
        raise ValueError(f"Código não encontrado na URL: {url_produto}")
    cor_match = re.search(r'[?&]cor=(\w+)', url_produto)
    if not cor_match:
        raise ValueError(f"Parâmetro 'cor' não encontrado na URL: {url_produto}")
    return codigo_match.group(1), cor_match.group(1)

def buscar_preco_centauro(url_produto, max_tentativas=3):
    codigo, cor = extrair_codigo_cor(url_produto)
    api_url = f"{CENTAURO_API_BASE}/{codigo}?color={cor}"
    print(f"   🔗 API: {api_url}")

    for tentativa in range(1, max_tentativas + 1):
        try:
            s = curl_requests.Session(impersonate="chrome")
            resp = s.get(api_url, headers=CENTAURO_HEADERS, timeout=30)
            print(f"   Status: {resp.status_code}")

            if resp.status_code == 403:
                raise Exception("403 Forbidden (Bloqueio Akamai)")
            if resp.status_code != 200:
                raise Exception(f"API retornou status {resp.status_code}")

            data = resp.json()
            product_data = data.get("product", {})
            sizes = product_data.get("sizes", [])

            if not sizes and product_data.get("priceInfos"):
                sizes = [{"priceInfos": product_data.get("priceInfos"), "hasStock": True, "description": "Único"}]

            precos_pix   = []
            precos_promo = []
            precos_cheios = []

            for item in sizes:
                if not item.get("hasStock", False):
                    continue

                tamanho = item.get("description", "N/A")
                pi = item.get("priceInfos", {})
                if not pi:
                    continue

                pix = pi.get("pixDiscount", {})
                if pix and pix.get("price"):
                    v_pix = float(pix["price"])
                    precos_pix.append(v_pix)
                    print(f"   [Disponível] Tam: {tamanho} | Pix: R$ {v_pix:.2f}")

                promo = pi.get("promotionalPrice")
                if promo:
                    precos_promo.append(float(promo))

                cheio = pi.get("price")
                if cheio:
                    precos_cheios.append(float(cheio))

            if precos_pix:
                return min(precos_pix)
            if precos_promo:
                return min(precos_promo)
            if precos_cheios:
                return min(precos_cheios)

            raise Exception("Nenhum preço disponível encontrado no JSON")

        except Exception as e:
            print(f"   ❌ Tentativa {tentativa}/{max_tentativas}: {e}")
            if tentativa < max_tentativas:
                time.sleep(5 * tentativa)

    raise Exception(f"Falha total após {max_tentativas} tentativa(s)")

# ============================================================
# SHIBATA — busca de preço via API
# ============================================================
def buscar_preco_shibata(produto) -> float:
    url_produto = produto["url"]
    nome        = produto["nome"]

    match_id = re.search(r'/produto/(\d+)/', url_produto)
    if not match_id:
        raise Exception(f"produto_id não encontrado na URL: {url_produto}")
    produto_id = int(match_id.group(1))

    termo = quote(nome.split()[0])
    api_url = (
        f"https://services.vipcommerce.com.br/api-admin/v1/org/{SHIBATA_ORG_ID}"
        f"/filial/1/centro_distribuicao/1/loja/buscas/produtos/termo/{termo}?page=1"
    )

    print(f"   🔄 Consultando API Shibata (produto_id={produto_id})...")
    response = requests.get(api_url, headers=SHIBATA_HEADERS, timeout=15)
    print(f"   Status HTTP: {response.status_code}")

    if response.status_code != 200:
        raise Exception(f"API Shibata retornou {response.status_code}")

    produtos = response.json().get("data", {}).get("produtos", [])
    print(f"   ℹ️  {len(produtos)} produto(s) retornado(s) pela API")

    for p in produtos:
        if p.get("produto_id") == produto_id or p.get("id") == produto_id:
            oferta       = p.get("oferta") or {}
            preco_oferta = oferta.get("preco_oferta")
            preco_base   = p.get("preco") or 0
            preco = float(preco_oferta) if (p.get("em_oferta") and preco_oferta) else float(preco_base)
            print(f"   ✅ [API Shibata] Produto encontrado: R$ {preco:.2f}")
            return preco

    raise Exception(f"Produto ID {produto_id} não encontrado na resposta da API Shibata")

# ============================================================
# MONITOR UNIFICADO
# ============================================================
def monitorar_produto(produto, loja, titulo_alerta, token, chat_id):
    nome = produto["nome"]
    url  = produto["url"]
    alvo = produto["alvo"]

    print(f"\n{'='*60}")
    print(f"📦 {nome}")
    print(f"   Alvo: R$ {alvo:.2f} | Loja: {loja.upper()}")
    print(f"{'='*60}")

    if loja == "centauro":
        preco = buscar_preco_centauro(url)
    elif loja == "shibata":
        preco = buscar_preco_shibata(produto)
    else:
        raise Exception(f"Loja desconhecida: '{loja}'")

    print(f"\n💰 Preço final: R$ {preco:.2f} | Alvo: R$ {alvo:.2f}")

    if preco <= alvo:
        msg = (
            f"<b>{titulo_alerta}</b>\n\n"
            f'<a href="{url}">{nome}</a>\n\n'
            f"Preço: <b>R$ {preco:.2f}</b>\n"
            f"Alvo:  <b>R$ {alvo:.2f}</b>"
        )
        enviar_telegram(token, chat_id, msg)
        print("📤 Alerta enviado!")
    else:
        print("ℹ️  Preço acima do alvo — sem alerta.")

def main():
    token   = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")

    erros = []

    for site in SITES:
        loja          = site["loja"]
        titulo_alerta = site["titulo_alerta"]
        produtos      = site["produtos"]

        print(f"\n{'#'*60}")
        print(f"# {titulo_alerta}")
        print(f"{'#'*60}")

        for produto in produtos:
            try:
                monitorar_produto(produto, loja, titulo_alerta, token, chat_id)
            except Exception as e:
                print(f"\n❌ ERRO em '{produto['nome']}': {e}")
                erros.append((produto["nome"], str(e)))
            time.sleep(2)

    if erros:
        print(f"\n⚠️ {len(erros)} produto(s) com erro:")
        for nome, err in erros:
            print(f"   • {nome}: {err}")
    else:
        print("\n✅ Monitoramento concluído sem erros.")

    total_produtos = sum(len(s["produtos"]) for s in SITES)
    if erros and len(erros) == total_produtos:
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"💥 Erro fatal: {e}")
        sys.exit(1)
