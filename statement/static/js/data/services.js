export async function getTransactionsByYearAndMonth(year, month) {
    const path = window.location.pathname;
    let accountId,
        cardId,
        url;
        
        if (path.includes('contas')) {
            accountId = path.split('/')[3];
            url = `/api/transactions/accounts/${accountId}/year/${year}/month/${month}/`;
        } else if (path.includes('cartoes')) {
        cardId = path.split('/')[3];
        url = `/api/transactions/card/${cardId}/year/${year}/month/${month}/`;
    } else {
        url = `/api/transactions/year/${year}/month/${month}/`;
    }

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