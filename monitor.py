import os
import re
import time
import sys

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

SHIBATA_IMG_BASE = "https://produto-assets-vipcommerce-com-br.br-se1.magaluobjects.com/500x500"

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
                "nome": "Sorvete Bombom",
                "url": "https://www.loja.shibata.com.br/produto/11622/sorvete-bombom-jundia-pote-2l",
                "alvo": 40.00,
            },
            {
                "nome": "Leite UHT 1L",
                "alvo": 5.00,
                "urls": [
                    {
                        "url": "https://www.loja.shibata.com.br/produto/15500/leite-uht-integral-jussara-caixa-com-tampa-1l",
                    },
                    {
                        "url": "https://www.loja.shibata.com.br/produto/12987/leite-longa-vida-batavo-integral-caixa-com-tampa-1l",
                    },
                    {
                        "url": "https://www.loja.shibata.com.br/produto/11158/leite-uht-com-tampa-integral-parmalat-caixa-1l",
                    },
                ],
            },
        ],
    },
]

# ============================================================
# TELEGRAM
# ============================================================
def enviar_telegram(token, chat_id, mensagem):
    """Envia mensagem de texto simples."""
    if not token or not chat_id:
        print("⚠️ Telegram não enviado: Variáveis de ambiente faltando.")
        return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": mensagem, "parse_mode": "HTML"}
        requests.post(url, json=payload, timeout=20)
    except Exception as e:
        print(f"⚠️ Erro Telegram (texto): {e}")

