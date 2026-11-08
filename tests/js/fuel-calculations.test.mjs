import assert from 'node:assert/strict';
import test from 'node:test';
import { readFile } from 'node:fs/promises';

const source = await readFile(new URL('../../statement/static/js/data/fuel-calculations.js', import.meta.url), 'utf8');
const { calculateFuel, calculateOdometerInterval, resolveFuelInputs } = await import(`data:text/javascript;charset=utf-8,${encodeURIComponent(source)}`);

test('preço e valor calculam litros preservando o preço digitado', () => {
    assert.deepEqual(resolveFuelInputs({ amount: '10', price: '6.4', liters: '', basis: 'price' }), {
        price: '6.4', liters: '1.563',
    });
});

test('litros e valor calculam preço considerando desconto', () => {
    assert.deepEqual(resolveFuelInputs({ amount: '220', liters: '40', price: '6.4', basis: 'liters' }), {
        liters: '40', price: '5.5000',
    });
});

test('alteração do total respeita o campo escolhido como base', () => {
    assert.equal(resolveFuelInputs({ amount: '128', price: '6.4', liters: '40', basis: 'price' }).liters, '20.000');
    assert.equal(resolveFuelInputs({ amount: '128', price: '6.4', liters: '40', basis: 'liters' }).price, '3.2000');
});

const point = (id, odometer, liters = 40, full = true, broken = false) => ({
    id, date: `2026-01-0${id}`, odometer, liters, full_tank: full, break_before: broken,
    amount: liters * 6, currency: 'BRL',
});

test('o preço por litro usa o total líquido e suporta três casas nos litros', () => {
    const result = calculateFuel({ amount: '220', liters: '40.125', distance: '400' });
    assert.equal(result.price, 220 / 40.125);
    assert.equal(result.consumption, 400 / 40.125);
    assert.equal(result.cost, 0.55);
});

test('ausência de distância mantém preço sem produzir consumo zero', () => {
    assert.deepEqual(calculateFuel({ amount: 240, liters: 40, distance: '' }), {
        price: 6, consumption: null, cost: null,
    });
    assert.equal(calculateFuel({ amount: 0, liters: 0, distance: 0 }).price, null);
});

test('prévia inclui abastecimentos parciais e exclui os litros iniciais', () => {
    const history = [point(1, 82000), point(2, null, 20, false)];
    const interval = calculateOdometerInterval(history, point(3, 82800, 30));
    assert.equal(interval.consumption, 16);
    assert.equal(interval.distance, 800);
    assert.equal(interval.liters, 50);
});

test('prévia não inclui registros posteriores em edição retroativa', () => {
    const history = [point(1, 1000), point(3, 2000)];
    assert.equal(calculateOdometerInterval(history, point(2, 1400)).consumption, 10);
});

test('abastecimento parcial ou com interrupção aguarda fechamento', () => {
    assert.equal(calculateOdometerInterval([point(1, 1000)], point(2, 1400, 20, false)), null);
    assert.equal(calculateOdometerInterval([point(1, 1000)], point(2, 1400, 40, true, true)), null);
    assert.equal(calculateOdometerInterval([point(1, 1000), point(2, 1200, 20, false, true)], point(3, 1600)), null);
});

test('novo tanque cheio pode iniciar referência mesmo após uma interrupção', () => {
    assert.equal(calculateOdometerInterval([point(1, 1000, 40, true, true)], point(2, 1400)).consumption, 10);
});

test('leituras inconsistentes ou litros ausentes não fecham prévia', () => {
    assert.equal(calculateOdometerInterval([point(1, 1000), point(2, 1900, 20, false)], point(3, 1800)), null);
    assert.equal(calculateOdometerInterval([point(1, 1000), point(2, 1200, null, false)], point(3, 1800)), null);
});
