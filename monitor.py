import os
import re
import json
import time
import requests
from urllib.parse import quote

# ============================================================
# CONFIGURAÇÕES DE EXTRAÇÃO DE PREÇO (Centauro / scrape.do)
# ============================================================
# JSON-LD é sempre a primeira e única estratégia ativa.
# Ative os fallbacks abaixo SOMENTE se o JSON-LD falhar no site alvo.

USAR_PIX_REGEX  = False  # Busca preço próximo à palavra "Pix"
USAR_HEURISTICA = False  # Tenta adivinhar o preço por heurística de valores no HTML
# ============================================================


# ============================================================
# CREDENCIAIS
# ============================================================
SCRAPE_TOKEN = "3a23ea3810a04b16bccfac96a2c3b1af73c97a98ef5"

# Token e configurações da API Shibata
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


# ============================================================
# SITES MONITORADOS
#
# Cada site tem:
#   "titulo_alerta" → título da mensagem no Telegram
#   "metodo"        → "scrape" (usa scrape.do) ou "shibata_api" (usa API direta)
#   "produtos"      → lista de produtos
#
# Para adicionar um novo site: copie um bloco e edite.
# ============================================================

SITES = [

    # ----------------------------------------------------------
    # 🏪 CENTAURO  (método: scrape.do)
    # Lógica de retry:
    #   • Até 3 tentativas com render=false (1 crédito cada)
    #   • 502 → aguarda 5 s e repete
    #   • Se as 3 tentativas falharem → ativa render=true (5 créditos)
    # ----------------------------------------------------------
    {
        "titulo_alerta": "🔥 ALERTA CENTAURO!",
        "metodo": "scrape",
        "produtos": [
            {
                "nome": "Agasalho Oxer Replayer (cor 05)",
                "url": "https://www.centauro.com.br/conjunto-de-agasalho-oxer-replayer-981478.html?cor=05",
                "alvo": 150.00,
            },
            {
                "nome": "Agasalho Asics Interlock (cor 02)",
                "url": "https://www.centauro.com.br/conjunto-de-agasalho-masculino-asics-com-capuz-interlock-fechado-976758.html?cor=02",
                "alvo": 150.00,
            },
            {
                "nome": "Regata Oxer Respirabilidade",
                "url": "https://www.centauro.com.br/regata-oxer-regata-respirabilidade-mas-984829.html?cor=83",
                "alvo": 80.00,
            },
        ],
    },

    # ----------------------------------------------------------
    # 🏪 SHIBATA  (método: API direta — 0 créditos scrape.do)
    #
    # A URL deve seguir o padrão:
    #   https://www.loja.shibata.com.br/produto/{produto_id}/{slug}
    # O código extrai o produto_id automaticamente da URL.
    # ----------------------------------------------------------
    {
        "titulo_alerta": "🔥 ALERTA SHIBATA!",
        "metodo": "shibata_api",
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


# ------------------------------------------------------------
# TELEGRAM
# ------------------------------------------------------------
def enviar_telegram(token, chat_id, mensagem):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": mensagem, "parse_mode": "HTML"}
        requests.post(url, json=payload, timeout=20)
    except Exception as e:
        print(f"⚠️ Erro Telegram: {e}")


# ------------------------------------------------------------
# EXTRAÇÃO DE PREÇO (HTML — usado apenas pelo método scrape)
# ------------------------------------------------------------
def extrair_preco(html):
    """
    Estratégias de extração em ordem de confiabilidade.
    As estratégias 2 e 3 são controladas pelas flags no topo do arquivo.
    """

    # --- Estratégia 1: JSON-LD (sempre ativa) ---
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
                if 10 < valor < 10000:
                    print(f"   ✅ [JSON-LD] Preço encontrado: R$ {valor:.2f}")
                    return valor
        except Exception:
            continue

    # --- Estratégia 2: Preço próximo à palavra "Pix" ---
    if USAR_PIX_REGEX:
        pix_match = re.search(
            r'R\$\s*([\d.,]+)(?:[\s\S]{0,200}?)(?:no\s+)?[Pp]ix'
            r'|(?:no\s+)?[Pp]ix(?:[\s\S]{0,200}?)R\$\s*([\d.,]+)',
            html,
        )
        if pix_match:
            raw = pix_match.group(1) or pix_match.group(2)
            try:
                valor = float(raw.replace(".", "").replace(",", "."))
                if 10 < valor < 10000:
                    print(f"   ✅ [Pix-regex] Preço encontrado: R$ {valor:.2f}")
                    return valor
            except Exception:
                pass
    else:
        print(f"   ⏭️  [Pix-regex] desativado (USAR_PIX_REGEX = False)")

    # --- Estratégia 3: Heurística ---
    if USAR_HEURISTICA:
        matches = re.findall(r'R\$\s*([\d.,]+)', html)
        valid_prices = []
        for m in matches:
            try:
                valor = float(m.replace(".", "").replace(",", "."))
                if 10 < valor < 10000:
                    valid_prices.append(valor)
            except Exception:
                continue
        unique_prices = sorted(set(valid_prices))
        print(f"   ℹ️  [Heurística] Preços válidos: {unique_prices}")
        if not unique_prices:
            return None
        if len(unique_prices) == 1:
            return unique_prices[0]
        preco = unique_prices[1] if len(unique_prices) >= 2 else unique_prices[0]
        print(f"   ✅ [Heurística] Preço estimado: R$ {preco:.2f}")
        return preco
    else:
        print(f"   ⏭️  [Heurística] desativada (USAR_HEURISTICA = False)")

    return None


# ------------------------------------------------------------
# MÉTODO SCRAPE — lógica de retry com render=false → render=true
# ------------------------------------------------------------
def _requisicao_scrape(url: str, render: bool) -> str:
    """
    Faz uma única requisição ao scrape.do.
    render=False → 1 crédito | render=True → 5 créditos
    Lança exceção em caso de falha.
    """
    encoded_url = quote(url)
    modo = "render=true" if render else "render=false"
    api_url = f"https://api.scrape.do/?token={SCRAPE_TOKEN}&url={encoded_url}&{modo}"

    response = requests.get(api_url, timeout=90)
    print(f"      Status HTTP: {response.status_code} | render={render} | {len(response.text):,} chars")

    if response.status_code == 200:
        return response.text
    elif response.status_code == 502:
        raise ConnectionError("502")          # identificador especial para 502
    else:
        raise Exception(f"scrape.do retornou {response.status_code}")


def buscar_html(url: str) -> tuple[str, str]:
    """
    Estratégia de requisição e economia de créditos:

    • Fase 1 — render=false (1 crédito por tentativa):
        Até 3 tentativas.
        - Sucesso com preço → retorna imediatamente.
        - 502              → aguarda 5 s e repete.
        - Outro erro       → encerra fase 1 e vai para fase 2.
        - Sem preço        → vai para fase 2.

    • Fase 2 — render=true (5 créditos):
        Ativada somente se a fase 1 esgotou as tentativas
        (seja por 502 repetido, erro ou ausência de preço).
        Uma única tentativa; lança exceção em caso de falha.

    Custo por produto:
        Melhor caso  →  1 crédito  (render=false resolveu na 1ª)
        Pior caso    →  8 créditos (3 × render=false + 1 × render=true)
    """
    MAX_TENTATIVAS_SEM_RENDER = 3
    ESPERA_502_SEGUNDOS       = 5

    ultimo_erro_foi_502 = False

    # ── Fase 1: render=false ──────────────────────────────────
    for tentativa in range(1, MAX_TENTATIVAS_SEM_RENDER + 1):
        print(f"   🔄 [render=false] Tentativa {tentativa}/{MAX_TENTATIVAS_SEM_RENDER} (1 crédito)...")
        try:
            html = _requisicao_scrape(url, render=False)
            preco_teste = extrair_preco(html)
            if preco_teste is not None:
                print(f"   💚 Preço encontrado sem render! Créditos poupados.")
                return html, "sem-render"
            else:
                print(f"   ⚠️ render=false retornou HTML mas sem preço.")
                ultimo_erro_foi_502 = False
                break   # HTML chegou mas sem preço → inútil repetir sem render

        except ConnectionError:
            # 502 — aguarda e tenta novamente se ainda há tentativas
            ultimo_erro_foi_502 = True
            if tentativa < MAX_TENTATIVAS_SEM_RENDER:
                print(f"   ⏳ 502 recebido — aguardando {ESPERA_502_SEGUNDOS}s antes de repetir...")
                time.sleep(ESPERA_502_SEGUNDOS)
            else:
                print(f"   ❌ 502 em todas as {MAX_TENTATIVAS_SEM_RENDER} tentativas sem render.")

        except Exception as e:
            print(f"   ⚠️ Erro inesperado em render=false: {e}")
            ultimo_erro_foi_502 = False
            break   # erro diferente de 502 → não faz sentido repetir

    # ── Fase 2: render=true ───────────────────────────────────
    motivo = "502 repetido" if ultimo_erro_foi_502 else "sem preço / erro"
    print(f"   🔄 [render=true] Ativando fallback ({motivo}) — 5 créditos...")
    try:
        html = _requisicao_scrape(url, render=True)
        return html, "render"
    except Exception as e:
        raise Exception(f"Falha ao carregar a página (render=true): {e}")


def buscar_preco_scrape(produto) -> float:
    """Orquestra busca de HTML e extração de preço para o método scrape."""
    url = produto["url"]
    html, modo = buscar_html(url)

    preco = extrair_preco(html)
    if preco is None:
        raise Exception(f"Nenhum preço encontrado no HTML (modo: {modo})")

    print(f"   📊 Modo usado: {modo}")
    return preco


# ------------------------------------------------------------
# MÉTODO SHIBATA API — consulta direta, zero créditos scrape.do
# ------------------------------------------------------------
def buscar_preco_shibata(produto) -> float:
    """
    Consulta a API interna da Shibata (vipcommerce) diretamente.
    Extrai o produto_id da URL e localiza o item pelo ID no retorno JSON.
    Custo scrape.do: 0 créditos.
    """
    url_produto = produto["url"]
    nome        = produto["nome"]

    # Extrai o produto_id da URL: /produto/11622/slug
    match_id = re.search(r'/produto/(\d+)/', url_produto)
    if not match_id:
        raise Exception(f"produto_id não encontrado na URL: {url_produto}")
    produto_id = int(match_id.group(1))

    # Usa a primeira palavra do nome como termo de busca
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
        # A API retorna tanto 'id' quanto 'produto_id'; verifica os dois
        if p.get("produto_id") == produto_id or p.get("id") == produto_id:
            oferta       = p.get("oferta") or {}
            preco_oferta = oferta.get("preco_oferta")
            preco_base   = p.get("preco") or 0
            preco = float(preco_oferta) if (p.get("em_oferta") and preco_oferta) else float(preco_base)
            print(f"   ✅ [API Shibata] Produto encontrado: R$ {preco:.2f}")
            return preco

    raise Exception(f"Produto ID {produto_id} não encontrado na resposta da API Shibata")


# ------------------------------------------------------------
# MONITOR PRINCIPAL
# ------------------------------------------------------------
def monitorar_produto(produto, titulo_alerta, metodo, token, chat_id):
    nome = produto["nome"]
    url  = produto["url"]
    alvo = produto["alvo"]

    print(f"\n{'='*60}")
    print(f"📦 {nome}")
    print(f"   Alvo: R$ {alvo:.2f} | Método: {metodo}")
    print(f"{'='*60}")

    if metodo == "shibata_api":
        preco = buscar_preco_shibata(produto)
    else:
        preco = buscar_preco_scrape(produto)

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
        titulo_alerta = site["titulo_alerta"]
        metodo        = site["metodo"]
        produtos      = site["produtos"]

        print(f"\n{'#'*60}")
        print(f"# {titulo_alerta}  [{metodo}]")
        print(f"{'#'*60}")

        for produto in produtos:
            try:
                monitorar_produto(produto, titulo_alerta, metodo, token, chat_id)
            except Exception as e:
                print(f"\n❌ ERRO em '{produto['nome']}': {e}")
                erros.append((produto["nome"], str(e)))
            time.sleep(3)

    if erros:
        print(f"\n⚠️ {len(erros)} produto(s) com erro:")
        for nome, err in erros:
            print(f"   • {nome}: {err}")
    else:
        print("\n✅ Monitoramento concluído sem erros.")


if __name__ == "__main__":
    main()
