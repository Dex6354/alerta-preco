(async () => {
  const url = "https://shopee.com.br/api/v4/pdp/get_rw?display_model_id=229441478391&item_id=58259028136&shop_id=1083800536&tz_offset_in_minutes=-180&detail_level=0&incoming_pdp_page_source=0&incoming_pdp_page_scenario=0";

  const headers = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "X-Shopee-Language": "pt-BR",
    "X-Requested-With": "XMLHttpRequest",
    "X-CSRFToken": "USYuhSWtpEpo9C2gIwuwfKMPJ7QUgdR2",
    "X-API-SOURCE": "rweb",
    "af-ac-enc-dat": "4f806e6f6eb2d216",
    "x-sz-sdk-version": "1.12.39",
    "x-sap-ri": "57f3256ac80e2889366454380a015a27bd369ef54257e5c9e8b1",
    "x-sap-sec": "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"
  };

  try {
    const response = await fetch(url, { method: "GET", headers });
    const data = await response.json();

    // Cria um Blob com o conteúdo JSON formatado
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const blobUrl = URL.createObjectURL(blob);

    // Abre em uma nova guia
    window.open(blobUrl, "_blank");
  } catch (error) {
    console.error("Erro ao buscar a API:", error);
  }
})();
