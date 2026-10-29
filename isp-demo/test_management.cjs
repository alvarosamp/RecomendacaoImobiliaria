'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const E = require('./web/management-engine.js');
const load = name => JSON.parse(fs.readFileSync(path.join(__dirname, 'data', name), 'utf8'));
const db = load('simulation.json'), territory = load('territory.json'), radar = load('radar.json');
const asOf = db.meta.as_of;

const clients = [
  { id:'A', city_id:'c', cto_id:'X', status:'active', installed_at:'2026-01-10', cancelled_at:null, suspended_at:null, monthly_price:100, lat:0, lng:0 },
  { id:'B', city_id:'c', cto_id:'X', status:'cancelled', installed_at:'2026-01-15', cancelled_at:'2026-02-20', suspended_at:null, monthly_price:50, lat:0, lng:0 },
  { id:'C', city_id:'c', cto_id:'X', status:'suspended', installed_at:'2026-02-01', cancelled_at:null, suspended_at:'2026-03-05', monthly_price:80, lat:0, lng:0 },
];

test('revenue counts suspended contracts as at risk, not billed, and churn uses the previous month base', () => {
  const s = E.revenueSeries(clients, '2026-03-20');
  assert.deepEqual(s.map(x => x.month), ['2026-01', '2026-02', '2026-03']);
  assert.equal(s[0].mrr, 150); assert.equal(s[0].churn_pct, null);
  assert.equal(s[1].mrr, 180); assert.equal(s[1].exits, 1); assert.equal(s[1].churn_pct, 50);
  assert.equal(s[2].mrr, 100); assert.equal(s[2].at_risk, 80); assert.equal(s[2].connected, 2); assert.equal(s[2].billed, 1);
});

test('revenue of the snapshot reconciles with the inventory and breakdowns sum to the total', () => {
  const last = E.revenueSeries(db.clients, asOf).at(-1);
  const billed = db.clients.filter(c => c.status === 'active');
  assert.equal(last.billed, billed.length);
  assert.ok(Math.abs(last.mrr - billed.reduce((s, c) => s + c.monthly_price, 0)) < 0.01);
  const byCity = E.revenueBreakdown(db.clients, asOf, c => c.city_id);
  assert.ok(Math.abs(byCity.reduce((s, g) => s + g.mrr, 0) - last.mrr) < 0.05);
  assert.equal(byCity.reduce((s, g) => s + g.contracts, 0), last.connected);
});

test('capacity forecast: full boxes first, no trend means no exhaustion date, pending requests raise risk', () => {
  const ctos = [{ id:'X', city_id:'c', capacity:3, status:'operational' }, { id:'Y', city_id:'c', capacity:16, status:'operational' }];
  const f = E.capacityForecast(ctos, clients, [{ nearest_cto:'Y', triage:'survey' }], '2026-03-20');
  const y = f.find(r => r.id === 'Y'), x = f.find(r => r.id === 'X');
  assert.equal(y.months_to_full, null); assert.equal(y.risk, 'ok'); assert.equal(y.pending_requests, 1);
  assert.equal(x.used, 2); assert.equal(x.free, 1);
  const full = E.capacityForecast([{ ...ctos[0], capacity:2 }], clients, [], '2026-03-20')[0];
  assert.equal(full.risk, 'full'); assert.equal(full.months_to_full, 0);
  const snapshot = E.capacityForecast(db.ctos, db.clients, db.requests, asOf);
  assert.equal(snapshot.length, db.ctos.length);
  const order = { full:0, critical:1, watch:2, ok:3 };
  snapshot.slice(1).forEach((r, i) => assert.ok(order[snapshot[i].risk] <= order[r.risk]));
});

test('census cell index locates installations and never double counts them', () => {
  for (const city of territory.cities) {
    const index = E.cellIndex(city.cells);
    city.cells.slice(0, 50).forEach(cell => assert.equal(index.find(cell), cell));
    const rows = E.territoryCells(city.id, { cells: city.cells, clients: db.clients, ctos: db.ctos, radarRegions: [] });
    const connected = db.clients.filter(c => c.city_id === city.id && c.status !== 'cancelled');
    const placed = rows.reduce((s, r) => s + r.subscribers, 0);
    assert.ok(placed <= connected.length);
    assert.ok(placed / connected.length > 0.9, `${city.id}: ${placed}/${connected.length}`);
    rows.forEach(r => assert.ok(r.gap >= 0));
  }
});

