import os
import re
import time
import sys

try:
    from curl_cffi import requests
except ImportError:
    raise ImportError("Instale curl_cffi: pip install curl_cffi")

# ============================================================
# CONFIGURAÇÕES SHOPEE
# ============================================================
SHOPEE_IMG_BASE = "https://down-br.img.susercontent.com/file"
ARQUIVO_ITENS = "listadeitens.js"
IMPERSONATE = "chrome120"  # Perfil TLS usado pelo curl_cffi

# 💡 Cole seus cookies do navegador aqui para evitar o erro 90309999
# F12 → Network → qualquer página da Shopee → header "Cookie"
SHOPEE_COOKIES = os.environ.get("SHOPEE_COOKIES", "")


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
# API SHOPEE  —  espelha o fetch() do JS com credentials:"include"
# ============================================================
def _get_csrf_token_from_cookies(raw_cookies: str) -> str:
    """
    Replica o getCookie("csrftoken") do JS:
        const match = document.cookie.match(/(^| )csrftoken=([^;]+)/);
    """
    match = re.search(r'(?:^|;)\s*csrftoken=([^;]+)', raw_cookies)
    return match.group(1) if match else ""


def buscar_preco_shopee(url_produto):
    # --- extrai shop_id e item_id da URL (igual ao JS que usa a URL atual da aba) ---
    match = re.search(r'i\.(\d+)\.(\d+)', url_produto)
    if not match:
        match = re.search(r'product/(\d+)/(\d+)', url_produto)
    if not match:
        raise Exception(f"shop_id e item_id não encontrados na URL: {url_produto}")

    shop_id = match.group(1)
    item_id = match.group(2)

    # --- monta sessão com impersonação TLS (curl_cffi) ---
    session = requests.Session(impersonate=IMPERSONATE)

    # Equivalente a credentials:"include" — injeta todos os cookies ativos
    if SHOPEE_COOKIES:
        for cookie in SHOPEE_COOKIES.split(";"):
            if "=" in cookie:
                k, v = cookie.strip().split("=", 1)
                session.cookies.set(k.strip(), v.strip(), domain=".shopee.com.br")
    else:
        # Fallback sem cookies: sujeito ao erro 90309999 (anti-bot)
        try:
            session.get("https://shopee.com.br/", timeout=15)
        except Exception as e:
            print(f"⚠️ Aviso: não foi possível obter cookies iniciais: {e}")

    # --- obtém csrftoken do cookie, exatamente como o getCookie() do JS ---
    raw_cookies = "; ".join(
        f"{c.name}={c.value}" for c in session.cookies
    )
    csrf_token = _get_csrf_token_from_cookies(raw_cookies)
    print(f"🔑 csrftoken: {'✅ ' + csrf_token[:10] + '...' if csrf_token else '❌ vazio'}")

    # --- headers idênticos ao fetch() do JS (sem User-Agent/Referer explícitos) ---
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-CSRFToken": csrf_token,          # ← mesmo que o JS
        "X-Requested-With": "XMLHttpRequest",
        "X-Shopee-Language": "pt-BR",
        "X-API-SOURCE": "rweb",
    }

    # --- URL igual à usada no JS ---
    api_url = (
        f"https://shopee.com.br/api/v4/pdp/get_rw?"
        f"display_model_id={item_id}&item_id={item_id}&shop_id={shop_id}"
        f"&tz_offset_in_minutes=-180&detail_level=0"
        f"&incoming_pdp_page_source=0&incoming_pdp_page_scenario=0"
    )

    print(f"🔗 API URL Shopee: {api_url}")

    response = session.get(api_url, headers=headers, timeout=20)

    if response.status_code == 403:
        print(f"❌ Bloqueio 403 — conteúdo: {response.text[:300]}")
        raise Exception("API Shopee retornou status 403 (bloqueio de IP ou token expirado)")

    if response.status_code != 200:
        raise Exception(f"API Shopee retornou status {response.status_code}")

    res_json = response.json()

    # Validação do erro 90309999 (anti-bot) — igual ao check do JS
    if "error" in res_json and res_json.get("error") != 0:
        raise Exception(
            f"Erro da API Shopee: {res_json.get('error')} "
            f"(Anti-bot ativo. Atualize os COOKIES)"
        )

    data = res_json.get("data", {})
    if not data:
        raise Exception(f"Dados do item {item_id} não encontrados no JSON")

    stock = data.get("stock", 0)
    if stock == 0:
        raise ProdutoIndisponivelException(f"Produto {item_id} está esgotado/indisponível.")

    raw_price = data.get("price") or data.get("price_min", 0)
    preco = float(raw_price) / 100000.0

    descricao = data.get("title") or data.get("name") or f"Produto {item_id}"
    imagem_arquivo = data.get("image")
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

    print("\n🚀 INICIANDO MONITOR SHOPEE\n")
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
