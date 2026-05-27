import os
import re
import time
import requests
from urllib.parse import quote

# ============================================================
# CREDENCIAIS SHIBATA
# ============================================================
# Token e configurações da API Shibata (retirados do app de referência)
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
# ============================================================
SITES = [
    {
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
# MÉTODO SHIBATA API — consulta direta
# ------------------------------------------------------------
def buscar_preco_shibata(produto) -> float:
    """
    Consulta a API interna da Shibata (vipcommerce) diretamente.
    Extrai o produto_id da URL e localiza o item pelo ID no retorno JSON.
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
            oferta      = p.get("oferta") or {}
            preco_oferta = oferta.get("preco_oferta")
            preco_base  = p.get("preco") or 0
            preco = float(preco_oferta) if (p.get("em_oferta") and preco_oferta) else float(preco_base)
            print(f"   ✅ [API Shibata] Produto encontrado: R$ {preco:.2f}")
            return preco

    raise Exception(f"Produto ID {produto_id} não encontrado na resposta da API Shibata")


# ------------------------------------------------------------
# MONITOR PRINCIPAL
# ------------------------------------------------------------
def monitorar_produto(produto, titulo_alerta, token, chat_id):
    nome = produto["nome"]
    url  = produto["url"]
    alvo = produto["alvo"]

    print(f"\n{'='*60}")
    print(f"📦 {nome}")
    print(f"   Alvo: R$ {alvo:.2f} | Método: API Shibata")
    print(f"{'='*60}")

    preco = buscar_preco_shibata(produto)

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
        produtos      = site["produtos"]

        print(f"\n{'#'*60}")
        print(f"# {titulo_alerta}")
        print(f"{'#'*60}")

        for produto in produtos:
            try:
                monitorar_produto(produto, titulo_alerta, token, chat_id)
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


if __name__ == "__main__":
    main()
