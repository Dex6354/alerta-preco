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
# CONFIGURAÇÕES CENTAURO
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
        if linha.startswith("http") and "centauro.com.br" in linha:
            url_centauro = linha
            alvo = None
            nome_item = "Produto"
            
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
                        if url_centauro not in item[2:]:
                            item.append(url_centauro)
                        grupo_existente = True
                        break
                
                if not grupo_existente:
                    produtos_carregados.append([alvo, nome_item, url_centauro])

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

def enviar_telegram_foto(token, chat_id, foto_url, caption, filename):
    if not token or not chat_id:
        print("⚠️ Telegram não enviado: Variáveis de ambiente faltando.")
        return
    try:
        img_resp = requests.get(foto_url, timeout=20)
        if not img_resp.ok:
            raise Exception(f"Erro ao baixar imagem: {img_resp.status_code}")

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
# API SCRAPER
# ============================================================
def extrair_codigo_cor(url_produto):
    codigo_match = re.search(r'-([a-zA-Z0-9]+?)(?:-mktp)?\.html', url_produto)
    if not codigo_match:
        raise ValueError(f"Código não encontrado na URL")
    
    cor_match = re.search(r'[?&]cor=(\w+)', url_produto)
    if not cor_match:
        raise ValueError(f"Parâmetro 'cor' não encontrado")
        
    return codigo_match.group(1), cor_match.group(1)

def buscar_preco_centauro(url_produto, codigo, cor, max_tentativas=3):
    api_url = f"{CENTAURO_API_BASE}/{codigo}?color={cor}"
    print(f"\n🔗 API Centauro:\n{api_url}")

    for tentativa in range(1, max_tentativas + 1):
        try:
            s = curl_requests.Session(impersonate="chrome")
            resp = s.get(api_url, headers=CENTAURO_HEADERS, timeout=30)

            if resp.status_code == 403:
                raise Exception("403 Forbidden (Akamai)")
            if resp.status_code != 200:
                raise Exception(f"Status {resp.status_code}")

            data = resp.json()
            product_data = data.get("product", {})
            
            if product_data.get("isAvailable") is False:
                raise ValueError("PRODUTO_INDISPONIVEL")

            nome_api = product_data.get("name") or "Produto Centauro"
            sizes = product_data.get("sizes", [])

            visual_medias = product_data.get("visualMedias", [])
            imagem_url = None
            for media in visual_medias:
                if media.get("type") == "image" and media.get("url"):
                    imagem_url = media.get("url")
                    break

            if not sizes and product_data.get("priceInfos"):
                sizes = [{"priceInfos": product_data.get("priceInfos"), "hasStock": True}]

            precos = []
            for item in sizes:
                if not item.get("hasStock", False):
                    continue
                pi = item.get("priceInfos", {})
                if not pi:
                    continue

                pix = pi.get("pixDiscount", {})
                if pix and pix.get("price"):
                    precos.append(float(pix["price"]))
                elif pi.get("promotionalPrice"):
                    precos.append(float(pi["promotionalPrice"]))
                elif pi.get("price"):
                    precos.append(float(pi["price"]))

            if precos:
                return min(precos), nome_api, imagem_url

            raise Exception("Nenhum preço disponível encontrado")
        except ValueError as ve:
            if str(ve) == "PRODUTO_INDISPONIVEL":
                raise ve
        except Exception as e:
            print(f"   ❌ Tentativa {tentativa}/{max_tentativas}: {e}")
            if tentativa < max_tentativas:
                time.sleep(5 * tentativa)

    raise Exception(f"Falha após {max_tentativas} tentativas")

# ============================================================
# MONITOR CORE
# ============================================================
def verificar_url_unica(alvo, nome_item, url, token=None, chat_id=None):
    print(f"🔍 Monitorando Alvo:")
    print(f"{nome_item}, R$ {alvo:.2f}")
    print(f"\n👕 Item:\n{url}")
    
    try:
        codigo, cor = extrair_codigo_cor(url)
        preco, nome_real, imagem_url = buscar_preco_centauro(url, codigo, cor)
        
        print(f"\n👕 {nome_real}")
        print(f"💰 R$ {preco:.2f} | 🎯 R$ {alvo:.2f}")

        if preco <= alvo:
            print("✅ Abaixo do alvo!")
            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            return {
                "nome": nome_real, 
                "nome_arquivo": nome_item,
                "url": url, 
                "preco": preco, 
                "imagem_url": imagem_url, 
                "alvo": alvo
            }, True
        else:
            print("ℹ️ Preço acima do alvo.")
            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            return None, True
    except ValueError as ve:
        if str(ve) == "PRODUTO_INDISPONIVEL":
            print("\nℹ️ Produto indisponível ignorado.")
            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            return None, True
    except Exception as e:
        print(f"\n❌ Erro ao processar link: {e}")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        msg_erro = (
            f"<b>━━━ ❌ ERRO CENTAURO ━━━</b>\n"
            f"👕 <a href='{url}'>{nome_item}</a>\n"
            f"⚠️ Falha ao consultar o item\n"
            f"<b>━━━━━━━━━━━━━━━━━━━━</b>"
        )
        enviar_telegram(token, chat_id, msg_erro)
        
        return None, False

def main():
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    erros = 0
    total_links = 0
    todos_atingidos = []

    print("\n🚀 INICIANDO MONITOR CENTAURO\n")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    produtos_monitorados = carregar_produtos_txt(ARQUIVO_ITENS)
    
    if not produtos_monitorados:
        print("❌ Nenhum produto válido da Centauro foi encontrado na lista.")
        sys.exit(1)
        
    for entrada in produtos_monitorados:
        alvo = entrada[0]
        nome_item = entrada[1]
        urls = entrada[2:]
        for url in urls:
            total_links += 1
            resultado, Platform_sucesso = verificar_url_unica(alvo, nome_item, url, token, chat_id)
            if not Platform_sucesso:
                erros += 1
            if resultado:
                todos_atingidos.append(resultado)
            time.sleep(2)

    if todos_atingidos:
        for p in todos_atingidos:
            caption = (
                f"<b>━━━━ ✅ CENTAURO ━━━━━━</b>\n"
                f"👕 <a href='{p['url']}'>{p['nome_arquivo']}</a>\n"
                f"💰 <b>R$ {p['preco']:.2f}</b> | 🎯 <b>R$ {p['alvo']:.2f}</b>\n"
                f"<b>━━━━━━━━━━━━━━━━━━━━</b>"
            )
            if p["imagem_url"]:
                filename = f"Centauro-{p['nome_arquivo']}-R${p['preco']:.2f}.jpg"
                enviar_telegram_foto(token, chat_id, p["imagem_url"], caption, filename)
            else:
                enviar_telegram(token, chat_id, caption)
            time.sleep(1)

    if erros == total_links:
        sys.exit(1)

if __name__ == "__main__":
    main()
