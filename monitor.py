import os
import re
import time
import requests

# ─── Produtos monitorados ────────────────────────────────────────────────────
# URL: página normal da Centauro (usada na notificação e para extrair código/cor)
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

# Base da API BFF da Centauro
CENTAURO_API_BASE = "https://apigateway.centauro.com.br/centauro-bff/products"
CENTAURO_SITE     = "https://www.centauro.com.br"

# Headers idênticos aos que o Chrome envia ao navegar pelo site
HEADERS_SITE = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Sec-CH-UA": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"Windows"',
}

HEADERS_API = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Origin": "https://www.centauro.com.br",
    "Referer": "https://www.centauro.com.br/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "Sec-CH-UA": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"Windows"',
}


# ─── Telegram ────────────────────────────────────────────────────────────────
def enviar_telegram(token, chat_id, mensagem):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": mensagem, "parse_mode": "HTML"}
        requests.post(url, json=payload, timeout=20)
    except Exception as e:
        print(f"⚠️ Erro Telegram: {e}")


# ─── Extração de código e cor da URL ─────────────────────────────────────────
def extrair_codigo_cor(url_produto):
    """
    Extrai o código do produto e a cor a partir da URL da Centauro.

    Exemplo:
      https://www.centauro.com.br/tenis-nike-revolution-995996.html?cor=31
      → codigo = "995996", cor = "31"
    """
    # Código: número imediatamente antes de ".html"
    codigo_match = re.search(r'-(\d{6,7})\.html', url_produto)
    if not codigo_match:
        raise ValueError(f"Código do produto não encontrado na URL: {url_produto}")
    codigo = codigo_match.group(1)

    # Cor: parâmetro ?cor=XX
    cor_match = re.search(r'[?&]cor=(\w+)', url_produto)
    if not cor_match:
        raise ValueError(f"Parâmetro 'cor' não encontrado na URL: {url_produto}")
    cor = cor_match.group(1)

    return codigo, cor


# ─── Sessão compartilhada com warm-up ────────────────────────────────────────
_session = None

def obter_sessao():
    """
    Retorna uma requests.Session já "aquecida":
    visita o site principal para receber cookies de sessão antes de
    chamar a API (que valida Origin + cookies via CORS).
    """
    global _session
    if _session is not None:
        return _session

    print("🔄 Iniciando sessão no site da Centauro (warm-up)...")
    s = requests.Session()
    try:
        resp = s.get(CENTAURO_SITE, headers=HEADERS_SITE, timeout=30)
        print(f"   Warm-up status: {resp.status_code} | "
              f"cookies: {list(s.cookies.keys())}")
    except Exception as e:
        print(f"   ⚠️ Warm-up falhou (seguindo mesmo assim): {e}")

    _session = s
    return _session


# ─── Consulta à API da Centauro ───────────────────────────────────────────────
def buscar_preco_api(url_produto, max_tentativas=3):
    """
    Chama a API BFF da Centauro e retorna o preço Pix do produto.

    Prioridade de preço:
      1. priceInfos.pixDiscount.price  (preço com desconto Pix — o mais barato)
      2. priceInfos.promotionalPrice   (preço promocional sem Pix)
      3. priceInfos.price              (preço cheio)

    A API retorna um objeto com a chave "skus" (lista de variações/tamanhos).
    Cada SKU tem seu próprio priceInfos; usamos o menor preço Pix disponível
    entre todos os SKUs com estoque.
    """
    codigo, cor = extrair_codigo_cor(url_produto)
    api_url = f"{CENTAURO_API_BASE}/{codigo}?color={cor}"

    print(f"   🔗 API: {api_url}")

    sessao = obter_sessao()

    for tentativa in range(1, max_tentativas + 1):
        try:
            resp = sessao.get(api_url, headers=HEADERS_API, timeout=30)
            print(f"   Status: {resp.status_code}")

            if resp.status_code == 403:
                # Sessão pode ter expirado — força novo warm-up
                global _session
                _session = None
                sessao = obter_sessao()
                raise Exception("403 — sessão renovada, tentando novamente")

            if resp.status_code != 200:
                raise Exception(f"API retornou status {resp.status_code}")

            data = resp.json()

            # Coleta preços de todos os SKUs com estoque
            precos_pix = []
            precos_promo = []
            precos_cheios = []

            skus = data.get("skus", [])
            if not skus:
                # Alguns endpoints retornam direto em "priceInfos" no nível raiz
                price_infos = data.get("priceInfos")
                if price_infos:
                    skus = [{"priceInfos": price_infos, "hasStock": True}]

            for sku in skus:
                # Ignora SKUs sem estoque (opcional: remova o if para pegar o
                # menor preço independentemente de disponibilidade)
                if not sku.get("hasStock", False):
                    continue

                pi = sku.get("priceInfos", {})
                if not pi:
                    continue

                pix = pi.get("pixDiscount", {})
                if pix and pix.get("price"):
                    precos_pix.append(float(pix["price"]))

                promo = pi.get("promotionalPrice")
                if promo:
                    precos_promo.append(float(promo))

                cheio = pi.get("price")
                if cheio:
                    precos_cheios.append(float(cheio))

            # Retorna o menor preço encontrado na ordem de prioridade
            if precos_pix:
                preco = min(precos_pix)
                print(f"   ✅ [Pix] R$ {preco:.2f}")
                return preco

            if precos_promo:
                preco = min(precos_promo)
                print(f"   ✅ [Promocional] R$ {preco:.2f}")
                return preco

            if precos_cheios:
                preco = min(precos_cheios)
                print(f"   ✅ [Preço cheio] R$ {preco:.2f}")
                return preco

            raise Exception("Nenhum campo de preço encontrado no JSON da API")

        except Exception as e:
            print(f"   ❌ Tentativa {tentativa}/{max_tentativas}: {e}")
            if tentativa < max_tentativas:
                time.sleep(4 * tentativa)

    raise Exception(f"Falha ao obter preço via API após {max_tentativas} tentativa(s)")


# ─── Monitor principal ────────────────────────────────────────────────────────
def monitor_produto(produto, token, chat_id):
    nome = produto["nome"]
    url  = produto["url"]
    alvo = produto["alvo"]

    print(f"\n{'=' * 60}")
    print(f"📦 {nome}")
    print(f"🎯 Alvo: R$ {alvo:.2f}")
    print(f"{'=' * 60}")

    preco = buscar_preco_api(url)

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
