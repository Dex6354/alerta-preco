url = "https://services.vipcommerce.com.br/api-admin/v1/org/161/filial/1/centro_distribuicao/1/loja/produtos/11158/detalhes";

fetch(url, {
    method: "GET",
    headers: {
        "OrganizationID": "161",
        "domainKey": "loja.shibata.com.br",
        "Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJ2aXBjb21tZXJjZSIsImF1ZCI6ImFwaS1hZG1pbiIsInN1YiI6IjZiYzQ4NjdlLWRjYTktMTFlOS04NzQyLTAyMGQ3OTM1OWNhMCIsInZpcGNvbW1lcmNlQ2xpZW50ZUlkIjpudWxsLCJpYXQiOjE3ODAxNzQxNzMsInZlciI6MSwiY2xpZW50IjpudWxsLCJvcGVyYXRvciI6bnVsbCwib3JnIjoiMTYxIn0.eUG_hnJZPfxHjt6sNt577iY8Z06syNNf59rpOLICOyM7uqlxBF21fFVrAZQuKfNHR8w03LD02HMN0d6ci2TKXA"
    }
})
.then(response => response.json())
.then(data => {
    // Converte o JSON em texto bonito e identado
    const jsonString = JSON.stringify(data, null, 2);
    // Cria um arquivo temporário em memória do tipo JSON
    const blob = new Blob([jsonString], { type: "application/json" });
    const urlBlob = URL.createObjectURL(blob);
    // Abre esse arquivo em uma nova guia
    window.open(urlBlob, "_blank");
})
.catch(error => console.error("Erro:", error));
