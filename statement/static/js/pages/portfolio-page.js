import * as services from '../data/services.js';
import * as doughnutChart from '../layout/elements/doughnut-chart.js';
import * as stakedAreaChart from '../layout/elements/staked-area-chart.js';

const fixedIncomeProgression = await services.getSpecificResource('fixed-income', 'progression');
const variableIncomeProgression = [];
const cryptoProgression = [];

// Dataset para gráfico de área
const stakedAreaDatasets = [{
    label: 'Renda Fixa',
    color: 'rgba(139, 0, 0, 1)',
    names: fixedIncomeProgression.map(item => item.date),
    values: fixedIncomeProgression.map(item => item.total_amount),
}];

const areaChart = stakedAreaChart.drawStackedAreaChart(stakedAreaDatasets, 'Progressão Patrimonial');


const doughnutDatasets = {
    colors: ['rgb(80, 0, 0)', 'rgb(110, 2, 2)', 'rgba(140, 0, 0, 1)'],
    names: ['Renda Fixa', 'Renda Variável', 'Criptomoedas'],
    values: [fixedIncomeProgression.at(-1).total_amount, variableIncomeProgression.at(-1), cryptoProgression.at(-1)]
};


window.doughnutChart = doughnutChart.drawDoughnutChart(doughnutDatasets, 'Distribuição Patrimonial', onDoughnutClick);

let combined = true;
let dataset;
function onDoughnutClick(selectedValue) {
    window.doughnutChart.destroy();

    if (combined) {
        dataset = {
            colors: ['rgba(80, 0, 0, 1)', 'rgba(110, 0, 0, 1)'],
            names: ['Renda Fixa', 'Renda Variável e Criptomoedas'],
            values: [fixedIncomeProgression.at(-1).total_amount, variableIncomeProgression.at(-1) + cryptoProgression.at(-1)]
        };
    } else {
        dataset = doughnutDatasets;
    }

    combined = !combined;

    window.doughnutChart = doughnutChart.drawDoughnutChart(dataset, 'Distribuição Patrimonial', onDoughnutClick);
}
