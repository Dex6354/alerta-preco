import os
import re
import time
import sys
import requests

# ============================================================
# CONFIGURAÇÕES SHOPEE (Atualizado com seus tokens do F12)
# ============================================================
SHOPEE_HEADERS = {
    "accept": "application/json",
    "accept-language": "pt-BR,pt;q=0.5",
    "content-type": "application/json",
    "x-api-source": "pc",
    "x-shopee-language": "pt-BR",
    "x-requested-with": "XMLHttpRequest",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "x-csrftoken": "mLHMHuzk1TUmVL1ur5YKo7T2Dr96UqcW",
    "af-ac-enc-dat": "7c20e5b5271f2f62",
    "af-ac-enc-sz-token": "z9cCWO9Hn9/rbWumTfhb/w==|axvWtWyU0tuCsDiFjJ3FfR1XwUtC4hoLPDOp7wRPGyWRsg9W1yYMPCqgKCBNQ/oDTvozYqofq+hu9nawrScQ|iBeow5EZe7utAPkj|08|3",
    "x-sap-ri": "94a3286a313715861d4aee3a0a0114a5b90d7bd68d15c149307a",
    "x-sap-sec": "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",
    "cookie": "_sapid=e5dbecf0df44c49ae08620f24740fe237f30a46b69620b14ba414a51; SPC_SI=jnYnagAAAABtTlBJWDE2eLVAHAAAAAAAbGQ3ekt4U1Q=; SPC_SEC_SI=v1-a0YwVWpnTENNSllrSWdNTnyWFMXkJQwPko8w9TW/cv7T9RJIqtDhkjswSk0sY4BzXDBdUOleF0SHg/tty/jQMxa9X03MGPx25QSju0NdcKA=; SPC_F=7Z6Q9SkMZDox1oR0Ii8J0826fC1LVmkV; REC_T_ID=df2d71de-6459-11f1-8c93-4a516f446b9e; csrftoken=mLHMHuzk1TUmVL1ur5YKo7T2Dr96UqcW; ssr-tz=America/Sao_Paulo; _QPWSDCXHZQA=5f16c521-09a7-4e98-c38c-e0af47ebb954; REC7iLP4Q=2f42958e-290c-450c-b342-6785931e3c52; language=pt-BR; SPC_CLIENTID=N1o2UTlTa01aRG94jgdxnmvfmycuoiil; SPC_EC=MGZRNEU0cmlBRnJBSjROMTIjGUWJaMd+k20XNnBSLNwAi9o73/vKav0ncNsmpZIUGDRfrTwl0x2Ofwwkp7Z818GJ+yPA/ZMukOcLEx2xqjmNugu5njDl2dBX5SRtAXQ8xlZFdgqn8Rs6BlzJU2QGHfYDssd8baEPayuRZn3NxmOlvi9FE2/hEAd2N1ka+0CCpDrrMCEHoIQ2z3mosKRzCw==.AKO/79S5x3FV5c4Ak52lE4lJvM6aSEcvu0SbcicX7Vpm; SPC_ST=b2JENmhEQTRjTkJIbXA5d8KVpVU015Q9De4SYFvRnkYdEyUiZtzGdyYrLSxYbqBlfCsrlj+SG7XnlBDYGwDmb5R+QEuAkHMNP08jIYjIL93pjOFYx5lJSKe7fBRejvMeeFoJNKcNFbMlZIpRPnYFf6eg/6D9OnZmBU32UgIZGvzI8Qh0uedt2M060BckjGlP/eSeLnHOlbpu7Eq0dzCF2Q==.AKADiCJvkpyMEonPulApzfsELparM++xJgSHLYPbIoMF; SPC_U=1287911842; SPC_T_ID=Yksys4nRzXNM7qi8X2MdlvlGeqhTPvJLw+m5WNGkZvW5/4PKw+Yk9m+aaK89rQQYfwmbnVXWaCG4PGFMbPG87ihNxS4sR6tFeJJkn8VdUk7ae9gRWikZ8t/LGmIojuWkWOfJ3JwqrUKD6thBI96Q/1x78XRa9D/1MTTJdyiHpkQ=; SPC_T_IV=VzVPd3c2WGo4dlNXdUNmYg==; SPC_R_T_ID=Yksys4nRzXNM7qi8X2MdlvlGeqhTPvJLw+m5WNGkZvW5/4PKw+Yk9m+aaK89rQQYfwmbnVXWaCG4PGFMbPG87ihNxS4sR6tFeJJkn8VdUk7ae9gRWikZ8t/LGmIojuWkWOfJ3JwqrUKD6thBI96Q/1x78XRa9D/1MTTJdyiHpkQ=; SPC_R_T_IV=VzVPd3c2WGo4dlNXdUNmYg==; SPC_IA=1; SPC_CDS_CHAT=6a97c807-e861-45a4-a37d-6eb3d3070995; AC_CERT_D=gqRjZGVrxHeFomtpuDE0MjUxOmNhcHRjaGFfY29va2llX2tleaJrdtEAAaRhbGdv0gAAAGSjZGVrwKJjdMRAAAAADIuMoXpgfbLg2vIC60fpVOLfZRKlV5ZfR9lIUiuFOKYtqqYoXpgK4bnsfkAcNUbyV3vNcNTgJXHGDgTEVqpjaXBoZXJ0ZXh0xQNAAAAADHkDCu83tcul3QA7hAYamolMfOr40HSmk+qU6VXGT3zvyvnOuM7O7WuaY6JzZafEOwNLt0FriyBX/hWZbvggaPYdrSW9qpsNAbG8tcS9TOAJTGbFxotsftruGtXa51Zscg770zyz/w0LzfJRcsm72yhVd6vCTRC6NGQJQQFZF7THcf4N9ODbRzSWylWgbaQEIheFTfGnLtfsKpo7v5xVScS62KAENX01MIJFfRfEe+2sgh4k1hTjycX3BHelIkG+vvh5Da3QCWTv46m7Vhu4ryPNr6xSkN/D0+RoRY96IJGpAp8PNC4I2ApfeFXJl3mX8A392gMhtPm2CHC0iqsHFZQ6N4hKb016G5IJdwZ9fU7De7KwB5m//Ac53pxUEQN8ToabcBX2Vga0LLhckblYcq3W6KAWFsNYbvbISUkLWGi6HQDAu5VYE7ArfnniYWrQDya1yRkZJY78U5JtEtFc5pYi5D8mkmkifU6e+vIYVjqwJzVbjtoyaHMsWQfnDn6iCyR9Pn+aPKlxrZKtHUUsV9Ky335HEr/nfgGnDPwVYEvRiN/zqWtAfp/xdePH3accDBGZGwAPcQomdA/Bi/u45+oga7iFG8p3tjqFX0dSmFoztjz8XwEJ+IcBky4Hf6GZELGAXvnSLEJycUp0P3vcQN7bZSUzcApxDUu+oFB3P4wOqO8vQpnNIeMahpgB0n+NSsxek0spfdOhOQJj8qjJ0K0lW4ETXbslPRHpya9yZCM4WA6rSBbiKxQfANXyPqaU8XdsCuXK9q6XVEbRpqBfrl6qsnj44Q5iF90/sSDKy9++qY0dggXbWEeWer1KxO3RqV4ED+dzr7neo3ZgTiW/vM3wDT5zR4CFMKAyBg5unU4hCl0qNGxnyiZ68dU9DLPet0XfF10BdiyKl4FpH5611SJG5ALexcnF7iv9s0y6nDaD1Zo13HHOHGCuL1Ht17TrLn27E0+lnHpBW/98Sr2wWXOgfXdqVj/KG884lmFm0USufoSbxSGLvFf50cmcIQtA06mwyVJzaHfEVkQCYwa4ht2x+qRQ0tGN7iI+zJqZeJOJjJB01y1UWTcF8vwUuUJvT6buha0CCmeJXuHrQw==; shopee_webUnique_ccd=z9cCWO9Hn9%2FrbWumTfhb%2Fw%3D%3D%7CaxvWtWyU0tuCsDiFjJ3FfR1XwUtC4hoLPDOp7wRPGyWRsg9W1yYMPCqgKCBNQ%2FoDTvozYqofq%2Bhu9nawrScQ%7CiBeow5EZe7utAPkj%7C08%7C3; ds=8fc5eed32a6b7255e899ea3737159e06"
}

