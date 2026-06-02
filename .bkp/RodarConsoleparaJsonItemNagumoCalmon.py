(function() {
    // 1. Extrai o ID do produto da URL atual
    const urlAtual = window.location.href.split('?')[0];
    let matchId = urlAtual.match(/-(\d+)\.html$/);
    
    if (!matchId) {
        matchId = window.location.href.match(/[?&]pid=(\d+)/);
    }

    if (!matchId) {
        console.error("❌ Não foi possível encontrar o ID do produto nesta URL.");
        alert("Abra a página de um produto do Nagumo antes de rodar o código!");
        return;
    }

    const produtoId = matchId[1];
    const urlJson = `https://www.nagumo.com.br/on/demandware.store/Sites-Nagumo-Site/pt_BR/Product-Variation?pid=${produtoId}`;

    console.log("⏳ Forçando a Loja 22 (Calmon) e buscando o JSON...");

    // 2. Faz a requisição simulando exatamente o cookie desejado
    fetch(urlJson, {
        headers: {
            "Upgrade-Insecure-Requests": "1",
            // Força o cookie da loja 22 diretamente na requisição HTTP
            "Cookie": "dw_store=22; dw_consent=tracking=false; __cq_dnt=1; dw_dnt=1"
        },
        credentials: "omit" // Ignora os cookies guardados no navegador para não misturar as lojas
    })
    .then(response => {
        if (!response.ok) throw new Error(`Erro na API: ${response.status}`);
        return response.json();
    })
    .then(dados => {
        // 3. Abre uma nova janela e joga o JSON formatado lá dentro
        const novaJanela = window.open();
        if (novaJanela) {
            novaJanela.document.open();
            novaJanela.document.write(`
                <html>
                <head><title>JSON Nagumo - Loja 22</title></head>
                <body>
                    <pre style="font-family: monospace; background: #1e1e1e; color: #fff; padding: 20px; border-radius: 5px; overflow: auto;">${JSON.stringify(dados, null, 4)}</pre>
                </body>
                </html>
            `);
            novaJanela.document.close();
            console.log("✅ JSON aberto com sucesso na nova aba com os dados da Loja 22!");
        } else {
            console.error("❌ O navegador bloqueou o pop-up. Permita pop-ups para este site.");
        }
    })
    .catch(erro => {
        console.error("❌ Erro ao buscar o JSON:", erro);
    });
})();
