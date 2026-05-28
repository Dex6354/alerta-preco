import os
import re
import sys
import time
from urllib.parse import quote
import requests

try:
    from curl_cffi import requests as curl_requests
except ImportError:
    print("❌ Erro: A biblioteca 'curl_cffi' não está instalada.")
    print("Execute: pip install curl_cffi")
    sys.exit(1)

# ============================================================
# CONFIGURAÇÃO DE PRODUTOS (Suporta 1 ou múltiplas URLs por alvo)
# ============================================================
PRODUTOS = [
    {
        "nome": "Tênis Masculino Nike Revolution 8",
        "urls": [
            "https://www.centauro.com.br/tenis-masculino-nike-revolution-8-995996.html?cor=31"
        ],
        "alvo": 300.00,
    },
    {
        "nome": "Sorvete Bombom Jundiaí Pote 2L",
        "urls": [
            "https://www.loja.shibata.com.br/produto/11622/sorvete-bombom-jundia-pote-2l"
        ],
        "alvo": 40.00,  # Aumente aqui para testar o disparo se o preço real for maior
    },
    {
        "nome": "Exemplo Multi-Links (Mesmo Alvo)",
        "urls": [
            "https://www.centauro.com.br/regata-oxer-regata-respirabilidade-mas-984829.html?cor=83",
            "https://www.loja.shibata.com.br/produto/11622/sorvete-bombom-jundia-pote-2l"
        ],
        "alvo": 150.00,
    }
]

