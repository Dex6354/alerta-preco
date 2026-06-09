import os
import re
import time
import sys
import json
from urllib.parse import unquote

try:
    from curl_cffi import requests
except ImportError:
    raise ImportError("Instale curl_cffi: pip install curl_cffi")

# ============================================================
# CONFIGURAÇÕES SHOPEE
# ============================================================
SHOPEE_IMG_BASE = "https://down-br.img.susercontent.com/file"
ARQUIVO_ITENS = "listadeitens.js"
IMPERSONATE = "chrome120"

# --- Cookies / credenciais hardcoded para teste ---
# Substitua pelos valores do seu F12 → Network → Cookie header
SHOPEE_COOKIES = os.environ.get("SHOPEE_COOKIES", "")

# CSRF token fixo para teste (pegue do header X-CSRFToken no F12)
_CSRF_TOKEN_HARDCODED = "w2nwOL9o7nYtJQ2yI8TFF2wVN8zZfSbT"

# Headers de segurança extras que a Shopee valida no servidor
# (pegue do F12 → Network → sua requisição bem-sucedida)
_EXTRA_HEADERS = {
    "af-ac-enc-dat":  "203d9124f33fc971",
    "x-sz-sdk-version": "1.12.39",
    "x-sap-ri": "ca95286a8c05a3ea246d96370a01e7c4b4149c8ba03c8540d51d",
    "x-sap-sec": (
        "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"
    ),
}


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
# HELPERS
# ============================================================
def _get_csrf_from_string(raw: str) -> str:
    """Replica getCookie('csrftoken') do JS."""
    match = re.search(r'(?:^|;)\s*csrftoken=([^;]+)', raw)
    return match.group(1).strip() if match else ""


def extrair_ids_shopee(url_produto: str):
    """
    Extrai shop_id, item_id e display_model_id da URL.
    display_model_id vem do extraParams JSON-encoded quando presente,
    caso contrário cai back para item_id.
    """
    display_model_id = None
    match_extra = re.search(r'[?&]extraParams=([^&]+)', url_produto)
    if match_extra:
        try:
            extra = json.loads(unquote(match_extra.group(1)))
            dmid = extra.get("display_model_id")
            if dmid:
                display_model_id = str(dmid)
        except Exception:
            pass

    match = re.search(r'i\.(\d+)\.(\d+)', url_produto)
    if not match:
        match = re.search(r'product/(\d+)/(\d+)', url_produto)
    if not match:
        raise Exception(f"shop_id e item_id não encontrados na URL: {url_produto}")

    shop_id = match.group(1)
    item_id = match.group(2)

    if not display_model_id:
        display_model_id = item_id

    return shop_id, item_id, display_model_id


# ============================================================
# API SHOPEE
# ============================================================
def buscar_preco_shopee(url_produto):
    shop_id, item_id, display_model_id = extrair_ids_shopee(url_produto)
    print(f"   shop_id={shop_id} | item_id={item_id} | display_model_id={display_model_id}")

    session = requests.Session(impersonate=IMPERSONATE)

    # Injeta cookies (credentials:"include")
    if SHOPEE_COOKIES:
        for cookie in SHOPEE_COOKIES.split(";"):
            if "=" in cookie:
                k, v = cookie.strip().split("=", 1)
                session.cookies.set(k.strip(), v.strip(), domain=".shopee.com.br")

    # CSRF: tenta cookie da sessão → string bruta → hardcoded de teste
    raw_session = "; ".join(f"{c.name}={c.value}" for c in session.cookies)
    csrf_token = (
        _get_csrf_from_string(raw_session)
        or _get_csrf_from_string(SHOPEE_COOKIES)
        or _CSRF_TOKEN_HARDCODED
    )
    print(f"🔑 csrftoken: {'✅ ' + csrf_token[:10] + '...' if csrf_token else '❌ vazio'}")

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-CSRFToken": csrf_token,
        "X-Requested-With": "XMLHttpRequest",
        "X-Shopee-Language": "pt-BR",
        "X-API-SOURCE": "rweb",
        **_EXTRA_HEADERS,   # af-ac-enc-dat, x-sap-ri, x-sap-sec, x-sz-sdk-version
    }

    api_url = (
        f"https://shopee.com.br/api/v4/pdp/get_rw?"
        f"display_model_id={display_model_id}&item_id={item_id}"
        f"&model_selection_logic=3&shop_id={shop_id}"
        f"&tz_offset_in_minutes=-180&detail_level=0"
        f"&incoming_pdp_page_source=0&incoming_pdp_page_scenario=0"
    )
    print(f"🔗 API URL: {api_url}")

    response = session.get(api_url, headers=headers, timeout=20)

    if response.status_code == 403:
        print(f"❌ Bloqueio 403 — conteúdo: {response.text[:300]}")
        raise Exception("API Shopee retornou status 403 (anti-bot — atualize cookies/headers)")

    if response.status_code != 200:
        raise Exception(f"API Shopee retornou status {response.status_code}")

    res_json = response.json()

    if res_json.get("error") not in (None, 0):
        raise Exception(
            f"Erro da API Shopee: {res_json.get('error')} "
            f"(Anti-bot ativo — atualize os cookies)"
        )

    # ---- estrutura real: data.item (não data diretamente) ----
    item = res_json.get("data", {}).get("item")
    if not item:
        raise Exception(f"Campo 'data.item' não encontrado no JSON do item {item_id}")

    # Disponibilidade: campo is_unavailable ou status != 1
    if item.get("is_unavailable") or item.get("status") != 1:
        raise ProdutoIndisponivelException(f"Produto {item_id} está indisponível.")

    # Preço: procura o modelo específico (display_model_id) na lista models[]
    # Se não achar, usa price_min do item raiz
    preco = None
    imagem_modelo = None

    modelos = item.get("models", [])
    for modelo in modelos:
        if str(modelo.get("model_id")) == str(display_model_id):
            if not modelo.get("has_stock", True) is False:
                raw = modelo.get("price", 0)
                preco = float(raw) / 100000.0
                # imagem do modelo via tier_index → first_tier_variations
                break

    if preco is None:
        # fallback para price_min do item quando modelo não encontrado
        raw = item.get("price") or item.get("price_min", 0)
        preco = float(raw) / 100000.0

    # Stock geral: verifica se há algum modelo disponível
    tem_stock = any(m.get("has_stock", False) for m in modelos) if modelos else (item.get("stock") or 0) > 0
    if not tem_stock:
        raise ProdutoIndisponivelException(f"Produto {item_id} está esgotado.")

    descricao = item.get("title") or item.get("name") or f"Produto {item_id}"
    imagem_arquivo = item.get("image")
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
