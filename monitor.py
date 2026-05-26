import os
import re
import json
import time
import random
import requests


# ─── Telegram ────────────────────────────────────────────────────────────────

def enviar_telegram(token, chat_id, mensagem):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": mensagem, "parse_mode": "HTML"}
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
    except Exception as e:
        print(f"[Telegram] Erro ao enviar: {e}")


# ─── Extração de preço ────────────────────────────────────────────────────────

def extrair_preco_vtex_state(html: str):
    """Lê o window.__STATE__ que a VTEX injeta no HTML e extrai o menor preço."""
    match = re.search(r'window\.__STATE__\s*=\s*(\{.+?\})\s*</script', html, re.DOTALL)
    if not match:
        return None
    try:
        state = json.loads(match.group(1))
        txt = json.dumps(state)
        # sellingPrice / bestPrice chegam em centavos; spotPrice em reais
        centavos = re.findall(r'"(?:sellingPrice|bestPrice)"\s*:\s*(\d+)', txt)
        reais    = re.findall(r'"spotPrice"\s*:\s*([\d.]+)', txt)
        candidatos = [int(v) / 100 for v in centavos if int(v) > 0]
        candidatos += [float(v) for v in reais if float(v) > 0]
        candidatos = [v for v in candidatos if 10 < v < 100_000]
        return min(candidatos) if candidatos else None
    except Exception as e:
        print(f"[VTEX state] parse error: {e}")
        return None


def extrair_preco_padroes(html: str):
    """Fallback: padrões genéricos no HTML (Schema.org, JSON-LD, texto R$)."""
    patterns = [
        (r'itemprop=["\']price["\'][^>]+content=["\']?([\d.]+)', 1),   # Schema.org attr
        (r'"price"\s*:\s*"?([\d]{2,5}(?:[.,]\d{2})?)"?', 1),          # JSON genérico
        (r'R\$\s*([\d]{2,3}(?:[.,]\d{3})*[.,]\d{2})', 1),             # Texto "R$ 189,99"
    ]
    for pattern, group in patterns:
        m = re.search(pattern, html, re.IGNORECASE)
        if m:
            raw = m.group(group).replace(",", ".")
            try:
                val = float(raw)
                if val > 1_000 and "," not in m.group(group):
                    val /= 100          # provavelmente centavos
                if 10 < val < 100_000:
                    return val
            except ValueError:
                continue
    return None


def extrair_preco_html(html: str):
    preco = extrair_preco_vtex_state(html)
    if preco:
        print(f"[OK] Preço via __STATE__: R$ {preco:.2f}")
        return preco
    preco = extrair_preco_padroes(html)
    if preco:
        print(f"[OK] Preço via padrão HTML: R$ {preco:.2f}")
    return preco


# ─── Método 1: requests puro ──────────────────────────────────────────────────

def capturar_via_requests(url: str):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.7,en;q=0.6",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.google.com/",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
        "Upgrade-Insecure-Requests": "1",
    }
    try:
        session = requests.Session()
        # Primeiro acessa a home para gerar cookies de sessão
        session.get("https://www.centauro.com.br/", headers=headers, timeout=20)
        time.sleep(random.uniform(1.5, 3.0))
        r = session.get(url, headers=headers, timeout=30)
        print(f"[requests] status={r.status_code} size={len(r.text)}")
        if r.status_code == 200 and len(r.text) > 10_000:
            return extrair_preco_html(r.text)
    except Exception as e:
        print(f"[requests] erro: {e}")
    return None


# ─── Método 2: undetected-chromedriver ───────────────────────────────────────

