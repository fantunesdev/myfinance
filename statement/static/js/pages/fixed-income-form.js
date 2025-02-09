const investmentDateInput = document.getElementById('id_investment_date');
const daysInput = document.getElementById('id_days');
const maturityDateInput = document.getElementById('id_maturity_date');

daysInput.addEventListener('change', () => {
    const investmentDate = new Date(investmentDateInput.value);
    const daysToAdd = parseInt(daysInput.value, 10);

    if (isNaN(daysToAdd)) return;

    investmentDate.setDate(investmentDate.getDate() + daysToAdd);

    maturityDateInput.value = investmentDate.toISOString().split('T')[0];
});