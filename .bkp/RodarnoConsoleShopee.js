(function() {
    // 1. Captura automaticamente o Shop ID e Item ID da URL da página atual
    const urlMatch = window.location.href.match(/i\.(\d+)\.(\d+)/);
    if (!urlMatch) {
        console.error("❌ Erro: Execute este script dentro de uma página de produto da Shopee!");
        return;
    }
    const [_, shopId, itemId] = urlMatch;

    // 2. Captura o token CSRF dinâmico do navegador atual (essencial para guias anônimas)
    const getCookie = (name) => document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'))?.[2] || "";
    const csrfToken = getCookie("csrftoken");

    const apiUrl = `https://shopee.com.br/api/v4/pdp/get_pc?item_id=${itemId}&shop_id=${shopId}&tz_offset_in_minutes=-180&detail_level=0&incoming_pdp_page_source=0&incoming_pdp_page_scenario=0`;

    // 3. Faz a requisição herdando os cookies ativos da janela atual
    fetch(apiUrl, {
        method: "GET",
        headers: {
            "accept": "application/json",
            "x-api-source": "pc",
            "x-shopee-language": "pt-BR",
            "x-csrftoken": csrfToken
        },
        credentials: "same-origin" // Força o uso dos cookies seguros da aba atual (anônima ou normal)
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            console.error("❌ Bloqueio detectado pela Shopee:", data);
            alert("A Shopee barrou a requisição automatizada. Atualize a página e tente novamente.");
            return;
        }
        // 4. Cria o arquivo temporário e abre na nova guia
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
        const blobUrl = URL.createObjectURL(blob);
        window.open(blobUrl, "_blank");
    })
    .catch(err => console.error("❌ Erro ao processar requisição:", err));
})();
