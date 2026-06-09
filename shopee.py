import os
import re
import time
import sys

try:
    from curl_cffi import requests
except ImportError:
    raise ImportError("Instale curl_cffi: pip install curl_cffi")

# ============================================================
# ⚠️ COLE SEUS COOKIES DIRETO ENTRE AS ASPAS ABAIXO PARA TESTAR:
# ============================================================
COOKIES_LOCAL = ""

# Se a variável local estiver vazia, tenta puxar do ambiente (GitHub Secrets)
SHOPEE_COOKIES = COOKIES_LOCAL.strip() if COOKIES_LOCAL.strip() else os.environ.get("SHOPEE_COOKIES", "").strip()

# ============================================================
# CONFIGURAÇÕES SHOPEE
# ============================================================
SHOPEE_IMG_BASE = "https://down-br.img.susercontent.com/file"
ARQUIVO_ITENS = "listadeitens.js"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
IMPERSONATE = "chrome120"

class ProdutoIndisponivelException(Exception):
    pass

# ============================================================
# CARREGAR PRODUTOS DO ARQUIVO TXT / JS
# ============================================================
def carregar_produtos_txt(caminho_arquivo):
    produtos_carregados = []
    if not os.path.exists(caminho_arquivo):
        print(f"⚠️ Arquivo {caminho_arquivo} não encontrado!")
        return produtos_carregados

    with open(caminho_arquivo, "r", encoding="utf-8") as f:
        linhas = [linha.strip() for linha in f.readlines()]

    for idx, linha in enumerate(linhas):
        if linha.startswith("http") and "shopee.com.br" in linha:
            url_shopee = linha
            alvo = None
            nome_item = "Produto Shopee"

            for i in range(idx - 1, -1, -1):
                if not linhas[i].startswith("http") and "," in linhas[i]:
                    try:
                        partes = linhas[i].split(",")
                        nome_item = partes[0].strip()
                        alvo = float(partes[1].strip())
                        break
                    except ValueError:
                        continue

            if alvo is not None:
                grupo_existente = False
                for item in produtos_carregados:
                    if item[0] == alvo and item[1] == nome_item:
                        if url_shopee not in item[2:]:
                            item.append(url_shopee)
                        grupo_existente = True
                        break

                if not grupo_existente:
                    produtos_carregados.append([alvo, nome_item, url_shopee])

    return [tuple(item) for item in produtos_carregados]

# ============================================================
# TELEGRAM
# ============================================================
def enviar_telegram(token, chat_id, mensagem):
    if not token or not chat_id:
        print("⚠️ Telegram não enviado: Variáveis de ambiente faltando.")
        return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": mensagem,
            "parse_mode": "HTML",
            "link_preview_options": {"is_disabled": True}
        }
        requests.post(url, json=payload, timeout=20, impersonate=IMPERSONATE)
    except Exception as e:
        print(f"⚠️ Erro Telegram (texto): {e}")

def enviar_telegram_foto(token, chat_id, foto_url, caption, filename):
    if not token or not chat_id:
        print("⚠️ Telegram não enviado: Variáveis de ambiente faltando.")
        return
    try:
        img_resp = requests.get(foto_url, timeout=20, impersonate=IMPERSONATE)
        if not img_resp.ok:
            raise Exception(f"Erro ao baixar imagem: {img_resp.status_code}")

        url = f"https://api.telegram.org/bot{token}/sendDocument"
        data = {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}
        files = {"document": (filename, img_resp.content)}

        resp = requests.post(url, data=data, files=files, timeout=30, impersonate=IMPERSONATE)
        if not resp.ok:
            raise Exception(f"sendDocument retornou {resp.status_code}")
    except Exception as e:
        print(f"⚠️ Erro Telegram (foto): {e} — enviando apenas texto.")
        enviar_telegram(token, chat_id, caption)

