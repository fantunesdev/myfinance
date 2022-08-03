export async function getMovementsYearMonth(year, month) {
    let url = `http://${window.location.host}/api/movimentacoes/ano/${year}/mes/${month}/`;

    const response = await fetch(url);
    return await response.json();
}

export async function getView(view) {
    const url = `http://${window.location.host}/api/${view}/`,
        response = await fetch(url);

    return await response.json();
}