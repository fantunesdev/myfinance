export async function getMovementsYearMonth(year, month) {
    let url = `/api/movimentacoes/ano/${year}/mes/${month}/`;

    const response = await fetch(url);
    return await response.json();
}


export async function getResource(view) {
    const url = `/api/${view}/`,
        response = await fetch(url);

    return await response.json();
}


export async function getSpecificResource(view, id) {
    const url = `/api/${view}/${id}/`,
        response = await fetch(url);
    console.log(url)
    return await response.json();
}


export async function getRelatedView(view, related, id) {
    const url = `/api/${view}/${id}/${related}`,
    response = await fetch(url);

    return await response.json();
}