SHOPEE_IMG_BASE = "https://down-br.img.susercontent.com/file"
ARQUIVO_ITENS = "listadeitens.js"

# Exceção customizada para identificar produto indisponível
class ProdutoIndisponivelException(Exception):
    pass

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
        if linha.startswith("http") and "shopee.com.br" in linha:
            url_shopee = linha
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
                        if url_shopee not in item[2:]:
                            item.append(url_shopee)
                        group_existente = True
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
    # Procura pelo padrão i.SHOPID.ITEMID nas URLs da Shopee
    match_id = re.search(r'i\.(\d+)\.(\d+)', url)
    if not match_id:
        raise Exception(f"shop_id ou item_id não encontrados na URL: {url}")
    
    shop_id = match_id.group(1)
    item_id = match_id.group(2)

    api_url = (
        f"https://shopee.com.br/api/v4/pdp/get_pc?item_id={item_id}&shop_id={shop_id}"
        f"&tz_offset_in_minutes=-180&detail_level=0&incoming_pdp_page_source=0&incoming_pdp_page_scenario=0"
    )
    
    print(f"🔗 API URL: {api_url}")

    response = requests.get(api_url, headers=SHOPEE_HEADERS, timeout=15)
    
    if response.status_code != 200:
        raise Exception(f"API Shopee retornou status {response.status_code}")

    res_json = response.json()
    
    # Verifica erro de anti-bot ou bloco estrutural
    if res_json.get("error") is not None and res_json.get("error") != 0:
        raise Exception(f"Shopee Anti-bot Ativado! Código Erro: {res_json.get('error')} Msg: {res_json.get('error_msg')}")

    item_data = res_json.get("data", {}).get("item", {})
    if not item_data:
        raise Exception(f"Dados do item {item_id} não localizados no JSON.")

    # Verifica estoque / disponibilidade
    if item_data.get("stock", 0) == 0:
        raise ProdutoIndisponivelException(f"Produto {item_id} está sem estoque no momento.")

    # Preço na Shopee vem em formato inteiro (ex: 2990000 = R$ 29,90). É preciso dividir por 100.000
    preco_cru = item_data.get("price") or item_data.get("price_min") or 0
    preco = float(preco_cru) / 100000

    if preco == 0:
        raise Exception("Preço do produto retornou zerado.")

    descricao = item_data.get("name") or f"Produto {item_id}"
    
    imagem_id = item_data.get("image")
    imagem_url = f"{SHOPEE_IMG_BASE}/{imagem_id}" if imagem_id else None

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
            print(f"\n💤 Produto sem estoque / ignorado.")
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
            
        time.sleep(2.5)  # Delay levemente maior para evitar taxa limite da Shopee

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

    # Processamento dos envios para o Telegram (Itens abaixo do alvo)
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
