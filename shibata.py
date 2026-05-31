import os
import re
import time
import sys
import requests

# ============================================================
# CONFIGURAÇÕES SHIBATA
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
TITULO_ALERTA = "🔥🛒 ALERTA SHIBATA!"
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
        # Identifica se a linha é um link do Shibata
        if linha.startswith("http") and "loja.shibata.com.br" in linha:
            url_shibata = linha
            alvo = None
            
            # Sobe as linhas anteriores para encontrar o preço alvo correspondente
            for i in range(idx - 1, -1, -1):
                if not linhas[i].startswith("http") and "," in linhas[i]:
                    try:
                        alvo = float(linhas[i].split(",")[1].strip())
                        break
                    except ValueError:
                        continue
            
            if alvo is not None:
                # Procura se já existe um grupo com este preço alvo para agrupar
                grupo_existente = False
                for item in produtos_carregados:
                    if item[0] == alvo:
                        # Evita duplicar o mesmo link no grupo
                        if url_shibata not in item[1:]:
                            item.append(url_shibata)
                        grupo_existente = True
                        break
                
                if not grupo_existente:
                    produtos_carregados.append([alvo, url_shibata])

    # Converte as listas internas para tuplas para manter compatibilidade com o core
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
            
        filename = "item.jpg"

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
# API SHIBATA
# ============================================================
def buscar_preco_shibata(url):
    match_id = re.search(r'/produto/(\d+)/', url)
    if not match_id:
        raise Exception(f"produto_id não encontrado na URL: {url}")
    produto_id = match_id.group(1)

    api_url = (
        f"https://services.vipcommerce.com.br/api-admin/v1/org/{SHIBATA_ORG_ID}"
        f"/filial/1/centro_distribuicao/1/loja/produtos/{produto_id}/detalhes"
    )

    response = requests.get(api_url, headers=SHIBATA_HEADERS, timeout=15)
    if response.status_code != 200:
        raise Exception(f"API Shibata retornou status {response.status_code}")

    produto = response.json().get("data", {}).get("produto", {})
    if not produto:
        raise Exception(f"Produto ID {produto_id} não encontrado")

    # Lógica de fallback para preço original e preço promocional
    preco_original = produto.get("preco_original")
    if preco_original and float(preco_original) > 0:
        preco = float(preco_original)
    else:
        preco = float(produto.get("preco") or 0)

    descricao = produto.get("descricao") or f"Produto {produto_id}"

    imagem_arquivo = produto.get("imagem")
    imagem_url = f"{SHIBATA_IMG_BASE}/{imagem_arquivo}" if imagem_arquivo else None

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
            preco, nome_real, imagem_url = buscar_preco_shibata(url)
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
                f'👉<a href="{p["url"]}">{p"nome"}</a>\n\n'
                f"💰Preço: <b>R$ {p['preco']:.2f}</b>\n"
                f"🎯Alvo:  <b>R$ {alvo:.2f}</b>"
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

    print("\n🚀 INICIANDO MONITOR SHIBATA")
    
    # Busca a lista dinâmica mapeada do arquivo de texto
    produtos_monitorados = carregar_produtos_txt(ARQUIVO_ITENS)
    
    if not produtos_monitorados:
        print("❌ Nenhum produto válido do Shibata foi encontrado na lista.")
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
