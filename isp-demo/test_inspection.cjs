'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { InspectionSession, DURATION } = require('./web/inspection-engine.js');
const cto = { id:'CTO-TEST-001', city_id:'test-city', pop_id:'POP-TEST', capacity:16, status:'operational' };
const clients = [
  { id:'A', cto_id:cto.id, port:1, status:'active', optical_dbm:-21 },
  { id:'B', cto_id:cto.id, port:2, status:'active', optical_dbm:-22 },
  { id:'C', cto_id:cto.id, port:3, status:'suspended', optical_dbm:-23 },
  { id:'D', cto_id:cto.id, port:4, status:'cancelled', optical_dbm:null },
  { id:'E', cto_id:'ANOTHER-CTO', port:1, status:'active', optical_dbm:-20 },
];
const make = profile => new InspectionSession({ cto, clients, profile, startedAt:'2026-10-18T18:00:00Z' });
const finish = session => { session.start(); for(let i=0;i<DURATION;i++)session.tick(); return session; };

test('pause/resume does not produce samples or accept duplicate starts', () => {
  const session=make('normal'); assert.equal(session.tick(),null);
  assert.equal(session.start(),true); assert.equal(session.start(),false);
  session.tick(); session.pause();
  assert.equal(session.tick(),null); assert.equal(session.elapsed,1);
  assert.equal(session.resume(),true); session.tick();
  assert.equal(session.elapsed,2); assert.equal(session.samples.length,2);
});
test('completed sessions have exactly 24 samples and cannot be resumed or ticked', () => {
  const session=finish(make('normal'));
  assert.equal(session.state,'completed'); assert.equal(session.report().complete,true);
  assert.equal(session.tick(),null); assert.equal(session.samples.length,24);
  assert.equal(session.resume(),false); assert.equal(session.start(),false);
});
test('stopped sessions preserve partial evidence without a completion claim', () => {
  const session=make('normal');session.start();session.tick();session.pause();session.stop();
  const report=session.report();
  assert.equal(report.state,'stopped');assert.equal(report.complete,false);
  assert.equal(report.samples.length,1);assert.equal(session.tick(),null);
});
test('outage has no invented signal or zero latency, and 100% packet loss only once tested', () => {
  const session=finish(make('outage'));
  for(const sample of session.samples){
    assert.equal(sample.optical_dbm,null);assert.equal(sample.latency_ms,null);
    assert.equal(sample.packet_loss_pct,sample.second>=11?100:null);
  }
  assert.equal(session.samples.at(-1).responding,0);
});
test('suspended ports remain occupied, but cancelled/unrelated clients do not enter the inspection', () => {
  const session=finish(make('normal')); const report=session.report();
  assert.equal(report.occupied_ports,3);assert.equal(report.testable_installations,2);
  assert.equal(session.samples.at(-1).responding,2);
});
test('baseline respects infrastructure status and degraded scenario differs from normal', () => {
  for(const [status,profile] of [['operational','normal'],['offline','outage'],['maintenance','degraded']]){
    assert.equal(new InspectionSession({cto:{...cto,status},clients}).profile,profile);
  }
  const normal=finish(make('normal')).samples.at(-1), degraded=finish(make('degraded')).samples.at(-1);
  assert.ok(degraded.optical_dbm<normal.optical_dbm);
  assert.ok(degraded.latency_ms>normal.latency_ms);
  assert.ok(degraded.packet_loss_pct>normal.packet_loss_pct);
});
test('simulation is deterministic and never mutates its source inventory or exported evidence', () => {
  const before=JSON.stringify({cto,clients});
  const one=finish(make('degraded')), two=finish(make('degraded'));
  assert.deepEqual(one.report(),two.report());
  assert.equal(JSON.stringify({cto,clients}),before);
  const report=one.report();report.samples[0].second=99;report.events[0].message='modified';
  assert.equal(one.samples[0].second,1);assert.notEqual(one.events[0].message,'modified');
  assert.equal(report.synthetic,true);
});
test('unrecognized scenario and missing target are rejected', () => {
  assert.throws(()=>make('unknown'));
  assert.throws(()=>new InspectionSession({clients}));
});
