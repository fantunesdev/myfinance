import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import vm from 'node:vm';

const pickerSource = await readFile(new URL('../../statement/static/js/layout/elements/searchable-select.js', import.meta.url), 'utf8');
const optionsSource = await readFile(new URL('../../statement/static/js/layout/elements/selects.js', import.meta.url), 'utf8');

function element(value = '') {
    return {
        id: '', textContent: '', required: false, disabled: false, hidden: false,
        children: [], labels: [], attributes: {}, dataset: {}, events: {},
        get value() { return this._value ?? String(value); },
        set value(value) { this._value = String(value); },
        get text() { return this.textContent; },
        set text(text) { this.textContent = text; },
        get options() { return this.children; },
        get length() { return this.children.length; },
        set length(length) { this.children.length = length; },
        appendChild(child) { this.children.push(child); },
        replaceChildren(...children) { this.children = children; },
        add(option, before) {
            const index = this.children.indexOf(before);
            this.children.splice(index < 0 ? this.children.length : index, 0, option);
        },
        addEventListener(name, handler) { (this.events[name] ||= []).push(handler); },
        emit(name, event = {}) {
            const data = { preventDefault() { this.defaultPrevented = true; }, ...event };
            for (const handler of this.events[name] || []) handler(data);
            return data;
        },
        dispatchEvent(event) { this.emit(event.type, event); },
        setAttribute(name, value) { this.attributes[name] = value; },
        removeAttribute(name) { delete this.attributes[name]; },
        setCustomValidity(message) { this.validationMessage = message; },
        contains(child) { return child === this || this.children.includes(child); },
        select() {},
        focus() { this.emit('focus'); },
    };
}

function picker({ selected = '1', required = true, choices } = {}) {
    const select = element(selected);
    select.id = 'id_category';
    select.required = required;
    select.labels = [{ htmlFor: select.id }];
    select.children = (choices || [
        ['', '---------'], ['3', 'zoológico'], ['2', 'Óleo'], ['1', 'Alimentação'], ['4', 'educação'],
    ]).map(([value, label]) => {
        const option = element(value);
        option.textContent = label;
        return option;
    });
    const search = element();
    search.id = 'id_category_search';
    search.hidden = true;
    const results = element();
    results.id = 'id_category_results';
    results.hidden = true;
    results.dataset.emptyMessage = 'Nenhuma categoria encontrada.';
    const wrapper = element();
    wrapper.children = [select, search, results];
    search.parentElement = wrapper;
    const context = vm.createContext({
        document: {
            getElementById(id) { return { id_category_search: search, id_category_results: results }[id]; },
            createElement() { return element(); },
        },
        Event: class { constructor(type) { this.type = type; } },
    });
    vm.runInContext(`${optionsSource}\n${pickerSource}`.replace(/^export /gm, ''), context);
    const controller = context.enhanceSearchableSelect(select);
    return { select, search, results, wrapper, controller, renderOptions: context.renderOptions,
        type(query) { search.value = query; search.emit('input'); },
        key(key) { return search.emit('keydown', { key }); },
        labels() { return Array.from(results.children, node => node.textContent); },
    };
}

test('preserva a seleção, ordena em português e transfere rótulo e validação ao campo de busca', () => {
    const page = picker();
    assert.deepEqual(page.select.options.map(option => option.textContent), [
        '---------', 'Alimentação', 'educação', 'Óleo', 'zoológico',
    ]);
    assert.equal(page.select.value, '1');
    assert.equal(page.search.value, 'Alimentação');
    assert.equal(page.select.hidden, true);
    assert.equal(page.select.required, false);
    assert.equal(page.search.hidden, false);
    assert.equal(page.search.required, true);
    assert.equal(page.select.labels[0].htmlFor, page.search.id);
    assert.equal(page.search.validationMessage, '');
});

test('filtra sem distinguir acentos ou maiúsculas e mostra uma mensagem quando não há resultados', () => {
    const page = picker();
    page.type('  EDUCACAO ');
    assert.deepEqual(page.labels(), ['educação']);
    assert.equal(page.results.hidden, false);
    assert.equal(page.search.attributes['aria-expanded'], 'true');
    page.type('inexistente');
    assert.deepEqual(page.labels(), ['Nenhuma categoria encontrada.']);
    assert.equal(page.search.attributes['aria-activedescendant'], undefined);
    assert.equal(page.search.validationMessage, 'Selecione uma opção da lista.');
    assert.equal(page.key('Enter').defaultPrevented, true);
    assert.equal(page.select.value, '1');
});

test('seleção pelo mouse dispara change para atualizar as subcategorias', () => {
    const page = picker();
    let changed = 0;
    page.select.addEventListener('change', () => { changed++; });
    page.type('oleo');
    assert.equal(page.results.children[0].emit('mousedown').defaultPrevented, true);
    page.results.children[0].emit('click');
    assert.equal(page.select.value, '2');
    assert.equal(page.search.value, 'Óleo');
    assert.equal(changed, 1);
    assert.equal(page.results.hidden, true);
    assert.equal(page.search.validationMessage, '');
});

test('setas e Enter selecionam sem enviar o formulário e Escape cancela a busca', () => {
    const page = picker();
    assert.equal(page.key('ArrowDown').defaultPrevented, true);
    page.key('ArrowDown');
    assert.equal(page.search.attributes['aria-activedescendant'], 'id_category_option_4');
    assert.equal(page.key('Enter').defaultPrevented, true);
    assert.equal(page.select.value, '4');
    assert.equal(page.search.value, 'educação');
    page.type('outro');
    assert.equal(page.key('Escape').defaultPrevented, true);
    assert.equal(page.search.value, 'educação');
    assert.equal(page.results.hidden, true);
    assert.equal(page.search.attributes['aria-expanded'], 'false');
});

test('atualizar opções após trocar tipo ou categoria remove o texto antigo e ordena os novos resultados', () => {
    const page = picker();
    page.type('alimentacao');
    page.renderOptions(page.select, [
        { id: 2, description: 'Zoológico' }, { id: 1, description: 'Água' },
    ]);
    page.select.value = '0';
    page.controller.refresh();
    assert.equal(page.search.value, '');
    assert.equal(page.results.hidden, true);
    assert.equal(page.search.validationMessage, 'Selecione uma opção da lista.');
    page.search.emit('focus');
    assert.deepEqual(page.labels(), ['Água', 'Zoológico']);
    page.renderOptions(page.select, []);
    page.controller.refresh();
    page.search.emit('focus');
    assert.deepEqual(page.labels(), ['Nenhuma categoria encontrada.']);
});

test('sair do campo restaura a seleção confirmada e fecha a lista', () => {
    const page = picker();
    page.type('outra categoria');
    page.wrapper.emit('focusout', { relatedTarget: null });
    assert.equal(page.search.value, 'Alimentação');
    assert.equal(page.search.validationMessage, '');
    assert.equal(page.results.hidden, true);
});

test('campo vazio obrigatório exige uma seleção e campo desabilitado não abre a lista', () => {
    const page = picker({ selected: '' });
    assert.equal(page.search.value, '');
    assert.equal(page.search.validationMessage, 'Selecione uma opção da lista.');
    page.select.disabled = true;
    page.controller.refresh();
    page.search.emit('focus');
    assert.equal(page.search.disabled, true);
    assert.equal(page.results.hidden, true);
});