# ============================================================
# CONFIGURAÇÕES DA API
# ============================================================
CENTAURO_API_BASE = "https://apigateway.centauro.com.br/centauro-bff/products"
HEADERS_CENTAURO = {
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

SHIBATA_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJ2aXBjb21tZXJjZSIsImF1ZCI6ImFwaS1hZG1pbiIsInN1YiI6IjZiYzQ4NjdlLWRjYTktMTFlOS04NzQyLTAyMGQ3OTM1OWNhMCIsInZpcGNvbW1lcmNlQ2xpZW50ZUlkIjpudWxsLCJpYXQiOjE3NTE5MjQ5MjgsInZlciI6MSwiY2xpVENTIjpudWxsLCJvcGVyYXRvciI6bnVsbCwib3JnIjoiMTYxIn0.yDCjqkeJv7D3wJ0T_fu3AaKlX9s5PQYXD19cESWpH-j3F_Is-Zb-bDdUvduwoI_RkOeqbYCuxN0ppQQXb1ArVg"
SHIBATA_ORG_ID = "161"
HEADERS_SHIBATA = {
    "Authorization": f"Bearer {SHIBATA_TOKEN}",
    "organizationid": SHIBATA_ORG_ID,
    "sessao-id": "4ea572793a132ad95d7e758a4eaf6b09",
    "domainkey": "loja.shibata.com.br",
    "User-Agent": "Mozilla/5.0",
}

# ------------------------------------------------------------
# TELEGRAM
# ------------------------------------------------------------
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

# ------------------------------------------------------------
# PARSERS E BUSCA CENTAURO
# ------------------------------------------------------------
def extrair_codigo_cor_centauro(url_produto):
    codigo_match = re.search(r'-(\d{6,7})\.html', url_produto)
    if not codigo_match:
        raise ValueError(f"Código não encontrado na URL: {url_produto}")
    cor_match = re.search(r'[?&]cor=(\w+)', url_produto)
    if not cor_match:
        raise ValueError(f"Parâmetro 'cor' não encontrado na URL: {url_produto}")
    return codigo_match.group(1), cor_match.group(1)

def buscar_preco_centauro(url_produto, max_tentativas=3):
    codigo, cor = extrair_codigo_cor_centauro(url_produto)
    api_url = f"{CENTAURO_API_BASE}/{codigo}?color={cor}"
    print(f"   🔗 API Centauro: {api_url}")

    for tentativa in range(1, max_tentativas + 1):
        try:
            s = curl_requests.Session(impersonate="chrome")
            resp = s.get(api_url, headers=HEADERS_CENTAURO, timeout=30)
            
            if resp.status_code == 403:
                raise Exception("403 Forbidden (Bloqueio Akamai)")
            if resp.status_code != 200:
                raise Exception(f"API retornou status {resp.status_code}")

            data = resp.json()
            product_data = data.get("product", {})
            sizes = product_data.get("sizes", [])
            
            if not sizes and product_data.get("priceInfos"):
                sizes = [{"priceInfos": product_data.get("priceInfos"), "hasStock": True, "description": "Único"}]

            precos = []
            for item in sizes:
                if not item.get("hasStock", False):
                    continue
                pi = item.get("priceInfos", {})
                if not pi:
                    continue

                pix = pi.get("pixDiscount", {})
                if pix and pix.get("price"):
                    precos.append(float(pix["price"]))
                elif pi.get("promotionalPrice"):
                    precos.append(float(pi["promotionalPrice"]))
                elif pi.get("price"):
                    precos.append(float(pi["price"]))

            if precos:
                return min(precos)
            raise Exception("Nenhum preço disponível encontrado no JSON")
        except Exception as e:
            print(f"   ❌ Tentativa {tentativa}/{max_tentativas}: {e}")
            if tentativa < max_tentativas:
                time.sleep(5 * tentativa)
    raise Exception(f"Falha total na Centauro após {max_tentativas} tentativa(s)")

# ------------------------------------------------------------
# PARSERS E BUSCA SHIBATA
# ------------------------------------------------------------
def buscar_preco_shibata(url_produto):
    # Extrai o ID do produto da URL
    match = re.search(r'/produto/(\d+)/([^/?#\s]+)', url_produto)
    if not match:
        raise Exception(f"Não foi possível extrair ID/Slug da URL Shibata: {url_produto}")
    
    produto_id = int(match.group(1))
    # Extrai o termo do slug da URL em vez de usar o 'nome' do produto mapeado
    termo = quote(match.group(2).split('-')[0])

    api_url = (
        f"https://services.vipcommerce.com.br/api-admin/v1/org/{SHIBATA_ORG_ID}"
        f"/filial/1/centro_distribuicao/1/loja/buscas/produtos/termo/{termo}?page=1"
    )
    print(f"   🔗 API Shibata: {api_url} (ID: {produto_id})")

    response = requests.get(api_url, headers=HEADERS_SHIBATA, timeout=15)
    if response.status_code != 200:
        raise Exception(f"API Shibata retornou status {response.status_code}. Token/Sessão podem ter expirado.")

    produtos = response.json().get("data", {}).get("produtos", [])
    for p in produtos:
        if p.get("produto_id") == produto_id or p.get("id") == produto_id:
            oferta = p.get("oferta") or {}
            preco_oferta = oferta.get("preco_oferta")
            preco_base = p.get("preco") or 0
            return float(preco_oferta) if (p.get("em_oferta") and preco_oferta) else float(preco_base)

    raise Exception(f"Produto ID {produto_id} não encontrado na listagem da busca da API Shibata.")

# ------------------------------------------------------------
# MONITOR FLUXO PRINCIPAL
# ------------------------------------------------------------
def monitorar_url(nome, url, alvo, token, chat_id):
    if "centauro.com.br" in url:
        loja = "CENTAURO"
        preco = buscar_preco_centauro(url)
    elif "shibata.com.br" in url:
        loja = "SHIBATA"
        preco = buscar_preco_shibata(url)
    else:
        print(f"⚠️ URL não suportada: {url}")
        return

    print(f"   💰 Preço atual: R$ {preco:.2f} | Alvo: R$ {alvo:.2f}")

    if preco <= alvo:
        # Formatação com o link embutido diretamente no nome do item
        msg = (
            f"🔥 <b>ALERTA {loja}!</b>\n\n"
            f'<a href="{url}">{nome}</a>\n\n'
            f"Preço: <b>R$ {preco:.2f}</b>\n"
            f"Alvo: <b>R$ {alvo:.2f}</b>"
        )
        enviar_telegram(token, chat_id, msg)
        print("   📤 Alerta enviado ao Telegram!")
    else:
        print("   ✅ Preço dentro do esperado (acima do alvo).")

def main():
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('CHAT_ID')
    erros = []

    for produto in PRODUTOS:
        nome = produto["nome"]
        alvo = produto["alvo"]
        urls = produto["urls"]

        print(f"\n{'=' * 60}\n📦 {nome}\n🎯 Alvo Geral: R$ {alvo:.2f}\n{'=' * 60}")

        for url in urls:
            try:
                print(f"\n🔍 Verificando link: {url[:65]}...")
                monitorar_url(nome, url, alvo, token, chat_id)
            except Exception as e:
                print(f"   ❌ ERRO: {e}")
                erros.append((nome, url, str(e)))
            time.sleep(2)

    print(f"\n{'#' * 60}\n🏁 Monitoramento Concluído.")
    if erros:
        print(f"⚠️ Houve falha em {len(erros)} link(s).")

if __name__ == "__main__":
    main()
