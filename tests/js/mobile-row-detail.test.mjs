import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const ROOT = new URL('../../', import.meta.url);

async function importModule(path) {
    const source = await readFile(new URL(path, ROOT), 'utf8');
    return import(`data:text/javascript;charset=utf-8,${encodeURIComponent(source)}`);
}

const {
    initMobileRowDetailNavigation,
    isMobileDetailNavigationEnabled,
    shouldIgnoreRowClick,
} = await importModule('statement/static/js/pages/mobile-row-detail.js');

function fakeElement({ closestResult = null, classNames = [] } = {}) {
    return {
        classList: {
            contains(className) {
                return classNames.includes(className);
            },
        },
        closest() {
            return closestResult;
        },
    };
}

test('habilita navegação apenas no wrapper simple-mobile e em tela de celular', () => {
    const table = fakeElement({ closestResult: {} });
    const mobileWindow = { matchMedia: () => ({ matches: true }) };
    const desktopWindow = { matchMedia: () => ({ matches: false }) };

    assert.equal(isMobileDetailNavigationEnabled(table, mobileWindow), true);
    assert.equal(isMobileDetailNavigationEnabled(table, desktopWindow), false);
    assert.equal(isMobileDetailNavigationEnabled(fakeElement(), mobileWindow), false);
});

test('ignora cliques em ações interativas e linhas de metadados', () => {
    const row = fakeElement();
    const actionTarget = fakeElement({ closestResult: {} });
    const normalTarget = fakeElement();
    const groupHeader = fakeElement({ classNames: ['group-header'] });

    assert.equal(shouldIgnoreRowClick(actionTarget, row), true);
    assert.equal(shouldIgnoreRowClick(normalTarget, groupHeader), true);
    assert.equal(shouldIgnoreRowClick(normalTarget, row), false);
});

test('registra clique nas tabelas marcadas e redireciona para o detalhe da linha', () => {
    let clickHandler = null;
    const row = fakeElement();
    row.dataset = { detailUrl: '/detalhe/123/' };

    const target = {
        closest(selector) {
            return selector === 'tbody tr[data-detail-url]' ? row : null;
        },
    };
    const table = {
        addEventListener(eventName, handler) {
            if (eventName === 'click') clickHandler = handler;
        },
        contains(element) {
            return element === row;
        },
        closest() {
            return {};
        },
    };
    const doc = {
        querySelectorAll(selector) {
            assert.equal(selector, '#statement-table, [data-mobile-row-detail-table]');
            return [table];
        },
    };
    const win = {
        location: { href: '' },
        matchMedia: () => ({ matches: true }),
    };

    initMobileRowDetailNavigation(doc, win);
    clickHandler({ target });

    assert.equal(win.location.href, '/detalhe/123/');
});
