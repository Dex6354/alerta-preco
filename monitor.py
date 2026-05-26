import os
import re
import time
import requests
from playwright.sync_api import sync_playwright


def enviar_telegram(token, chat_id, mensagem):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": mensagem, "parse_mode": "HTML"}
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Erro ao enviar mensagem para o Telegram: {e}")


def extrair_preco_do_texto(texto):
    """Extrai o primeiro valor monetário de uma string."""
    # Captura padrões como R$ 189,99 ou 189.99
    match = re.search(r"R?\$?\s*([\d]{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))", texto)
    if not match:
        return None
    valor = match.group(1)
    # Normaliza: remove ponto de milhar, troca vírgula decimal por ponto
    if "," in valor:
        valor = valor.replace(".", "").replace(",", ".")
    return float(valor)


def monitorar_preco():
    url = "https://www.centauro.com.br/conjunto-de-agasalho-oxer-replayer-981478.html?cor=05"
    alvo = 200.00
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")

    # Seletores em ordem de prioridade — o script tenta cada um
    SELETORES = [
        '[data-testid="price-current"]',
        '[data-testid="price-promotional"]',
        '[class*="priceTag"]',
        '[class*="price-current"]',
        '[class*="ProductPrice"]',
        '[class*="product-price"]',
        'span[class*="price"]',
        'div[class*="price"]',
        # Fallback genérico: qualquer span/div que contenha "R$"
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1366, "height": 768},
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            # Faz o site acreditar que há suporte a WebGL, etc.
            java_script_enabled=True,
        )

        # Remove o header "webdriver" que entrega automação
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'languages', { get: () => ['pt-BR', 'pt', 'en-US'] });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
        """)

        page = context.new_page()

        try:
            print("Abrindo página...")
            page.goto(url, wait_until="domcontentloaded", timeout=60000)

            # Aguarda a rede estabilizar (conteúdo dinâmico/JS carregar)
            page.wait_for_load_state("networkidle", timeout=30000)

            # Simula scroll para acionar lazy-load de preço
            page.evaluate("window.scrollBy(0, 500)")
            time.sleep(2)

            preco = None
            seletor_usado = None

            # --- Tentativa 1: seletores específicos ---
            for seletor in SELETORES:
                try:
                    elemento = page.locator(seletor).first
                    elemento.wait_for(state="visible", timeout=5000)
                    texto = elemento.inner_text()
                    print(f"Seletor '{seletor}' retornou: {texto!r}")
                    preco = extrair_preco_do_texto(texto)
                    if preco:
                        seletor_usado = seletor
                        break
                except Exception:
                    continue

            # --- Tentativa 2: varredura de todos os elementos com "R$" ---
            if not preco:
                print("Seletores específicos falharam. Varrendo o DOM por 'R$'...")
                elementos = page.locator("text=/R\\$\\s*\\d/").all()
                for elem in elementos[:10]:
                    try:
                        texto = elem.inner_text()
                        candidato = extrair_preco_do_texto(texto)
                        if candidato and candidato > 10:   # ignora valores muito pequenos
                            preco = candidato
                            seletor_usado = "varredura DOM"
                            print(f"Preço encontrado via varredura: {texto!r}")
                            break
                    except Exception:
                        continue

            # --- Tentativa 3: extrair do HTML completo via regex ---
            if not preco:
                print("Varrendo HTML completo por padrão de preço...")
                html = page.content()
                matches = re.findall(
                    r"R\$\s*([\d]{1,3}(?:[.,]\d{3})*[.,]\d{2})", html
                )
                candidatos = []
                for m in matches:
                    try:
                        v = float(m.replace(".", "").replace(",", "."))
                        if v > 10:
                            candidatos.append(v)
                    except ValueError:
                        continue
                if candidatos:
                    # Pega o valor mais frequente ou o menor (mais provável de ser o preço)
                    from collections import Counter
                    contagem = Counter(candidatos)
                    preco = contagem.most_common(1)[0][0]
                    seletor_usado = "regex no HTML"
                    print(f"Preço extraído do HTML: R$ {preco}")

            if not preco:
                raise ValueError(
                    "Não foi possível capturar o preço por nenhum método. "
                    "O site pode estar bloqueando ou o layout mudou."
                )

            print(f"✅ Preço capturado via [{seletor_usado}]: R$ {preco:.2f}")

            if preco <= alvo:
                msg = (
                    f"🔥 <b>Alerta de Preço!</b>\n\n"
                    f"O produto baixou para <b>R$ {preco:.2f}</b>\n"
                    f"Seu alvo é R$ {alvo:.2f}\n\n"
                    f"🔗 <a href='{url}'>Ver produto na Centauro</a>"
                )
            else:
                msg = (
                    f"✅ Monitoramento ativo.\n"
                    f"Preço atual: R$ {preco:.2f}\n"
                    f"Alvo: R$ {alvo:.2f}"
                )

            enviar_telegram(token, chat_id, msg)

        except Exception as e:
            erro_msg = f"❌ Erro na automação Centauro:\n{str(e)[:300]}"
            print(erro_msg)
            enviar_telegram(token, chat_id, erro_msg)
        finally:
            browser.close()


if __name__ == "__main__":
    monitorar_preco()
