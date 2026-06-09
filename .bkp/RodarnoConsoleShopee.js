const url = "https://shopee.com.br/api/v4/pdp/get_pc?item_id=20399258102&shop_id=290408305&tz_offset_in_minutes=-180&detail_level=0&incoming_pdp_page_source=0&incoming_pdp_page_scenario=0";

fetch(url, {
    method: "GET",
    headers: {
        "accept": "application/json",
        "x-api-source": "pc",
        "x-shopee-language": "pt-BR",
        "x-csrftoken": "mLHMHuzk1TUmVL1ur5YKo7T2Dr96UqcW",
        "af-ac-enc-dat": "7c20e5b5271f2f62",
        "af-ac-enc-sz-token": "z9cCWO9Hn9/rbWumTfhb/w==|axvWtWyU0tuCsDiFjJ3FfR1XwUtC4hoLPDOp7wRPGyWRsg9W1yYMPCqgKCBNQ/oDTvozYqofq+hu9nawrScQ|iBeow5EZe7utAPkj|08|3",
        "x-sap-ri": "94a3286a313715861d4aee3a0a0114a5b90d7bd68d15c149307a",
        "x-sap-sec": "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"
    }
})
.then(res => res.json())
.then(data => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const blobUrl = URL.createObjectURL(blob);
    window.open(blobUrl, "_blank");
})
.catch(err => console.error("Erro ao carregar os dados:", err));
