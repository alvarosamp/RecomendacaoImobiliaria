'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const C = require('./web/crm-engine.js');
const db = JSON.parse(fs.readFileSync(path.join(__dirname, 'data', 'simulation.json'), 'utf8'));
const AT = '2026-10-29T10:00:00-03:00';
const seed = () => C.seedDeals(db.requests, db.meta.as_of);

test('every request becomes one open lead at an early stage, with its value and origin', () => {
  const deals = seed();
  assert.equal(deals.length, db.requests.length);
  assert.equal(new Set(deals.map(d => d.id)).size, deals.length);
  deals.forEach(d => {
    assert.equal(d.outcome, null); assert.ok(['new', 'qualification'].includes(d.stage));
    assert.equal(d.source.kind, 'request'); assert.equal(d.history.length, 1);
  });
  assert.ok(deals.filter(d => d.stage === 'new').every(d => d.triage === 'outside'));
});

test('stage moves are logged and immutable; installation and win need the required checklist', () => {
  const deal = seed()[0], frozen = JSON.stringify(deal);
  const moved = C.applyAction(deal, { type: 'move', stage: 'proposal' }, AT);
  assert.equal(JSON.stringify(deal), frozen);
  assert.equal(moved.stage, 'proposal'); assert.match(moved.history.at(-1).action, /Proposta/);
  assert.throws(() => C.applyAction(moved, { type: 'move', stage: 'installation' }, AT), /checklist/);
  assert.throws(() => C.applyAction(moved, { type: 'win' }, AT), /pendentes/);
  let d = moved;
  for (const item of ['viability', 'plan', 'contract']) d = C.applyAction(d, { type: 'check', item, done: true }, AT);
  d = C.applyAction(d, { type: 'move', stage: 'installation' }, AT); // scheduling may still be pending here
  assert.throws(() => C.applyAction(d, { type: 'win' }, AT), /Instalação agendada/);
  d = C.applyAction(d, { type: 'check', item: 'schedule', done: true }, AT);
  const won = C.applyAction(d, { type: 'win' }, AT);
  assert.equal(won.outcome, 'won'); assert.equal(won.stage, 'result'); assert.equal(won.closed_from, 'installation');
  assert.throws(() => C.applyAction(won, { type: 'move', stage: 'new' }, AT), /encerrado/);
  const reopened = C.applyAction(won, { type: 'reopen' }, AT);
  assert.equal(reopened.stage, 'installation'); assert.equal(reopened.outcome, null);
});

test('losses need a reason, and a competitor when lost to one; changing the type resets the checklist', () => {
  const deal = seed()[1];
  assert.throws(() => C.applyAction(deal, { type: 'lose' }, AT), /motivo/);
  assert.throws(() => C.applyAction(deal, { type: 'lose', reason: 'competitor' }, AT), /concorrente/);
  const lost = C.applyAction(deal, { type: 'lose', reason: 'competitor', competitor: 'VIVO' }, AT);
  assert.equal(lost.competitor.name, 'VIVO'); assert.equal(lost.lost_reason, 'competitor');
  const checked = C.applyAction(deal, { type: 'check', item: 'plan', done: true }, AT);
  const business = C.applyAction(checked, { type: 'update', fields: { type: 'business' } }, AT);
  assert.deepEqual(business.checklist, {});
  assert.equal(C.applyAction(deal, { type: 'update', fields: { mrr: deal.mrr } }, AT), deal); // no-op keeps identity
  assert.throws(() => C.applyAction(deal, { type: 'update', fields: { mrr: -1 } }, AT), /inválido/);
  assert.throws(() => C.applyAction(deal, { type: 'note', text: '  ' }, AT), /vazia/);
});

test('dashboard: pipeline, weighted forecast, win rate, losses by reason and competitor, follow-ups', () => {
  let deals = seed().slice(0, 6);
  const won = (d) => { for (const item of ['viability', 'plan', 'contract', 'schedule']) d = C.applyAction(d, { type: 'check', item, done: true }, AT); return C.applyAction({ ...d, competitor: { name: 'OI' } }, { type: 'win' }, AT); };
  deals[0] = won(deals[0]);
  deals[1] = C.applyAction(deals[1], { type: 'lose', reason: 'competitor', competitor: 'VIVO' }, AT);
  deals[2] = C.applyAction(deals[2], { type: 'lose', reason: 'price' }, AT);
  deals[3] = C.applyAction(deals[3], { type: 'discard' }, AT);
  deals[4] = C.applyAction(deals[4], { type: 'update', fields: { next_action: { date: '2026-10-20', text: 'Ligar' } } }, AT);
  deals[5] = C.applyAction(deals[5], { type: 'update', fields: { next_action: { date: '2026-10-29', text: 'Visita' } } }, AT);
  const dash = C.dashboard(deals, '2026-10-29');
  assert.equal(dash.open, 2); assert.equal(dash.won, 1); assert.equal(dash.lost, 2); assert.equal(dash.discarded, 1);
  assert.equal(dash.win_rate, 33.3);
  assert.deepEqual(dash.lost_by_reason, { competitor: 1, price: 1 });
  assert.deepEqual(dash.competitors.map(c => [c.name, c.won, c.lost]).sort(), [['OI', 1, 0], ['VIVO', 0, 1]]);
  assert.deepEqual(dash.follow_up, { overdue: 1, today: 1, upcoming: 0, missing: 0 });
  const expected = deals.filter(d => !d.outcome).reduce((s, d) => s + d.mrr * C.STAGES.find(x => x.id === d.stage).probability, 0);
  assert.ok(Math.abs(dash.forecast_mrr - expected) < 0.01);
  assert.equal(dash.by_stage.reduce((s, x) => s + x.count, 0), 2);
});

test('state merge keeps seed order, overrides changed deals and appends new ones; backups are validated', () => {
  const base = seed(), changed = C.applyAction(base[3], { type: 'move', stage: 'viability' }, AT);
  const created = C.createDeal({ title: 'Condomínio Teste', type: 'condo', mrr: 1500, lat: -22.2, lng: -45.9, city_id: 'pouso-alegre' }, AT, 1);
  const merged = C.mergeState(base, { deals: [changed, created] });
  assert.equal(merged.length, base.length + 1); assert.equal(merged[3].stage, 'viability'); assert.equal(merged.at(-1).id, 'CRM-N0001');
  assert.throws(() => C.createDeal({ title: '', type: 'condo', mrr: 1, lat: 0, lng: 0 }, AT, 2), /título/);
  assert.throws(() => C.validateImport({ format: 'other', deals: [] }), /backup/);
  assert.throws(() => C.validateImport({ format: 'urbia-isp-crm', deals: [{ id: 'X', stage: 'nope', history: [], type: 'condo' }] }), /inválido/);
  assert.equal(C.validateImport({ format: 'urbia-isp-crm', deals: [created], seq: 1 }).deals.length, 1);
});