def enviar_telegram_foto(token, chat_id, foto_url, caption):
    """Envia texto embutindo a foto ocultamente como miniatura pequena na lateral."""
    if not token or not chat_id:
        print("⚠️ Telegram não enviado: Variáveis de ambiente faltando.")
        return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        
        # Truque: caractere invisível (&#8203;) ancorando a foto para forçar o embed oculto
        texto_com_embed = f'<a href="{foto_url}">&#8203;</a>{caption}'
        
        payload = {
            "chat_id": chat_id,
            "text": texto_com_embed,
            "parse_mode": "HTML",
            "link_preview_options": {
                "prefer_small_media": True,  # Força imagem pequena (estilo thumbnail)
                "show_above_text": False     # Garante que fique alinhado abaixo/ao lado do texto
            }
        }
        resp = requests.post(url, json=payload, timeout=20)
        if not resp.ok:
            raise Exception(f"sendMessage (embed) retornou {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"⚠️ Erro Telegram (embed): {e} — tentando enviar só o texto.")
        enviar_telegram(token, chat_id, caption)

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

def buscar_preco_centauro(url_produto, nome_fallback="Produto", max_tentativas=3):
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

            data         = resp.json()
            product_data = data.get("product", {})

            nome_api = product_data.get("name") or nome_fallback
            sizes = product_data.get("sizes", [])

            if not sizes and product_data.get("priceInfos"):
                sizes = [{"priceInfos": product_data.get("priceInfos"), "hasStock": True, "description": "Único"}]

            precos_pix    = []
            precos_promo  = []
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
                return min(precos_pix), nome_api, None
            if precos_promo:
                return min(precos_promo), nome_api, None
            if precos_cheios:
                return min(precos_cheios), nome_api, None

            raise Exception("Nenhum preço disponível encontrado no JSON")

        except Exception as e:
            print(f"   ❌ Tentativa {tentativa}/{max_tentativas}: {e}")
            if tentativa < max_tentativas:
                time.sleep(5 * tentativa)

    raise Exception(f"Falha total após {max_tentativas} tentativa(s)")

# ============================================================
# SHIBATA — busca de preço via API
# ============================================================
def buscar_preco_shibata(nome, url):
    match_id = re.search(r'/produto/(\d+)/', url)
    if not match_id:
        raise Exception(f"produto_id não encontrado na URL: {url}")
    produto_id = match_id.group(1)

    api_url = (
        f"https://services.vipcommerce.com.br/api-admin/v1/org/{SHIBATA_ORG_ID}"
        f"/filial/1/centro_distribuicao/1/loja/produtos/{produto_id}/detalhes"
    )

    print(f"   🔄 Consultando API Shibata (produto_id={produto_id})...")
    response = requests.get(api_url, headers=SHIBATA_HEADERS, timeout=15)
    print(f"   Status HTTP: {response.status_code}")

    if response.status_code != 200:
        raise Exception(f"API Shibata retornou {response.status_code}")

    produto = response.json().get("data", {}).get("produto", {})
    if not produto:
        raise Exception(f"Produto ID {produto_id} não encontrado na API Shibata")

    preco     = float(produto.get("preco") or 0)
    descricao = produto.get("descricao") or f"Produto {produto_id}"

    imagem_arquivo = produto.get("imagem")
    imagem_url = f"{SHIBATA_IMG_BASE}/{imagem_arquivo}" if imagem_arquivo else None

    print(f"   ✅ {descricao} — R$ {preco:.2f}")
    if imagem_url:
        print(f"   🖼️  Imagem: {imagem_url}")

    return preco, descricao, imagem_url

# ============================================================
# BUSCA DE PREÇO — roteador por loja
# ============================================================
def buscar_preco(loja, nome, url):
    if loja == "centauro":
        return buscar_preco_centauro(url, nome_fallback=nome)
    elif loja == "shibata":
        return buscar_preco_shibata(nome, url)
    else:
        raise Exception(f"Loja desconhecida: '{loja}'")

# ============================================================
# MONITOR — produto com URL única
# ============================================================
def monitorar_url_unica(entrada, loja, titulo_alerta, token, chat_id):
    nome = entrada["nome"]
    url  = entrada["url"]
    alvo = entrada["alvo"]

    print(f"\n{'='*60}")
    print(f"📦 {nome}")
    print(f"   Alvo: R$ {alvo:.2f} | Loja: {loja.upper()}")
    print(f"{'='*60}")

    preco, nome_real, imagem_url = buscar_preco(loja, nome, url)
    print(f"\n💰 {nome_real} — R$ {preco:.2f} | Alvo: R$ {alvo:.2f}")

    if preco <= alvo:
        caption = (
            f"<b>{titulo_alerta}</b>\n\n"
            f'<a href="{url}">{nome_real}</a>\n\n'
            f"Preço: <b>R$ {preco:.2f}</b>\n"
            f"Alvo:  <b>R$ {alvo:.2f}</b>"
        )
        if imagem_url:
            enviar_telegram_foto(token, chat_id, imagem_url, caption)
        else:
            enviar_telegram(token, chat_id, caption)
        print("📤 Alerta enviado!")
    else:
        print("ℹ️  Preço acima do alvo — sem alerta.")

# ============================================================
# MONITOR — grupo de URLs com alvo compartilhado
# ============================================================
def monitorar_urls_compartilhadas(entrada, loja, titulo_alerta, token, chat_id):
    nome_grupo = entrada["nome"]
    alvo       = entrada["alvo"]
    urls       = entrada["urls"]

    print(f"\n{'='*60}")
    print(f"📦 GRUPO: {nome_grupo}  |  Alvo compartilhado: R$ {alvo:.2f} | Loja: {loja.upper()}")
    print(f"{'='*60}")

    atingiram = []
    erros     = []

    for item in urls:
        url  = item["url"]
        nome = item.get("nome", url)
        print(f"\n   🔍 {url}")
        try:
            preco, nome_real, imagem_url = buscar_preco(loja, nome, url)
            print(f"   💰 {nome_real} — R$ {preco:.2f} | Alvo: R$ {alvo:.2f}")
            if preco <= alvo:
                atingiram.append({"nome": nome_real, "url": url, "preco": preco, "imagem_url": imagem_url})
                print("   ✅ Abaixo do alvo!")
            else:
                print("   ℹ️  Acima do alvo.")
        except Exception as e:
            print(f"   ❌ Erro: {e}")
            erros.append((nome, str(e)))
        time.sleep(2)

    if atingiram:
        for p in atingiram:
            caption = (
                f"<b>{titulo_alerta}</b>\n"
                f"Grupo: <b>{nome_grupo}</b> | Alvo: <b>R$ {alvo:.2f}</b>\n\n"
                f'<a href="{p["url"]}">{p["nome"]}</a>\n'
                f"Preço: <b>R$ {p['preco']:.2f}</b>"
            )
            if p["imagem_url"]:
                enviar_telegram_foto(token, chat_id, p["imagem_url"], caption)
            else:
                enviar_telegram(token, chat_id, caption)

        print(f"\n📤 Alerta do grupo '{nome_grupo}' enviado ({len(atingiram)} produto(s) abaixo do alvo)!")
    else:
        print(f"\nℹ️  Nenhum produto do grupo '{nome_grupo}' atingiu o alvo.")

    return erros

# ============================================================
# MAIN
# ============================================================
def main():
    token   = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")

    erros = []

    for site in SITES:
        loja          = site["loja"]
        titulo_alerta = site["titulo_alerta"]

        print(f"\n{'#'*60}")
        print(f"# {titulo_alerta}")
        print(f"{'#'*60}")

        for entrada in site["produtos"]:
            try:
                if "url" in entrada:
                    monitorar_url_unica(entrada, loja, titulo_alerta, token, chat_id)
                elif "urls" in entrada:
                    erros_grupo = monitorar_urls_compartilhadas(entrada, loja, titulo_alerta, token, chat_id)
                    erros.extend(erros_grupo)
                else:
                    raise Exception(f"Entrada sem 'url' nem 'urls': {entrada.get('nome', '?')}")
            except Exception as e:
                print(f"\n❌ ERRO em '{entrada.get('nome', '?')}': {e}")
                erros.append((entrada.get("nome", "?"), str(e)))
            time.sleep(2)

    if erros:
        print(f"\n⚠️ {len(erros)} produto(s) com erro:")
        for nome, err in erros:
            print(f"   • {nome}: {err}")
    else:
        print("\n✅ Monitoramento concluído sem erros.")

    total_links = sum(
        1 if "url" in e else len(e.get("urls", []))
        for s in SITES for e in s["produtos"]
    )
    if erros and len(erros) == total_links:
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"💥 Erro fatal: {e}")
        sys.exit(1)
