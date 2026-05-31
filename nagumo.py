import os
import re
import time
import sys
import requests

# ============================================================
# CONFIGURAÇÕES NAGUMO
# ============================================================
NAGUMO_API_URL = "https://www.nagumo.com.br/on/demandware.store/Sites-Nagumo-Site/pt_BR/Product-Variation"
TITULO_ALERTA = "🔥🛒 ALERTA NAGUMO!"
ARQUIVO_ITENS = "listadeitens.js"

# ============================================================
# CARREGAR PRODUTOS DO ARQUIVO TXT
# ============================================================
def carregar_produtos_txt(caminho_arquivo):
    produtos_carregados = []
    if not os.path.exists(caminho_arquivo):
        print(f"⚠️ Arquivo {caminho_arquivo} não encontrado!")
        return produtos_carregados

    with open(caminho_arquivo, "r", encoding="utf-8") as f:
        linhas = [linha.strip() for linha in f.readlines()]

    for idx, linha in enumerate(linhas):
        if linha.startswith("http") and "nagumo.com.br" in linha:
            url_nagumo = linha
            alvo = None
            
            for i in range(idx - 1, -1, -1):
                if not linhas[i].startswith("http") and "," in linhas[i]:
                    try:
                        alvo = float(linhas[i].split(",")[1].strip())
                        break
                    except ValueError:
                        continue
            
            if alvo is not None:
                grupo_existente = False
                for item in produtos_carregados:
                    if item[0] == alvo:
                        if url_nagumo not in item[1:]:
                            item.append(url_nagumo)
                        grupo_existente = True
                        break
                
                if not grupo_existente:
                    produtos_carregados.append([alvo, url_nagumo])

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
    # Remove query strings (?pid=...) para garantir que o final termine em .html
    url_limpa = url.split("?")[0]
    
    # Captura estritamente o número após o último hífen e antes de .html no fim da URL
    match_id = re.search(r'-(\d+)\.html$', url_limpa)
    if not match_id:
        # Fallback para query string clássica caso usem a URL direta da API
        match_id = re.search(r'[?&]pid=(\d+)', url)
        
    if not match_id:
        raise Exception(f"produto_id não encontrado na URL: {url}")
        
    produto_id = match_id.group(1)

    params = {"pid": produto_id}
    
    cookies = {
        "dw_store": "22",
        "dw_consent": "tracking=false",
        "__cq_dnt": "1",
        "dw_dnt": "1"
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest"
    }

    response = requests.get(NAGUMO_API_URL, params=params, cookies=cookies, headers=headers, timeout=15)
    
    if response.status_code != 200:
        raise Exception(f"API Nagumo retornou status {response.status_code} para o ID {produto_id}")

    dados = response.json()
    
    preco = 0
    tipo_preco = "Todas Lojas"
    
    flagtypes = dados.get("flagtypes") or dados.get("product", {}).get("flagtypes") or []
    
    for flag in flagtypes:
        flag_type = str(flag.get("flagType", ""))
        if "22" in flag_type and flag.get("valueFlag") is not None:
            preco = float(flag.get("valueFlag"))
            tipo_preco = "Loja Calmon"
            break
            
    if preco == 0:
        price_sales = dados.get("product", {}).get("price", {}).get("sales", {})
        value_price = price_sales.get("value")
        if value_price is not None:
            preco = float(value_price)
            tipo_preco = "Todas Lojas"

    if preco == 0:
        raise Exception(f"Não foi possível obter o preço para o ID {produto_id}")

    product_data = dados.get("product", {})
    descricao = product_data.get("productName") or f"Produto {produto_id}"
    
    images = product_data.get("images", {}).get("large", [])
    imagem_url = images[0].get("url") if images else None

    if imagem_url:
        if "https://" in imagem_url:
            imagem_url = imagem_url[imagem_url.find("https://"):]
        elif "http://" in imagem_url:
            imagem_url = imagem_url[imagem_url.find("http://"):]
        elif imagem_url.startswith("/"):
            imagem_url = f"https://www.nagumo.com.br{imagem_url}"

    return preco, descricao, imagem_url, tipo_preco

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
            preco, nome_real, imagem_url, tipo_preco = buscar_preco_nagumo(url)
            print(f"   💰 {nome_real} — R$ {preco:.2f} [{tipo_preco}]")
            if preco <= alvo:
                atingiram.append({"nome": nome_real, "url": url, "preco": preco, "imagem_url": imagem_url, "tipo": tipo_preco})
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
                f"💰 Preço: <b>R$ {p['preco']:.2f}</b> ({p['tipo']})\n"
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
    
    produtos_monitorados = carregar_produtos_txt(ARQUIVO_ITENS)
    
    if not produtos_monitorados:
        print("❌ Nenhum produto válido do Nagumo foi encontrado na lista.")
        sys.exit(1)
        
    for entrada in produtos_monitorados:
        alvo = entrada[0]
        urls = entrada[1:]
        falhou = monitorar_grupo(alvo, urls, token, chat_id)
        if falhou:
            falhas_totais += 1

    if falhas_totais == len(produtos_monitorados):
        sys.exit(1)

if __name__ == "__main__":
    main()
