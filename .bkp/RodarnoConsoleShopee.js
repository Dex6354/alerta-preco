(async () => {
  // Captura o cookie de forma mais robusta via Regex
  function getCookie(name) {
    const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return match ? match[2] : null;
  }

  const csrfToken = getCookie("csrftoken");
  if (!csrfToken) {
    console.error("❌ Não foi possível encontrar o 'csrftoken'. Certifique-se de estar na página da Shopee.");
    return;
  }

  const url = "https://shopee.com.br/api/v4/pdp/get_rw?display_model_id=229441478391&item_id=58259028136&shop_id=1083800536&tz_offset_in_minutes=-180&detail_level=0&incoming_pdp_page_source=0&incoming_pdp_page_scenario=0";

  const headers = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "X-CSRFToken": csrfToken,
    "X-Requested-With": "XMLHttpRequest",
    "X-Shopee-Language": "pt-BR",
    "X-API-SOURCE": "rweb"
  };

  try {
    console.log("🔄 Iniciando requisição com o Token:", csrfToken);

    const response = await fetch(url, { 
      method: "GET", 
      headers: headers,
      credentials: "include" // Força o uso de todos os cookies ativos da sua sessão (essencial contra o anti-bot)
    });

    const data = await response.json();
    console.log("📦 Resposta recebida:", data);

    // Abre os dados em nova aba
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const blobUrl = URL.createObjectURL(blob);
    window.open(blobUrl, "_blank");

    console.log("✅ Concluído com sucesso!");
  } catch (error) {
    console.error("❌ Erro ao buscar a API:", error);
  }
})();