# ============================================================
# API SHOPEE
# ============================================================
def buscar_preco_shopee(url_produto):
    match = re.search(r'i\.(\d+)\.(\d+)', url_produto)
    if not match:
        match = re.search(r'product/(\d+)/(\d+)', url_produto)

    if not match:
        raise Exception(f"shop_id e item_id não encontrados na URL: {url_produto}")

    shop_id = match.group(1)
    item_id = match.group(2)

    model_match = re.search(r'display_model_id(?:%22%3A|%3D|=)(\d+)', url_produto)
    display_model_id = model_match.group(1) if model_match else item_id

    session = requests.Session(impersonate=IMPERSONATE)
    csrf_token = ""

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "X-Shopee-Language": "pt-BR",
        "X-API-SOURCE": "rweb",
        "User-Agent": USER_AGENT,
        "Referer": url_produto,
        "af-ac-enc-dat": "203d9124f33fc971",
        "x-sz-sdk-version": "1.12.39",
        "x-sap-ri": "ca95286a8c05a3ea246d96370a01e7c4b4149c8ba03c8540d51d",
        "x-sap-sec": "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"
    }

    if SHOPEE_COOKIES:
        headers["Cookie"] = SHOPEE_COOKIES
        csrf_match = re.search(r'csrftoken=([^;]+)', SHOPEE_COOKIES)
        csrf_token = csrf_match.group(1) if csrf_match else "w2nwOL9o7nYtJQ2yI8TFF2wVN8zZfSbT"
    else:
        print("⚠️ Alerta: Executando sem cookies mapeados.")
        csrf_token = "w2nwOL9o7nYtJQ2yI8TFF2wVN8zZfSbT"

    headers["X-CSRFToken"] = csrf_token
    print(f"🔑 Cookies injetados. csrftoken ativo: {csrf_token[:10]}...")

    api_url = (
        f"https://shopee.com.br/api/v4/pdp/get_rw?"
        f"display_model_id={display_model_id}&item_id={item_id}&shop_id={shop_id}"
        f"&tz_offset_in_minutes=-180&detail_level=0"
        f"&incoming_pdp_page_source=0&incoming_pdp_page_scenario=0"
    )

    print(f"🔗 API URL Shopee: {api_url}")
    response = session.get(api_url, headers=headers, timeout=20)

    if response.status_code == 403:
        print(f"❌ Bloqueio 403 — conteúdo: {response.text[:300]}")
        raise Exception("API Shopee retornou status 403 (Sua sessão expirou ou os cookies estão mal formatados)")

    if response.status_code != 200:
        raise Exception(f"API Shopee retornou status {response.status_code}")

    res_json = response.json()
    if "error" in res_json and res_json.get("error") is not None:
        raise Exception(f"Erro da API Shopee: {res_json.get('error')} (Anti-bot barrou o cabeçalho)")

    data = res_json.get("data", {})
    if not data:
        raise Exception(f"Dados do Item {item_id} não encontrados no JSON")

    stock = data.get("item", {}).get("stock", 1)
    if stock == 0:
        raise ProdutoIndisponivelException(f"Produto {item_id} está esgotado/indisponível.")

    raw_price = data.get("item", {}).get("price", 0) or data.get("item", {}).get("price_min", 0)
    preco = float(raw_price) / 100000.0

    descricao = data.get("item", {}).get("title") or f"Produto {item_id}"
    imagem_arquivo = data.get("item", {}).get("image")
    imagem_url = f"{SHOPEE_IMG_BASE}/{imagem_arquivo}" if imagem_arquivo else None

    return preco, descricao, imagem_url

# ============================================================
# MONITOR CORE
# ============================================================
def monitorar_grupo(alvo, nome_item, urls, token, chat_id):
    atingiram = []
    erros = 0

    for url in urls:
        print(f"🔍 Monitorando Alvo:")
        print(f"{nome_item}, R$ {alvo:.2f}\n")
        print(f"🛒 Item:\n{url}")
        try:
            preco, nome_real, imagem_url = buscar_preco_shopee(url)
            print(f"\n🛒 {nome_real}")
            print(f"💰 R$ {preco:.2f} | 🎯 R$ {alvo:.2f}")
            if preco <= alvo:
                atingiram.append({
                    "nome": nome_real,
                    "nome_arquivo": nome_item,
                    "url": url,
                    "preco": preco,
                    "imagem_url": imagem_url,
                    "alvo": alvo
                })
                print("✅ Abaixo do alvo!")
                print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            else:
                print("ℹ️ Acima do alvo")
                print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        except ProdutoIndisponivelException:
            print(f"\n💤 Produto indisponível/esgotado ignorado.")
            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        except Exception as e:
            print(f"\n❌ Erro: {e}")
            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            erros += 1
            msg_erro = (
                f"<b>━━━━ ❌ ERRO SHOPEE ━━━━</b>\n"
                f"🛒 <a href='{url}'>{nome_item}</a>\n"
                f"⚠️ Falha ao consultar o item\n"
                f"<b>━━━━━━━━━━━━━━━━━━━━</b>"
            )
            enviar_telegram(token, chat_id, msg_erro)

        time.sleep(3.0)

    return atingiram, (erros == len(urls))

def main():
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    falhas_totais = 0
    todos_atingidos = []

    print("\n🚀 INICIANDO MONITOR SHOPEE (TESTE LOCAL)\n")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    produtos_monitorados = carregar_produtos_txt(ARQUIVO_ITENS)

    if not produtos_monitorados:
        print("❌ Nenhum produto válido da Shopee foi encontrado na lista.")
        sys.exit(1)

    for entrada in produtos_monitorados:
        alvo = entrada[0]
        nome_item = entrada[1]
        urls = entrada[2:]
        atingiram, falhou = monitorar_grupo(alvo, nome_item, urls, token, chat_id)
        if falhou:
            falhas_totais += 1
        todos_atingidos.extend(atingiram)

    if todos_atingidos:
        for p in todos_atingidos:
            caption = (
                f"<b>━━━━ ✅ SHOPEE ━━━━━━━</b>\n"
                f"🛒 <a href='{p['url']}'>{p['nome_arquivo']}</a>\n"
                f"💰 <b>R$ {p['preco']:.2f}</b> | 🎯 <b>R$ {p['alvo']:.2f}</b>\n"
                f"<b>━━━━━━━━━━━━━━━━━━━━</b>"
            )
            if p["imagem_url"]:
                filename = f"Shopee-{p['nome_arquivo']}-R${p['preco']:.2f}.jpg"
                enviar_telegram_foto(token, chat_id, p["imagem_url"], caption, filename)
            else:
                enviar_telegram(token, chat_id, caption)
            time.sleep(1)

    if falhas_totais == len(produtos_monitorados):
        sys.exit(1)

if __name__ == "__main__":
    main()
