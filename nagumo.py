import os
import re
import time
import sys
import requests

# ============================================================
# CONFIGURAÇÕES NAGUMO
# ============================================================
NAGUMO_API_URL = "https://www.nagumo.com.br/on/demandware.store/Sites-Nagumo-Site/pt_BR/Product-Variation"

# O cookie 'dw_store' força a filial desejada (Ex: 22)
NAGUMO_COOKIES = {
    "dw_store": "22",
    "dw_consent": "tracking=false",
    "__cq_dnt": "1",
    "dw_dnt": "1"
}

NAGUMO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest"
}

TITULO_ALERTA = "🔥🛒 ALERTA NAGUMO!"

# ============================================================
# PRODUTOS MONITORADOS (Suporta links únicos e Grupos)
# ============================================================
PRODUTOS = [
    (10.00, "https://www.nagumo.com.br/categoria/departamentos/hortifruti/legumes/tuberculos/cenoura-13772.html"),
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
        print(f"⚠️ Erro Telegram (texto): {e}")

def enviar_telegram_foto(token, chat_id, foto_url, caption, nome_arquivo):
    if not token or not chat_id:
        print("⚠️ Telegram não enviado: Variáveis de ambiente faltando.")
        return
    try:
        img_resp = requests.get(foto_url, timeout=20)
        if not img_resp.ok:
            raise Exception(f"Erro ao baixar imagem: {img_resp.status_code}")
        
        filename_limpo = re.sub(r'[\\/*?:"<>|]', "", nome_arquivo).strip()
        filename = f"{filename_limpo}.jpg"

        url = f"https://api.telegram.org/bot{token}/sendDocument"
        data = {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}
        files = {"document": (filename, img_resp.content)}
        
        resp = requests.post(url, data=data, files=files, timeout=30)
        if not resp.ok:
            raise Exception(f"sendDocument retornou {resp.status_code}")
    except Exception as e:
        print(f"⚠️ Erro Telegram (foto): {e} — enviando apenas texto.")
        enviar_telegram(token, chat_id, caption)

# ============================================================
# API NAGUMO
# ============================================================
def buscar_preco_nagumo(url):
    # Captura o ID tanto do formato de URL comum quanto do parâmetro pid=
    match_id = re.search(r'(?:-|\bpid=)(\d+)(?:\.html|\b|$)', url)
    if not match_id:
        raise Exception(f"produto_id não encontrado na URL: {url}")
    produto_id = match_id.group(1)

    params = {"pid": produto_id}
    response = requests.get(NAGUMO_API_URL, params=params, cookies=NAGUMO_COOKIES, headers=NAGUMO_HEADERS, timeout=15)
    
    if response.status_code != 200:
        raise Exception(f"API Nagumo retornou status {response.status_code}")

    dados = response.json()
    
    # Extração do Preço procurando especificamente a flag da loja 22
    preco = 0
    flagtypes = dados.get("flagtypes", [])
    
    for flag in flagtypes:
        flag_type = flag.get("flagType", "")
        if "_22_" in flag_type or flag_type.startswith("NGM_22"):
            preco = float(flag.get("valueFlag") or 0)
            break
            
    # Fallback caso não encontre a flag da loja 22 na lista
    if preco == 0 and flagtypes:
        preco = float(flagtypes[0].get("valueFlag") or 0)
        
    if preco == 0:
        preco = float(dados.get("product", {}).get("price", {}).get("sales", {}).get("value") or 0)

    if preco == 0:
        raise Exception(f"Não foi possível obter o preço para o ID {produto_id}")

    # Extração do Nome e Imagem do produto
    product_data = dados.get("product", {})
    descricao = product_data.get("productName") or f"Produto {produto_id}"
    
    images = product_data.get("images", {}).get("large", [])
    imagem_url = images[0].get("url") if images else None

    return preco, descricao, imagem_url

# ============================================================
# MONITOR CORE
# ============================================================
def monitorar_grupo(alvo, urls, token, chat_id):
    print(f"\n📦 Monitorando Grupo/Item | Alvo: R$ {alvo:.2f}")
    atingiram = []
    erros = 0

    for url in urls:
        print(f"   🔍 {url}")
        try:
            preco, nome_real, imagem_url = buscar_preco_nagumo(url)
            print(f"   💰 {nome_real} — R$ {preco:.2f}")
            if preco <= alvo:
                atingiram.append({"nome": nome_real, "url": url, "preco": preco, "imagem_url": imagem_url})
                print("   ✅ Abaixo do alvo!")
        except Exception as e:
            print(f"   ❌ Erro: {e}")
            erros += 1
        time.sleep(1.5)

    if atingiram:
        for p in atingiram:
            caption = (
                f"<b>{TITULO_ALERTA}</b>\n\n"
                f'👉 <a href="{p["url"]}">{p["nome"]}</a>\n\n'
                f"💰 Preço: <b>R$ {p['preco']:.2f}</b>\n"
                f"🎯 Alvo:  <b>R$ {alvo:.2f}</b>"
            )
            if p["imagem_url"]:
                enviar_telegram_foto(token, chat_id, p["imagem_url"], caption, p["nome"])
            else:
                enviar_telegram(token, chat_id, caption)
    
    return erros == len(urls)

def main():
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    falhas_totais = 0

    print("\n🚀 INICIANDO MONITOR NAGUMO")
    for entrada in PRODUTOS:
        alvo = entrada[0]
        urls = entrada[1:]
        falhou = monitorar_grupo(alvo, urls, token, chat_id)
        if falhou:
            falhas_totais += 1

    if falhas_totais == len(PRODUTOS):
        sys.exit(1)

if __name__ == "__main__":
    main()
