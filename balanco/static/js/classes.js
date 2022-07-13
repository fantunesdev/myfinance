import * as cartoesServices from './services/cartao.js'
import * as categoriaServices from './services/categoria.js'
import * as subcategoriaServices from './services/subcategoria.js'
import * as selects from './html-objects/selects.js'

const cartao = {
    select: document.querySelector('#id_cartao'),
    async changeForm() {
        const dataLancamento = document.querySelector('#id_data_lancamento'),
            dataEfetivacao = document.querySelector('#id_data_efetivacao'),
            cartao = await cartoesServices.getCartaoId(this.select.value);

        let efetivacao = validarLancamento(dataLancamento.value, cartao.vencimento);
        dataEfetivacao.value = efetivacao;
    }
    
}

function validarLancamento(dataLancamento, diaVencimento) {
    let [yearLancamento, monthLancamento, dayLancamento] = dataLancamento.split('-');

    let lancamento = parseInt(dayLancamento);
    
    if (diaVencimento < lancamento) {
        return somarMes(diaVencimento, monthLancamento, yearLancamento)
    } else {
        return `${yearLancamento}-${monthLancamento}-${diaVencimento < 10 ? `0${diaVencimento}` : diaVencimento}`;
    }
}

function somarMes(dia, mesString, anoString) {
    var mes = parseInt(mesString),
        ano = parseInt(anoString),
        diaString;

    mes = mes + 1;
    if (mes > 12) {
        mes = 12;
        ano = ano + 1;
    }

    if (dia < 10) {
        diaString = `0${dia}`;
    } else {
        diaString = `${dia}`;
    }

    if (mes < 10) {
        mesString = `0${mes}`;
    } else {
        mesString = `${mes}`;
    }

    return `${ano}-${mesString}-${diaString}`
}

cartao.select.addEventListener('change', () => cartao.changeForm());


const categoria = {
    select: document.querySelector('#id_categoria'),
    teste() {
        console.log('categoria')
    }
}

categoria.select.addEventListener('focusout', () => {
    subcategoria.renderSelect();
});

const conta = {
    select: document.querySelector('#id_conta')
}

const subcategoria = {
    select: document.querySelector('#id_subcategoria'),
    async renderSelect() {
        const subcategorias = await subcategoriaServices.getSubcategoriasCategoria(categoria.select.value);

        selects.renderOptions(this.select, subcategorias);
    }
}

const meioDePagamento = {
    select: document.querySelector('#id_meio_de_pagamento'),
    async changeForm() {
        const father = document.querySelector('#conta-cartao'),
            labelConta = father.children[0],
            labelCartao = father.children[2];
        
        
        if (this.select.value == 1) {
            conta.select.style.display = 'none';
            labelConta.style.display = 'none';
            cartao.select.style.display = 'block';
            labelCartao.style.display = 'block';
        } else if (this.select.value == 2) {
            cartao.select.style.display = 'none';
            labelCartao.style.display = 'none';
            conta.select.style.display = 'block';
            labelConta.style.display = 'block';
        }
    }
}

meioDePagamento.changeForm();
meioDePagamento.select.addEventListener('change', () => meioDePagamento.changeForm());

