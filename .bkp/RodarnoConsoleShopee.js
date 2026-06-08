(async () => {
  // Função para capturar o CSRF Token real e atualizado dos cookies do navegador
  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
  }

  const csrfToken = getCookie("csrftoken");

  if (!csrfToken) {
    console.error("❌ Não foi possível encontrar o 'csrftoken' nos cookies. Certifique-se de estar no site da Shopee.");
    return;
  }

  const url = "https://shopee.com.br/api/v4/pdp/get_rw?display_model_id=229441478391&item_id=58259028136&shop_id=1083800536&tz_offset_in_minutes=-180&detail_level=0&incoming_pdp_page_source=0&incoming_pdp_page_scenario=0";

  // Cabeçalhos simplificados utilizando a sua sessão ativa do navegador
  const headers = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "X-Shopee-Language": "pt-BR",
    "X-Requested-With": "XMLHttpRequest",
    "X-CSRFToken": csrfToken,
    "X-API-SOURCE": "rweb"
  };

  try {
    console.log("🔄 Iniciando requisição com o Token atualizado:", csrfToken);
    
    const response = await fetch(url, { method: "GET", headers });
    const data = await response.json();

    console.log("📦 Resposta recebida:", data);

    // Cria o arquivo JSON e abre em nova aba
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const blobUrl = URL.createObjectURL(blob);
    window.open(blobUrl, "_blank");
    
    console.log("✅ Concluído com sucesso!");
  } catch (error) {
    console.error("❌ Erro ao buscar a API:", error);
  }
})();
