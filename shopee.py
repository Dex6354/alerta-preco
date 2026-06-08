import os
import re
import time
import sys
import requests

# ============================================================
# CONFIGURAÇÕES SHOPEE
# ============================================================
SHOPEE_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "X-Shopee-Language": "pt-BR",
    "X-Requested-With": "XMLHttpRequest",
    "X-CSRFToken": "USYuhSWtpEpo9C2gIwuwfKMPJ7QUgdR2",
    "X-API-SOURCE": "rweb",
    "af-ac-enc-dat": "4f806e6f6eb2d216",
    "x-sz-sdk-version": "1.12.39",
    "x-sap-ri": "57f3256ac80e2889366454380a015a27bd369ef54257e5c9e8b1",
    "x-sap-sec": "hje0QfiMzlUOwWwOYIuOY5NOTIqvYkpOXIqWYP2OvDqLYPwO1DqEYOpOuIqOY52OllulY5uOgIuuY4wOiDu/YJrObIuNYJXOGIupYIwOmDuOYk2OYIuOYInKhIuOYIuOmXE/YIuOYIqAhupkYIuOYep6iwh9wluOYpAIwIuOlIwOYO2IYIuOYInHDIwOYhwIYIt74sNjCIbOYpV/CxjOYp0CmIbOYItB+aSOwQuOAIbOYeuJYItKwQuOQIbOYkXOYIqrZY7/Vs324gMooGqW5Z/j8E3aSA/gRwA/LSBBVulV4cLS2oNU53lbDvLtS8IyNpAULtnWZwmI4mcS2hX55HvfyvsVSkny+2TYL2B+auCjJlepBh+35nEjUxc4S8QmhpTNLDuObIuOYpABKswVYIamG+0CnzkFexp5JAbnZQXOYsjQ/Saq3Q3wIyDz545qDJ6b9Tcp64evkH0swYsFREjbbYXHyZSjSnPEAha3HhyxRZdlMAVLfGWJwJ3RLxsDrJwOWSJKS+PSo4LjhxqSj3jr/YwxLDWqms2xY514g3/czsnEEf9JBaUu+70RUi5GEjnX/CzK7zGh99u3QFlkWwKtFX+PCJ0400rjQOg9d/bMHWUPCEkuj3nEDk+nu6quOVsJCcHTFLp7XsAc2AkdeZTkl45mg7kxQtcMcMEOJ3xAQmh7N9+oIWDuZc2hVsd9N7kLZOobjSVhSlVGih19a82mU9RKtsnWZYAV9D8U707spgaGMtmeW4hMWxfkZAxJHKBPXr5I9cMSoWKUeTAcpsohzIETMyQX9x/ZesRIKXBVpKWfQsgc4GT3ny5OeMbWwX5ZZpTzSGpAeyKW1OLsTTIgLmJc9qq1j2KQ42nBIFlhJfa8ymWbC/+Qg1gJ7IFiOMQlstk336u4yt9ULnB5uZVGTGxktwIl44IGp/GXIuWk2/JzM/1KDh7ZDe0TOd71mmKDAtSgKzSKRoaUa3dpZKlfZaJjV58W1YFuPOMc3Ajq+2Jpb/hqwLRtxRr4c/lwjmOX4pBwRMzyCf4rpYQ2/o8khURvhAM1xN++0v0jGy8D5YBTALik/dZ5AaNG7FZqOsG9I903wijnT/vUKfeSmnV8EDT5IzdXQG6AEu9d/mleHS6ETC0hE/i75YaIdSzOYIudYQuOJnVrIri16K+SvmckC/EclzL+fbY13tXvwP3h2Px/ZmATpegvcg+mIPMoWgX8qUZy6JOyVsjl2rjyE4Iau/E+W1PP7Nf9XR2mv7bAaGlrAZVWZzVgMief9xVHEyx2saDDm4HydE/wIF+2jeWgdjAWEWJbOW2Z+XDA7l1Cf879O6eDAKB2GOgL1xm7DMfSKI96A9sy57+1aVwhisIe8XVmKngYXscA52kU5KVuHSEz+AhFkhDALzDWaC4JHIefoUH6kgCDd1X6TOPXI4zGDMHoeieMec6SX032ZYcJBBLrJNzdc0rGPTUVN+ci4/IzlHZOiwie41Evs3wqAXiunPa9/CmCKk0gSALIUkzMFvgTPNAzknXuxDwOY5XOYItUdFf8XpBb1Oq6lOhCtLqoaM70nwrLswM+HZh0FLto0pq6qj3qY4wAxrxr4UVhKTP07IuOaluOYk7qTllKqLI/8iflqZ9bXaLFBkXOgluOYkAyqzrP1F646DWvD4b0A3yBjqXTRetT7meK7ecOT/xRFq0fwG8yPoU7Sy2SQr+eYPrOYItrVX00wFb0TYU3JqQ2AWLBjYC/+HOcvyKLaJzSbNyISTVI37TQJMr4mwru3l1KilMqZ3pAlQMvoiTDudBdJVdLz2eqXAgtV8TNIbFq8b1UUnznhxVMl3EhfE5OY5zOYIuFjh4kAx6NtzXC6MforiGM+TaCljrWBn4cAS1ePdmf+v9DU9nQl60K/XFUORR5BrQEmISQ40iqY5HOYIq4u3O5O1i1wdjJkZhupbM8LBgnMOW2FGZgXcy0BjbM653G+K0zp1od7Rw5VtfxUXut+aIUehZOp3pOYIusYIuO47gatdwP/pXgYIuO6oQNHU62bBxUqybdop/QP1pmM+MAz0/IJK0HmzSp9y3S+fSLLU12lHaPxSU1yVz2IIuOYJHOYIudGLHg0u5dpEY5WVUmMf3TbroZbS9nCekPYIuOCIuOYShJbw3aJTs/ZluOYIoqarNFpkxZFUz6KwXkwsgbZ1D9T4L/qCwTLD3E0/XOaQuOYEZlinh5SJBv/Hb1svspZqM3YIuO",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

