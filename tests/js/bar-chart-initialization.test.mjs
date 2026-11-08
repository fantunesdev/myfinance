import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const source = await readFile(new URL('../../statement/static/js/layout/elements/graphics.js', import.meta.url), 'utf8');
// Importa o módulo real: não remove imports, para detectar ciclos com a página.
const { drawBarChart } = await import(`data:text/javascript;charset=utf-8,${encodeURIComponent(source)}`);

function setup() {
    const storage = new Map([['bar_chart_level', 'categories']]);
    globalThis.sessionStorage = {
        getItem: key => storage.get(key),
        setItem: (key, value) => storage.set(key, value),
        removeItem: key => storage.delete(key),
    };
    globalThis.window = { matchMedia: () => ({ matches: false }) };
    globalThis.document = { getElementById: () => ({ getContext: () => ({ canvas: { style: {} } }) }) };
    globalThis.Chart = class {
        constructor(context, config) {
            this.canvas = context.canvas;
            this.data = config.data;
            this.options = config.options;
            // Chart.js pode disparar eventos durante a construção.
            this.options.onHover({}, [], this);
        }
    };
    return storage;
}

test('gráfico inicializa e recebe hover sem importar a página', () => {
    setup();
    const chart = drawBarChart({ names: ['Transporte'], values: [230], colors: ['red'] }, 'Despesas');
    assert.equal(chart.canvas.style.cursor, 'default');
    chart.options.onHover({}, [{ index: 0 }], chart);
    assert.equal(chart.canvas.style.cursor, 'pointer');
});

test('clique usa o gráfico do evento e chama a atualização da página', async () => {
    const storage = setup();
    let selected;
    const first = drawBarChart({ names: ['Transporte'], values: [230], colors: [] }, 'Despesas', async chart => { selected = chart; });
    drawBarChart({ names: ['Alimentação'], values: [100], colors: [] }, 'Outro gráfico');
    await first.options.onClick({}, [{ index: 0 }], first);
    assert.equal(selected, first);
    assert.equal(storage.get('bar_label_clicked'), 'Transporte');
    assert.equal(storage.get('bar_chart_level'), 'subcategories');
    await first.options.onClick({}, [], first);
    assert.equal(storage.get('bar_chart_level'), 'categories');
    assert.equal(storage.has('bar_label_clicked'), false);
});
