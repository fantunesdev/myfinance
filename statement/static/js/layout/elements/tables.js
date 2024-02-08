import * as tableData from '../../data/expenses-table.js';


export function renderTable(father, transactions, transactionAttrs) {
    const table = document.createElement('table'),
        thead = document.createElement('thead'),
        tbody = document.createElement('tbody'),
        row = document.createElement('tr');
    
    table.id = 'subcategory-table';

    let headRow = createTitleRow(row, tableData.columnTitles);
    thead.appendChild(headRow);

    for (let transaction of transactions) {
        let newRow = document.createElement('tr'),
            data = tableData.setData(transaction, transactionAttrs),
            urls = tableData.setURLs(transaction),
            anchors = createAnchors(urls);
        createRow(newRow, 'td', data, anchors);
        tbody.appendChild(newRow);
    }
    
    table.appendChild(thead);
    table.appendChild(tbody);
    
    father.appendChild(table);
}


function createTitleRow(row, data) {
    for (let i of data) {
        let column = document.createElement('th');
        column.innerHTML = i;
        row.appendChild(column);
    }
    return row;
}


function createRow(row, type, data, anchors) {
    for (let i = 0; i < data.length; i++) {
        let column = document.createElement(type);
        if (i === 1) {
            createImage(column, data[i]);
        } else {
            column.innerHTML = data[i];
        }
        row.appendChild(column);
    }
    if (anchors) {
        for (let anchor of anchors) {
            row.appendChild(anchor);
        }
    }
    return row;
}


function createImage(father, src) {
    const img = document.createElement('img');

    img.src = src;
    img.alt = 'Logotipo';
    img.style = 'max-height: 25px';
    father.appendChild(img);
}


function createAnchors(urls) {    
    let anchors = [];
    for (let index = 0; index < 3; index++) {
        let anchor = document.createElement('a'),
            content = createAnchorWithFontAwesomeIcons(index);
            anchor.href = urls[index];
            anchor.appendChild(content);
            anchors.push(anchor);
        }
        
        return anchors;
    }
    
    
function createAnchorWithFontAwesomeIcons(index) {
    const content = document.createElement('i'),
        fontAwesomeClassName = {
            format: 'fa-solid',
            icons: [
                'fa-file-lines',
                'fa-pen-to-square',
                'fa-trash'
            ],
            behavior: 'action-icon'
        }
        
    content.classList.add(fontAwesomeClassName.format);
    content.classList.add(fontAwesomeClassName.icons[index]);
    content.classList.add(fontAwesomeClassName.behavior);
    return content;
}