def capturar_via_uc(url: str):
    """
    Usa undetected-chromedriver que patcha o binário do Chrome para
    remover as impressões digitais de automação (a melhor defesa contra
    Cloudflare / Akamai / DataDome).
    """
    try:
        import undetected_chromedriver as uc
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1366,768")
        options.add_argument("--lang=pt-BR")

        driver = uc.Chrome(options=options, headless=True, version_main=None)
        driver.set_page_load_timeout(60)

        try:
            print("[uc] Abrindo página...")
            driver.get(url)

            # Aguarda carregamento completo (até 30 s)
            WebDriverWait(driver, 30).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            time.sleep(random.uniform(2.0, 4.0))

            # Scroll suave (dispara lazy-load)
            driver.execute_script("window.scrollBy(0, 600)")
            time.sleep(1.5)

            html = driver.page_source
            print(f"[uc] HTML capturado: {len(html)} chars")

            # 1) Tenta extrair do HTML
            preco = extrair_preco_html(html)
            if preco:
                return preco

            # 2) Tenta seletores DOM (mais rápido que regex quando o JS renderizou)
            seletores = [
                '[data-testid="price-current"]',
                '[data-testid="price-promotional"]',
                '[class*="priceTag"]',
                '[class*="price-current"]',
                '[class*="ProductPrice"]',
                'span[itemprop="price"]',
                '.price',
            ]
            for sel in seletores:
                try:
                    elem = WebDriverWait(driver, 5).until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, sel))
                    )
                    texto = elem.text
                    print(f"[uc] seletor '{sel}' → {texto!r}")
                    preco = extrair_preco_padroes(texto)
                    if preco:
                        return preco
                except Exception:
                    continue

        finally:
            driver.quit()

    except ImportError:
        print("[uc] undetected-chromedriver não instalado, pulando.")
    except Exception as e:
        print(f"[uc] erro: {e}")

    return None


# ─── Método 3: playwright-stealth ────────────────────────────────────────────

def capturar_via_playwright(url: str):
    try:
        from playwright.sync_api import sync_playwright
        from playwright_stealth import stealth_sync

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1366, "height": 768},
                locale="pt-BR",
                timezone_id="America/Sao_Paulo",
            )
            page = ctx.new_page()
            stealth_sync(page)    # ← aplica todas as patches anti-detecção

            try:
                print("[playwright] Abrindo página com stealth...")
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_load_state("networkidle", timeout=30000)
                page.evaluate("window.scrollBy(0, 600)")
                time.sleep(2)

                html = page.content()
                print(f"[playwright] HTML capturado: {len(html)} chars")
                return extrair_preco_html(html)
            finally:
                browser.close()

    except ImportError:
        print("[playwright] playwright-stealth não instalado, pulando.")
    except Exception as e:
        print(f"[playwright] erro: {e}")
    return None


# ─── Orquestrador ─────────────────────────────────────────────────────────────

def monitorar_preco():
    url    = "https://www.centauro.com.br/conjunto-de-agasalho-oxer-replayer-981478.html?cor=05"
    alvo   = 200.00
    token  = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")

    preco = None

    # Tenta cada método em cascata — para no primeiro que funcionar
    metodos = [
        ("requests puro",        lambda: capturar_via_requests(url)),
        ("undetected-chromedriver", lambda: capturar_via_uc(url)),
        ("playwright-stealth",   lambda: capturar_via_playwright(url)),
    ]

    for nome, metodo in metodos:
        print(f"\n{'='*50}")
        print(f"Tentando: {nome}")
        print('='*50)
        try:
            preco = metodo()
        except Exception as e:
            print(f"[{nome}] exceção inesperada: {e}")
        if preco:
            print(f"✅ Preço obtido via [{nome}]: R$ {preco:.2f}")
            break

    if not preco:
        erro = (
            "❌ <b>Erro na automação Centauro</b>\n\n"
            "Nenhum dos 3 métodos conseguiu capturar o preço.\n"
            "Verifique se o produto ainda está disponível ou se o layout mudou."
        )
        print(erro)
        enviar_telegram(token, chat_id, erro)
        return

    if preco <= alvo:
        msg = (
            f"🔥 <b>Alerta de Preço!</b>\n\n"
            f"Produto baixou para <b>R$ {preco:.2f}</b>\n"
            f"Seu alvo era R$ {alvo:.2f}\n\n"
            f'🔗 <a href="{url}">Ver na Centauro</a>'
        )
    else:
        msg = (
            f"✅ Monitoramento ativo.\n"
            f"Preço atual: R$ {preco:.2f}\n"
            f"Alvo: R$ {alvo:.2f}"
        )

    print(msg)
    enviar_telegram(token, chat_id, msg)


if __name__ == "__main__":
    monitorar_preco()
