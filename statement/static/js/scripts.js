function toggleSidebar() {
    toggle = document.getElementsByClassName('toggle');

    if (body.classList.length === 0) {
        recallSidebar();
    } else {
        expandSidebar();
    }
}

function recallSidebar() {
    let body = document.getElementsByTagName('body')[0],
        logo = document.getElementsByTagName('body')[0].children[1].children[0],
        toggle = document.getElementsByClassName('toggle'),
        inverseToggle = document.getElementsByClassName('inverse-toggle'),
        i;

        body.classList.add('toggled-sidebar');
        logo.children[1].classList.add('toggled');

        for (i of toggle) {
            i.classList.add('toggled');
        }

        for (j of inverseToggle) {
            j.classList.add('toggled')
        }
}

function expandSidebar() {
    let body = document.getElementsByTagName('body')[0],
        logo = document.getElementsByTagName('body')[0].children[1].children[0],
        toggle = document.getElementsByClassName('toggle'),
        inverseToggle = document.getElementsByClassName('inverse-toggle'),
        i;

        body.classList.remove('toggled-sidebar');
        logo.children[1].classList.remove('toggled');

        for (i of toggle) {
            i.classList.remove('toggled');
        }

        for (j of inverseToggle) {
            j.classList.remove('toggled')
        }
}

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

function toggleBox(id) {
    let element = document.querySelector(`#${id}`);

    if (hasToggled(element.classList)) {
        element.classList.remove('active');
    } else {
        element.classList.add('active');
    }

    if (id == 'search') {
        const search = document.querySelector('#id_search_description');
        search.focus();
    }
}

function toggleNavegacao(id) {
    let navegacao = document.querySelector(`#${id}`),
        navegacaoButton = document.querySelector(`#${id}-button`),
        i,
        j;

    if (hasToggled(navegacao.classList)) {
        navegacao.classList.remove('toggled');
        navegacaoButton.children[0].outerHTML = '<i class="fa-solid fa-angles-up" onclick="toggleNavegacao(\'navegacao\')"></i>';
        for (i = 0; i < navegacao.children.length; i++) {
            navegacao.children[i].classList.remove('toggled');
        }
    } else {
        navegacao.classList.add('toggled');
        navegacaoButton.children[0].outerHTML = '<i class="fa-solid fa-angles-down" onclick="toggleNavegacao(\'navegacao\')"></i>';
        for (i = 0; i < navegacao.children.length; i++) {
            navegacao.children[i].classList.add('toggled');
        }
    }
}

let sidebarButton = document.querySelector('#sidebar-button'),
    searchButton = document.querySelector('#search-button'),
    body = document.getElementsByTagName('body')[0];


sidebarButton.addEventListener('click', () => {
    toggleSidebar();
});


(window.onresize = () => {
    let boxes = [
        document.getElementById('tempo-area'),
        document.getElementById('graphic')
    ];
    
    if (body.clientWidth < 1200) {
        recallSidebar();
        for (box of boxes) {
            if (box) {
                box.style.maxWidth = 'calc(100% - 20px)';
            }
        }
    } else {
        expandSidebar();
        for (box of boxes) {
            if (box) {
                box.style.maxWidth = 'calc(55% - 20px)';
            }
        }
    }
})();

function toggle(id) {
    let box = document.getElementById(id);

        if (hasToggled(box.classList)) {
            box.classList.remove('toggled');
        } else {
            box.classList.add('toggled');
        }
}

function hasToggled(classList) {
    let list = Array.from(classList);

    return list.includes('active');
}

function hasClass(classList, verifiedClass) {
    const list = Array.from(classList);

    return list.includes(verifiedClass);
}

const asides = document.getElementsByTagName('aside')[0];
asides.addEventListener('mouseover', () => {
    expandSidebar();
});

function searchByDescription() {
    const description = document.getElementById('id_search_description'),
        url = `/relatorio_financeiro/pesquisa/descricao/${description.value}`;
    window.location.href = url;
}