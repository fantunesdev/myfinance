import * as tableData from '../../data/expenses-table.js';


export function renderTable(father, movements, subcategories, category) {
    const table = document.createElement('table'),
        thead = document.createElement('thead'),
        tbody = document.createElement('tbody'),
        row = document.createElement('tr');
    
    table.id = 'subcategory-table';

    let headRow = createRow(row, 'th', tableData.columnTitles);
    thead.appendChild(headRow);

    for (let movement of movements) {
        let newRow = document.createElement('tr'),
            data = tableData.setData(movement, subcategories, category),
            urls = tableData.setURLs(movement),
            anchors = createAnchors(urls);
        createRow(newRow, 'td', data, anchors);
        tbody.appendChild(newRow);
    }
    
    table.appendChild(thead);
    table.appendChild(tbody);
    
    father.appendChild(table);
};


function createRow(row, type, data, anchors) {
    for (let i of data) {
        let column = document.createElement(type);
        column.innerHTML = i;
        row.appendChild(column);
    };
    if (anchors) {
        for (let anchor of anchors) {
            row.appendChild(anchor);
        }
    };
    return row;
};


function createAnchors(urls) {    
    let anchors = [];
    for (let index = 0; index < 3; index++) {
        let anchor = document.createElement('a'),
            content = createAnchorWithFontAwesomeIcons(index);
            anchor.href = urls[index];
            anchor.appendChild(content);
            anchors.push(anchor);
        };
        
        return anchors;
    };
    
    
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
        };
        
    content.classList.add(fontAwesomeClassName.format);
    content.classList.add(fontAwesomeClassName.icons[index]);
    content.classList.add(fontAwesomeClassName.behavior);
    return content;
}