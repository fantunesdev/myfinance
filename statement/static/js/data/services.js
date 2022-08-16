export async function getTransactionsByYearAndMonth(year, month) {
    let url = `/api/transactions/year/${year}/month/${month}/`;

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

    return await response.json();
}


export async function getRelatedResource(view, related, id) {
    const url = `/api/${view}/${id}/${related}`,
    response = await fetch(url);

    return await response.json();
}