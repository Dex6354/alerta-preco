import os
import re
import json
import time
import requests
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed

# ─── Grupos de produtos ───────────────────────────────────────────────────────
GRUPOS = [
    {
        "alvo": 200.00,
        "produtos": [
            {
                "nome": "Conjunto Agasalho Oxer Replayer",
                "url": "https://www.centauro.com.br/conjunto-de-agasalho-oxer-replayer-981478.html?cor=05",
            },
            {
                "nome": "Conjunto Agasalho Masculino Asics Interlock",
                "url": "https://www.centauro.com.br/conjunto-de-agasalho-masculino-asics-com-capuz-interlock-fechado-976758.html?cor=02",
            },
        ],
    },
    {
        "alvo": 80.00,
        "produtos": [
            {
                "nome": "Regata Oxer Respirabilidade",
                "url": "https://www.centauro.com.br/regata-oxer-regata-respirabilidade-mas-984829.html?cor=83",
            },
        ],
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

MAX_SCRAPE_CALLS = 5


# ─── Telegram ────────────────────────────────────────────────────────────────
def enviar_telegram(token, chat_id, mensagem):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": mensagem, "parse_mode": "HTML"}
        requests.post(url, json=payload, timeout=20)
    except Exception as e:
        print(f"⚠️ Erro Telegram: {e}")


# ─── Disponibilidade ─────────────────────────────────────────────────────────
INDISPONIVEL_PATTERNS = [
    r'produto\s+indispon[íi]vel',
    r'indispon[íi]vel',
    r'fora\s+de\s+estoque',
    r'out\s+of\s+stock',
    r'esgotado',
]

def verificar_disponibilidade(html):
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
            availability = offers.get("availability", "")
            if "OutOfStock" in availability or "Discontinued" in availability:
                return False
            if availability:
                return True
        except Exception:
            continue

    for pattern in INDISPONIVEL_PATTERNS:
        if re.search(pattern, html, re.IGNORECASE):
            return False

    return True


# ─── Extração de preço ───────────────────────────────────────────────────────
def extrair_preco(html):
    # JSON-LD
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
                    return valor
        except Exception:
            continue

    # Pix
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
                return valor
        except Exception:
            pass

    # Heurística
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
    if not unique_prices:
        return None
    return unique_prices[1] if len(unique_prices) >= 2 else unique_prices[0]


# ─── Busca de HTML com fallback em camadas ────────────────────────────────────
def buscar_html(url_produto, nome):
    encoded_url = quote(url_produto)
    scrape_calls = 0

    def log(msg):
        print(f"   [{nome}] {msg}")

    # Camada 0: requisição direta
    try:
        resp = requests.get(url_produto, headers=HEADERS_DIRETO, timeout=15)
        if resp.status_code == 200 and len(resp.text) > 5_000:
            if extrair_preco(resp.text) is not None:
                log("✅ Camada 0 (gratuita)")
                return resp.text, scrape_calls
        elif resp.status_code == 403:
            log("⛔ 403 — pulando para scrape.do")
    except Exception as e:
        log(f"❌ Camada 0: {e}")

    # Camada 1: scrape.do sem render
    for tentativa in range(1, 3):
        if scrape_calls >= MAX_SCRAPE_CALLS:
            break
        try:
            api_url = f"https://api.scrape.do/?token={SCRAPE_TOKEN}&url={encoded_url}"
            resp = requests.get(api_url, timeout=45)
            scrape_calls += 1
            if resp.status_code == 200 and len(resp.text) > 5_000:
                if extrair_preco(resp.text) is not None:
                    log(f"✅ Camada 1 (chamadas pagas: {scrape_calls})")
                    return resp.text, scrape_calls
                log("⚠️ Sem preço sem render — avançando")
                break
            elif resp.status_code == 502:
                log(f"⚠️ 502 tentativa {tentativa}")
                time.sleep(2)
        except Exception as e:
            log(f"❌ Camada 1 tentativa {tentativa}: {e}")
            time.sleep(2)

    # Camada 2: scrape.do com render=true
    for tentativa in range(1, MAX_SCRAPE_CALLS + 1):
        if scrape_calls >= MAX_SCRAPE_CALLS:
            break
        try:
            api_url = (
                f"https://api.scrape.do/?token={SCRAPE_TOKEN}"
                f"&url={encoded_url}&render=true"
            )
            resp = requests.get(api_url, timeout=60)
            scrape_calls += 1
            if resp.status_code == 200:
                log(f"✅ Camada 2 render ({len(resp.text):,} chars, chamadas pagas: {scrape_calls})")
                return resp.text, scrape_calls
            elif resp.status_code == 502:
                log(f"⚠️ 502 tentativa {tentativa}")
                time.sleep(3)
            else:
                raise Exception(f"scrape.do retornou {resp.status_code}")
        except Exception as e:
            log(f"❌ Camada 2 tentativa {tentativa}: {e}")
            time.sleep(2)

    raise Exception(f"Falha após {scrape_calls} chamada(s) pagas")


# ─── Processar um produto (roda em paralelo) ──────────────────────────────────
def processar_produto(produto, alvo):
    """Retorna dict com resultado para ser enviado ao Telegram depois."""
    nome = produto["nome"]
    url  = produto["url"]

    try:
        html, scrape_calls = buscar_html(url, nome)

        disponivel = verificar_disponibilidade(html)
        if not disponivel:
            print(f"   [{nome}] ⛔ Indisponível")
            return {"nome": nome, "url": url, "alvo": alvo, "disponivel": False}

        preco = extrair_preco(html)
        if preco is None:
            raise Exception("Nenhum preço encontrado")

        print(f"   [{nome}] 💰 R$ {preco:.2f} | Alvo: R$ {alvo:.2f}")
        return {"nome": nome, "url": url, "alvo": alvo, "disponivel": True, "preco": preco}

    except Exception as e:
        print(f"   [{nome}] ❌ {e}")
        return {"nome": nome, "url": url, "alvo": alvo, "erro": str(e)}


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    token   = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('CHAT_ID')

    # Achata todos os produtos mantendo o alvo do grupo
    tarefas = [
        (produto, grupo["alvo"])
        for grupo in GRUPOS
        for produto in grupo["produtos"]
    ]

    print(f"🚀 Iniciando monitoramento paralelo de {len(tarefas)} produto(s)...\n")
    inicio = time.time()

    resultados = {}
    with ThreadPoolExecutor(max_workers=len(tarefas)) as executor:
        futures = {
            executor.submit(processar_produto, produto, alvo): produto["nome"]
            for produto, alvo in tarefas
        }
        for future in as_completed(futures):
            resultado = future.result()
            resultados[resultado["nome"]] = resultado

    print(f"\n⏱️ Busca concluída em {time.time() - inicio:.1f}s\n")

    # Envia mensagens na ordem original
    for produto, alvo in tarefas:
        nome = produto["nome"]
        r = resultados[nome]

        if "erro" in r:
            msg = f"❌ Monitor Centauro — {nome}\nErro: {r['erro']}"
        elif not r["disponivel"]:
            msg = f"⛔ Monitor Centauro — {nome}\nProduto indisponível no momento."
        elif r["preco"] <= alvo:
            msg = (
                f"🔥 <b>ALERTA CENTAURO!</b>\n"
                f"<b>{nome}</b>\n"
                f"Preço baixou para <b>R$ {r['preco']:.2f}</b> (alvo: R$ {alvo:.2f})\n\n"
                f"{produto['url']}"
            )
        else:
            msg = (
                f"✅ Monitor Centauro — {nome}\n"
                f"Preço atual: R$ {r['preco']:.2f} (Alvo: R$ {alvo:.2f})"
            )

        enviar_telegram(token, chat_id, msg)
        print(f"📤 [{nome}] Mensagem enviada")


if __name__ == "__main__":
    main()