test('territory actions follow their documented criteria and satellite context does not change the action', () => {
  const city = territory.cities[0], regions = radar.cities.flatMap(c => c.regions), opts = { radius: 250, target: 0.25, minHomes: 20 };
  const withSat = E.territoryCells(city.id, { cells: city.cells, clients: db.clients, ctos: db.ctos, radarRegions: regions }, opts);
  const without = E.territoryCells(city.id, { cells: city.cells, clients: db.clients, ctos: db.ctos, radarRegions: [] }, opts);
  assert.deepEqual(withSat.map(r => r.action), without.map(r => r.action));
  assert.ok(withSat.some(r => r.satellite_regions.length));
  withSat.filter(r => r.action).forEach(r => {
    assert.ok(r.homes >= 20);
    if (r.action === 'capture') { assert.ok(r.covered); assert.ok(r.penetration < 25); }
    if (r.action === 'capacity') { assert.equal(r.covered, false); assert.ok(r.nearest_cto_m <= 250); }
    if (r.action === 'expand') { assert.ok(r.nearest_cto_m > 250 && r.nearest_cto_m <= 1500); }
  });
  const ranked = E.rankTerritory(withSat), order = { capacity:0, capture:1, expand:2 };
  ranked.slice(1).forEach((r, i) => assert.ok(order[ranked[i].action] <= order[r.action]));
});

test('work orders come from the snapshot with unique ids, SLA deadlines and no field visit for retention', () => {
  const orders = E.buildWorkOrders(db, asOf);
  assert.equal(new Set(orders.map(o => o.id)).size, orders.length);
  assert.equal(orders.filter(o => o.type === 'corrective').length, db.ctos.filter(c => c.status !== 'operational').length);
  assert.equal(orders.filter(o => o.type === 'survey').length, db.requests.filter(r => r.triage === 'survey').length);
  assert.equal(orders.filter(o => o.type === 'retention').length, db.clients.filter(c => c.status === 'suspended').length);
  assert.ok(orders.filter(o => o.type === 'retention').every(o => o.field === false));
  assert.equal(orders[0].priority, 'critical');
  orders.forEach(o => assert.equal(new Date(o.due_at) - new Date(o.created_at), E.SLA_HOURS[o.priority] * 3600000));
});

test('local edits are merged without mutating the generated orders; auto assignment stays in the city and balances load', () => {
  const orders = E.buildWorkOrders(db, asOf), before = JSON.stringify(orders);
  const teams = [{ id:'T1', city_id:'pouso-alegre' }, { id:'T2', city_id:'pouso-alegre' }, { id:'T3', city_id:'itajuba' }];
  const changes = E.autoAssign(orders, teams);
  const merged = E.applyOverrides(orders, { overrides: changes, created: [] });
  assert.equal(JSON.stringify(orders), before);
  merged.filter(o => o.team).forEach(o => assert.equal(teams.find(t => t.id === o.team).city_id, o.city_id));
  assert.ok(merged.filter(o => o.city_id === 'santa-rita').every(o => !o.team));
  const t1 = merged.filter(o => o.team === 'T1').length, t2 = merged.filter(o => o.team === 'T2').length;
  assert.ok(Math.abs(t1 - t2) <= 1);
  assert.deepEqual(E.autoAssign(merged, teams), {});
  const done = E.applyOverrides(orders, { overrides: { [orders[0].id]: { status: 'done' } }, created: [] });
  assert.equal(done.at(-1).id, orders[0].id);
  assert.equal(E.isOverdue(done.at(-1), '2100-01-01'), false);
});

test('day route visits each assigned stop once, in nearest-neighbour order from the base', () => {
  const base = { lat: 0, lng: 0 };
  const stops = [{ id:'far', lat:0, lng:0.02, priority:'low', due_at:'2' , status:'open' }, { id:'near', lat:0, lng:0.005, priority:'low', due_at:'1', status:'open' }, { id:'done', lat:0, lng:0.001, priority:'low', due_at:'0', status:'done' }];
  const r = E.dayRoute(base, stops);
  assert.deepEqual(r.stops.map(s => s.id), ['near', 'far']);
  assert.ok(Math.abs(r.straight_km - 2.22) < 0.02);
  assert.equal(E.dayRoute(base, []).straight_km, 0);
  const urgent = E.dayRoute(base, [...stops, { id:'outage', lat:0, lng:0.03, priority:'critical', due_at:'3', status:'open' }]);
  assert.deepEqual(urgent.stops.map(s => s.id), ['outage', 'far', 'near']);
});
