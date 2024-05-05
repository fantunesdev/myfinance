import * as transactionsObjectConversor from './transactions-object-conversor.js'
import * as general from './general.js';

/**
 * Converte uma lista de transações para o formato CSV e baixa o arquivo resultante.
 *
 * @param {Array} transactions - Lista de objetos que representam transações.
 */
export async function convertTransactions(transactions) {
    const header = [
        'Data de Lançamento',
        'Data de Pagamento',
        'Tipo',
        'Conta',
        'Cartão',
        'Categoria',
        'Subcategoria',
        'Descrição',
        'Valor',
    ];

    const csvHeader = removeColumnByActualPath(header);

    const csv = [csvHeader];

    for (const transaction of transactions) {
        let line = [
            transaction.release_date,
            transaction.payment_date,
            transaction.type,
            transaction.account,
            transaction.card,
            transaction.category,
            transaction.subcategory,
            transaction.description,
            transaction.value,
        ];

        csv.push(removeColumnByActualPath(line));
    }

    // Converter o array pra um csv com linhas
    const csvContent = csv.join('');

    await downloadCsvFile(csvContent);
}

/**
 * Trata uma linha de dados com base na URL atual. Dependendo da URL, a função remove determinadas colunas,
 * filtra valores nulos, indefinidos ou vazios e formata a linha como uma string CSV.
 * 
 * @param {Array} line - Uma matriz de valores que representa uma linha de dados a ser tratada.
 * @returns {string} A linha de dados formatada como uma string CSV com uma nova linha no final.
 */
function removeColumnByActualPath(line) {
    const path = window.location.href;
    
    if (path.includes('contas')) {
        line[4] = null; // Remove a coluna Cartões
    } else if (path.includes('cartoes')) {
        line[2] = null; // Remove a coluna Tipo (saida/entrada)
        line[3] = null; // Remove a coluna Cartões
    }
    
    if (path.includes('contas') || path.includes('cartoes')) {
        // Remove `null`, `undefined` e strings vazias
        const filteredLine = line.filter(item => item !== null && item !== undefined && item !== '');
    
        // Junta os elementos com `;` como separador
        const result = filteredLine.join(';');
    
        // Remove espaços vazios no início e no fim da string
        const resultWithoutSpaces = result.trim();
    
        // Retorna a string com uma nova linha no final
        return `${resultWithoutSpaces}\n`;
    }

    // Se não for conta ou cartão, vai retornar a linha sem remover colunas
    return `${line.join(';')}\n`;
}

/**
 * Faz o download de um arquivo CSV com base no conteúdo fornecido.
 * 
 * Cria um arquivo e um hiperlink temporários, simulando um click no mesmo para fazer o download do arquivo.
 * 
 * @param {string} csvContent - O conteúdo do arquivo CSV a ser baixado.
 */
async function downloadCsvFile(csvContent) {
    const blob = new Blob([csvContent], { type: 'text/csv' }); // Cria um arquivo temporário com o conteúdo passado
    const url = URL.createObjectURL(blob); // Cria uma URL para o arquivo
    const link = document.createElement('a'); // Crie um elemento HTML com o link temporário do arquivo

    link.href = url; // Seta a url do <a>
    link.download = await defineFileNameByPath(); // Define o nome do arquivo
    document.body.appendChild(link); // Adiciona o <a> no html
    link.click(); // Simula o click
    document.body.removeChild(link); // Remove o <a> do html
}

/**
 * Define um nome de arquivo com base no caminho atual da URL.
 * 
 * O nome do arquivo é determinado com base no tipo de recurso (contas ou cartões) e a data (mês e ano).
 */
async function defineFileNameByPath() {
    const path = window.location.pathname;

    let fileName,
        month, 
        year;

    
    let arrayPath = path.split('/');
    
    if (path.includes('cartoes')) {
        const index = arrayPath.findIndex(element => element === 'cartoes');
        const cardId = arrayPath[index + 1];
        const card = await transactionsObjectConversor.setCard(cardId);
        const cardName = general.handleNamesToComputer(card.description);

        fileName = `fatura_${cardName}_`;
    } else if (path.includes('contas')) {
        const index = arrayPath.findIndex(element => element === 'contas');
        const accountId = arrayPath[index + 1];
        const account = await transactionsObjectConversor.setAccount(accountId);
        const accountName = general.handleNamesToComputer(account.bank.description);

        fileName = `extrato_${accountName}_`;
    } else {
        fileName = 'extrato_';
    }

    if (path.includes('mes_atual')) {
        const actualDate = new Date();
        month = String(actualDate.getMonth() + 1).padStart(2, '0');
        year = String(actualDate.getFullYear());
    } else {
        if (path.includes('contas')) {
            const index = arrayPath.findIndex(element => element === 'extrato');
            year = arrayPath[index + 1];
            month = arrayPath[index + 2];
        } else if (path.includes('cartoes')) {
            const index = arrayPath.findIndex(element => element === 'fatura');
            year = arrayPath[index + 1];
            month = arrayPath[index + 2];
        }
    }

    fileName += `${year}-${month}`;

    return fileName;
}