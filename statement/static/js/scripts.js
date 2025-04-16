// DEFINIÇÃO DE CONSTANTES

const pathName = window.location.pathname,
    search = document.querySelector('#id_search_description'),
    asides = document.getElementsByTagName('aside')[0],
    sidebarButton = document.querySelector('#sidebar-button'),
    searchButton = document.querySelector('#search-button'),
    body = document.getElementsByTagName('body')[0];

// FUNÇÕES ESTÉTICAS

/**
 * Encolhe e estica a barra lateral.
 */
function toggleSidebar() {
    toggle = document.getElementsByClassName('toggle');

    if (body.classList.length === 0) {
        recallSidebar();
    } else {
        expandSidebar();
    }
}

/**
 * Recolhe a barra do menu lateral e colapsa os itens que irão desaparecer.
 */
function recallSidebar() {
    let body = document.getElementsByTagName('body')[0];
    let logo = document.getElementsByTagName('body')[0].children[1].children[0];
    let toggle = document.getElementsByClassName('toggle');
    let inverseToggle = document.getElementsByClassName('inverse-toggle');

    body.classList.add('toggled-sidebar');
    logo.children[1].classList.add('toggled');

    for (let i of toggle) {
        i.classList.add('toggled');
    }

    for (let j of inverseToggle) {
        j.classList.add('toggled');
    }
}

/**
 * Expande a barra do menu lateral e mostra os itens que estavam escondidos.
 */
function expandSidebar() {
    let body = document.getElementsByTagName('body')[0];
    let logo = document.getElementsByTagName('body')[0].children[1].children[0];
    let toggle = document.getElementsByClassName('toggle');
    let inverseToggle = document.getElementsByClassName('inverse-toggle');

    body.classList.remove('toggled-sidebar');
    logo.children[1].classList.remove('toggled');

    for (let i of toggle) {
        i.classList.remove('toggled');
    }

    for (let j of inverseToggle) {
        j.classList.remove('toggled');
    }
}

/**
 * Retrai e expande os submenus.
 *
 * @param {string} id - Uma string com o id html do submenu a ser retraído/expandido.
 */
function toggleSubMenu(id) {
    let subMenu = document.querySelector(`#${id}`),
        subMenuButton = document.querySelector(`#${id}-button`);

    if (hasToggled(subMenu.classList)) {
        subMenu.classList.remove('active');
        subMenuButton.lastElementChild.lastElementChild.outerHTML = "<i class='fa-solid fa-angle-up'></i>";
    } else {
        subMenu.classList.add('active');
        subMenuButton.lastElementChild.lastElementChild.outerHTML = "<i class='fa-solid fa-angle-down'></i>";
    }
}

/**
 * Colapsa e revela caixas.
 *
 * @param {string} id - Uma string com o ID HTML da caixa a ser colapsada/revelada.
 */
function toggleBox(id) {
    let element = document.querySelector(`#${id}`);

    if (hasToggled(element.classList)) {
        element.classList.remove('active');
    } else {
        element.classList.add('active');
    }

    if (id == 'search') {
        search.focus();
    }
}

/**
 * Função anônima que encolhe e amplia o menu lateral de acordo com o tamanho da tela disponível.
 */
(window.onresize = () => {
    let boxes = [document.getElementById('tempo-area'), document.getElementById('graphic')];

    if (body.clientWidth < 1200) {
        recallSidebar();
        for (let box of boxes) {
            if (box) {
                box.style.maxWidth = 'calc(100% - 20px)';
            }
        }
    } else {
        expandSidebar();
        for (let box of boxes) {
            if (box) {
                box.style.maxWidth = 'calc(55% - 20px)';
            }
        }
    }
})();

/**
 * Adiciona a classe CSS toggled para colapçar/mostrar elementos.
 *
 * @param {string} id - Uma string com o ID HTML do elemento que será colapsado/mostrado.
 */
function toggle(id) {
    let box = document.getElementById(id);

    if (hasToggled(box.classList)) {
        box.classList.remove('toggled');
    } else {
        box.classList.add('toggled');
    }
}

/**
 * Verifica e inclui a classe CSS active na lista de classes de um elemento html.
 *
 * @param {Array} classList - Um array com as classes CSS de um elemento.
 * @returns - O array com as classes CSS com a classe active adicionada.
 */
function hasToggled(classList) {
    let list = Array.from(classList);

    return list.includes('active');
}

/**
 * Verifica e inclui uma classe CSS na lista de classe de um elemento html.
 *
 * @param {Array} classList - Um array com as classes CSS de um elemento.
 * @param {string} verifiedClass - Uma string da classe CSS a ser verificada.
 * @returns - O array com a classe adicionada.
 */
function hasClass(classList, verifiedClass) {
    const list = Array.from(classList);

    return list.includes(verifiedClass);
}

/**
 * Redireciona para a página de pesquisa passando a string do item a ser pesquisado.
 */
function searchByDescription() {
    const description = document.getElementById('id_search_description'),
        url = `/relatorio_financeiro/pesquisa/descricao/${description.value}`;
    window.location.href = url;
}

// EVENT LISTENERS

// Evento do icone hamburger para encolher/expandir o menu lateral.
sidebarButton.addEventListener('click', () => {
    toggleSidebar();
});

// Expandir o menu lateral quando o mouse passar por cima.
asides.addEventListener('mouseover', () => {
    expandSidebar();
});

// Chama a função que pesquisa ao apertar enter no formulário.
search.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
        searchByDescription();
    }
});
