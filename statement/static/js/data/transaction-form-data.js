export function setPaymentDate(releaseDate, card) {
    let [year, month, day] = releaseDate.split('-');

    let releaseDay = parseInt(day);
    if (card) {
        if (releaseDay > card.closing_day) {
            return addMonth(card.expiration_day, month, year);
        } else {
            return `${year}-${month}-${card.expiration_day.toString().padStart(2, '0')}`;
        }
    } else {
        return releaseDate;
    };
};


function addMonth(day, monthString, anoString) {
    var month = parseInt(monthString),
        year = parseInt(anoString);

    month = month + 1;
    if (month > 12) {
        month = 1;
        year = year + 1;
    };

    return `${year}-${month.toString().padStart(2, '0')}-${day.toString().padStart(2, '0')}`;
}