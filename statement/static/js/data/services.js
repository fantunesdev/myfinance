export async function getMovementsYearMonth(year, month) {
    let url = `/api/movimentacoes/ano/${year}/mes/${month}/`;

    const response = await fetch(url);
    return await response.json();
}


export async function getView(view) {
    const url = `/api/${view}/`,
        response = await fetch(url);

    return await response.json();
}


export async function getViewDetail(view, id) {
    const url = `/api/${view}/${id}/`,
        response = await fetch(url);

    return await response.json();
}


export async function getRelatedView(view, related, id) {
    const url = `/api/${view}/${id}/${related}`,
    response = await fetch(url);

    return await response.json();
}