SHOPEE_IMG_BASE = "https://down-br.img.susercontent.com/file"
ARQUIVO_ITENS = "listadeitens.js"

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
# API SHOPEE
# ============================================================
def buscar_preco_shopee(url):
    # Suporta padrões: i.SHOP_ID.ITEM_ID ou product/SHOP_ID/ITEM_ID
    match = re.search(r'i\.(\d+)\.(\d+)', url)
    if not match:
        match = re.search(r'product/(\d+)/(\d+)', url)
        
    if not match:
        raise Exception(f"shop_id e item_id não encontrados na URL: {url}")
        
    shop_id = match.group(1)
    item_id = match.group(2)

    api_url = (
        f"https://shopee.com.br/api/v4/pdp/get_rw?"
        f"display_model_id={item_id}&item_id={item_id}&shop_id={shop_id}"
        f"&tz_offset_in_minutes=-180&detail_level=0&incoming_pdp_page_source=0"
    )
    
    print(f"🔗 API URL Shopee: {api_url}")

    response = requests.get(api_url, headers=SHOPEE_HEADERS, timeout=15)
    if response.status_code != 200:
        raise Exception(f"API Shopee retornou status {response.status_code}")

    data = response.json().get("data", {})
    if not data:
        raise Exception(f"Dados do Item {item_id} não encontrados no JSON")

    # Verificação de estoque total
    stock = data.get("stock", 0)
    if stock == 0:
        raise ProdutoIndisponivelException(f"Produto {item_id} está esgotado/indisponível.")

    # Preço na Shopee vem multiplicado por 100000 (Ex: R$ 10,50 vem 1050000)
    raw_price = data.get("price") or data.get("price_min", 0)
    preco = float(raw_price) / 100000.0

    descricao = data.get("title") or data.get("name") or f"Produto {item_id}"

    # Resgata a imagem principal
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
        except ProdutoIndisponivelException as e:
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
            
        time.sleep(2.0)  # Delay levemente maior para evitar blocks da Shopee

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
