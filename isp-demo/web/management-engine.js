/* Deterministic management calculations over the synthetic inventory, IBGE cells and satellite screening. No external calls. */
(function (root) {
  'use strict';
  const DAY = 86400000;
  const round = (value, decimals = 1) => Number(value.toFixed(decimals));
  const toDate = value => new Date(value.length === 10 ? value + 'T12:00:00-03:00' : value);
  const addDays = (iso, days) => new Date(toDate(iso).getTime() + days * DAY).toISOString().slice(0, 10);
  const connected = c => c.status !== 'cancelled';
  const occupiedAt = (c, at) => c.installed_at <= at && (!c.cancelled_at || c.cancelled_at > at);
  const billedAt = (c, at) => occupiedAt(c, at) && (!c.suspended_at || c.suspended_at > at);
  function distance(a, b) {
    const rad = Math.PI / 180, dLat = (b.lat - a.lat) * rad, dLng = (b.lng - a.lng) * rad;
    const h = Math.sin(dLat / 2) ** 2 + Math.cos(a.lat * rad) * Math.cos(b.lat * rad) * Math.sin(dLng / 2) ** 2;
    return 6371000 * 2 * Math.asin(Math.sqrt(h));
  }
  const monthEnd = month => { const [y, m] = month.split('-').map(Number); return new Date(Date.UTC(y, m, 0)).toISOString().slice(0, 10); };

  /* Monthly recurring revenue. Suspended contracts keep the port but are treated as revenue at risk, not billed. */
  function revenueSeries(clients, asOf) {
    const months = [], first = clients.map(c => c.installed_at.slice(0, 7)).sort()[0];
    // Continuous range: a month without installations still has a base, exits and revenue.
    for (let [y, m] = (first || asOf.slice(0, 7)).split('-').map(Number); `${y}-${String(m).padStart(2, '0')}` <= asOf.slice(0, 7); m === 12 ? (y++, m = 1) : m++) months.push(`${y}-${String(m).padStart(2, '0')}`);
    return months.map((month, i) => {
      const at = i === months.length - 1 ? asOf : monthEnd(month);
      const start = i ? monthEnd(months[i - 1]) : null;
      const base = start ? clients.filter(c => occupiedAt(c, start)).length : 0;
      const exits = clients.filter(c => c.cancelled_at && c.cancelled_at.slice(0, 7) === month && c.cancelled_at <= at).length;
      const entries = clients.filter(c => c.installed_at.slice(0, 7) === month && c.installed_at <= at).length;
      const billed = clients.filter(c => billedAt(c, at)), atRisk = clients.filter(c => occupiedAt(c, at) && c.suspended_at && c.suspended_at <= at);
      return {
        month, at, entries, exits, net: entries - exits,
        connected: clients.filter(c => occupiedAt(c, at)).length,
        billed: billed.length,
        mrr: round(billed.reduce((s, c) => s + c.monthly_price, 0), 2),
        at_risk: round(atRisk.reduce((s, c) => s + c.monthly_price, 0), 2),
        churn_pct: base ? round(exits / base * 100, 2) : null,
      };
    });
  }
  function revenueBreakdown(clients, asOf, key) {
    const groups = new Map();
    clients.filter(c => occupiedAt(c, asOf)).forEach(c => {
      const id = key(c), g = groups.get(id) || { id, contracts: 0, billed: 0, mrr: 0, at_risk: 0 };
      g.contracts++;
      if (billedAt(c, asOf)) { g.billed++; g.mrr += c.monthly_price; } else g.at_risk += c.monthly_price;
      groups.set(id, g);
    });
    return [...groups.values()].map(g => ({ ...g, mrr: round(g.mrr, 2), at_risk: round(g.at_risk, 2), arpu: g.billed ? round(g.mrr / g.billed, 2) : null })).sort((a, b) => b.mrr - a.mrr);
  }

  /* Port saturation forecast from the recent net additions of each CTO; a linear trend, not a sales forecast. */
  function capacityForecast(ctos, clients, requests, asOf, windowDays = 90) {
    const from = addDays(asOf, -windowDays), months = windowDays / 30;
    return ctos.map(cto => {
      const linked = clients.filter(c => c.cto_id === cto.id);
      const used = linked.filter(connected).length, free = cto.capacity - used;
      const net = linked.filter(c => c.installed_at > from && c.installed_at <= asOf).length - linked.filter(c => c.cancelled_at && c.cancelled_at > from && c.cancelled_at <= asOf).length;
      const rate = round(net / months, 2);
      const pending = requests.filter(r => r.nearest_cto === cto.id && ['survey', 'capacity'].includes(r.triage)).length;
      const months_to_full = free === 0 ? 0 : rate > 0 ? round(free / rate, 1) : null;
      const risk = free === 0 ? 'full' : (months_to_full !== null && months_to_full <= 2) || pending >= free ? 'critical' : months_to_full !== null && months_to_full <= 6 ? 'watch' : 'ok';
      return { id: cto.id, city_id: cto.city_id, sector: cto.sector, street: cto.street, lat: cto.lat, lng: cto.lng, status: cto.status, capacity: cto.capacity, used, free, net_window: net, net_per_month: rate, pending_requests: pending, months_to_full, risk };
    }).sort((a, b) => RISK_ORDER[a.risk] - RISK_ORDER[b.risk] || (a.months_to_full ?? 1e9) - (b.months_to_full ?? 1e9) || b.pending_requests - a.pending_requests);
  }
  const RISK_ORDER = { full: 0, critical: 1, watch: 2, ok: 3 };

  /* Index regular 200 m census cells by their grid key so each point is located without a full scan. */
  function cellIndex(cells) {
    const index = new Map();
    cells.forEach(cell => index.set(cell.id.split(':').slice(1).join(':'), cell));
    const sample = cells[0];
    if (!sample) return { find: () => null };
    const [, ix, iy] = sample.id.split(':').map(Number), [[s, w], [n, e]] = sample.bounds;
    const dLat = n - s, dLng = e - w, lat0 = s - iy * dLat, lng0 = w - ix * dLng;
    const inside = (cell, p) => cell && p.lat >= cell.bounds[0][0] && p.lat < cell.bounds[1][0] && p.lng >= cell.bounds[0][1] && p.lng < cell.bounds[1][1];
    return {
      find(p) {
        const x = Math.floor((p.lng - lng0) / dLng), y = Math.floor((p.lat - lat0) / dLat);
        for (const [dx, dy] of [[0, 0], [1, 0], [-1, 0], [0, 1], [0, -1]]) { const cell = index.get(`${x + dx}:${y + dy}`); if (inside(cell, p)) return cell; }
        return null;
      },
    };
  }

  /* Combine real census addresses, synthetic installations and capacity, and the real Sentinel-2 screen per cell. */
  function territoryCells(city, { cells, clients, ctos, radarRegions = [] }, options = {}) {
    const { radius = 250, minHomes = 20, target = 0.25, expansionMax = 1500, radarRadius = 300 } = options;
    const index = cellIndex(cells), counts = new Map();
    clients.filter(c => c.city_id === city && connected(c)).forEach(c => { const cell = index.find(c); if (cell) counts.set(cell.id, (counts.get(cell.id) || 0) + 1); });
    const cityCtos = ctos.filter(c => c.city_id === city).map(c => ({ ...c, free: c.capacity - clients.filter(x => x.cto_id === c.id && connected(x)).length }));
    const regions = radarRegions.filter(r => r.city_id === city);
    return cells.map(cell => {
      const homes = cell.residential, subscribers = counts.get(cell.id) || 0;
      const near = cityCtos.map(c => ({ cto: c, d: distance(cell, c) })).sort((a, b) => a.d - b.d);
      const inRadius = near.filter(x => x.d <= radius), available = inRadius.filter(x => x.cto.status === 'operational' && x.cto.free > 0);
      const satellite = regions.filter(r => distance(cell, r) <= radarRadius);
      const penetration = homes ? subscribers / homes : null, gap = Math.max(0, Math.round(homes * target) - subscribers);
      let action = null;
      if (homes >= minHomes) {
        if (available.length && penetration < target) action = 'capture';
        else if (inRadius.length && !available.length) action = 'capacity';
        else if (!inRadius.length && near[0] && near[0].d <= expansionMax) action = 'expand';
      }
      return {
        id: cell.id, city_id: city, lat: cell.lat, lng: cell.lng, bounds: cell.bounds, homes, addresses: cell.total, subscribers,
        penetration: penetration === null ? null : round(penetration * 100, 1), gap,
        nearest_cto: near[0]?.cto.id || null, nearest_cto_m: near[0] ? Math.round(near[0].d) : null,
        free_ports_in_radius: available.reduce((s, x) => s + x.cto.free, 0), covered: available.length > 0,
        satellite_regions: satellite.map(r => r.id), satellite_changed_ha: round(satellite.reduce((s, r) => s + r.changed_area_ha, 0), 2),
        action,
      };
    });
  }
  const ACTION_ORDER = { capacity: 0, capture: 1, expand: 2 };
  function rankTerritory(rows) {
    return rows.filter(r => r.action).sort((a, b) => ACTION_ORDER[a.action] - ACTION_ORDER[b.action] || (b.satellite_regions.length > 0) - (a.satellite_regions.length > 0) || b.gap - a.gap || a.id.localeCompare(b.id));
  }

  /* Work orders derived from the snapshot. Manual orders and local edits are merged by the caller. */
  const SLA_HOURS = { critical: 4, high: 24, medium: 72, low: 120 };
  function buildWorkOrders({ ctos, clients, requests, pops }, asOf, options = {}) {
    const { weakSignal = -25 } = options, orders = [];
    const add = (o) => orders.push({ status: 'open', team: null, ...o, due_at: new Date(toDate(o.created_at).getTime() + SLA_HOURS[o.priority] * 3600000).toISOString() });
    ctos.filter(c => c.status !== 'operational').forEach(c => add({ id: `OS-COR-${c.id}`, type: 'corrective', priority: c.status === 'offline' ? 'critical' : 'high', title: c.incident || 'Ocorrência na CTO', city_id: c.city_id, lat: c.lat, lng: c.lng, ref: { kind: 'cto', id: c.id }, created_at: asOf + 'T08:00:00-03:00', affected: clients.filter(x => x.cto_id === c.id && connected(x)).length }));
    clients.filter(c => c.status === 'active' && c.optical_dbm !== null && c.optical_dbm < weakSignal).forEach(c => add({ id: `OS-PRE-${c.id}`, type: 'preventive', priority: 'medium', title: `Sinal simulado ${c.optical_dbm} dBm abaixo de ${weakSignal} dBm`, city_id: c.city_id, lat: c.lat, lng: c.lng, ref: { kind: 'client', id: c.id }, created_at: asOf + 'T07:00:00-03:00', affected: 1 }));
    requests.filter(r => r.triage === 'survey').forEach(r => add({ id: `OS-VIS-${r.id}`, type: 'survey', priority: 'medium', title: `Vistoria de viabilidade · ${r.street}`, city_id: r.city_id, lat: r.lat, lng: r.lng, ref: { kind: 'request', id: r.id }, created_at: r.created_at + 'T09:00:00-03:00', affected: 0 }));
    requests.filter(r => r.triage === 'capacity').forEach(r => add({ id: `OS-PRJ-${r.id}`, type: 'project', priority: 'low', title: `Estudar ampliação · ${r.nearest_cto} sem porta`, city_id: r.city_id, lat: r.lat, lng: r.lng, ref: { kind: 'request', id: r.id }, created_at: r.created_at + 'T09:00:00-03:00', affected: 0 }));
    clients.filter(c => c.status === 'suspended').forEach(c => add({ id: `OS-RET-${c.id}`, type: 'retention', priority: 'low', title: `Contato de retenção · ${c.monthly_price.toFixed(2).replace('.', ',')} em risco`, city_id: c.city_id, lat: c.lat, lng: c.lng, ref: { kind: 'client', id: c.id }, created_at: c.suspended_at + 'T10:00:00-03:00', affected: 1, field: false }));
    return orders.sort((a, b) => PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority] || a.due_at.localeCompare(b.due_at) || a.id.localeCompare(b.id));
  }
  const PRIORITY_ORDER = { critical: 0, high: 1, medium: 2, low: 3 };
  function applyOverrides(orders, state) {
    const merged = orders.concat(state.created || []).map(o => ({ ...o, ...(state.overrides?.[o.id] || {}) }));
    return merged.sort((a, b) => (a.status === 'done') - (b.status === 'done') || PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority] || a.due_at.localeCompare(b.due_at) || a.id.localeCompare(b.id));
  }
  const isOverdue = (order, now) => order.status !== 'done' && order.due_at < now;

  /* Balance open field orders across the teams of each city, highest priority first. Returns only the changes. */
  function autoAssign(orders, teams) {
    const load = new Map(teams.map(t => [t.id, orders.filter(o => o.team === t.id && o.status !== 'done').length])), changes = {};
    orders.filter(o => !o.team && o.status === 'open' && o.field !== false).forEach(o => {
      const options = teams.filter(t => t.city_id === o.city_id).sort((a, b) => load.get(a.id) - load.get(b.id) || a.id.localeCompare(b.id));
      if (!options.length) return;
      changes[o.id] = { team: options[0].id, status: 'scheduled' };
      load.set(options[0].id, load.get(options[0].id) + 1);
    });
    return changes;
  }

  /* Visit order: critical/high orders first, then the rest, each tier by nearest neighbour in straight line from the
     previous stop. Not a road route or a driving instruction. */
  function dayRoute(base, orders, limit = 8) {
    const chosen = orders.filter(o => o.status !== 'done' && o.field !== false).slice().sort((a, b) => PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority] || a.due_at.localeCompare(b.due_at)).slice(0, limit);
    const tiers = [chosen.filter(o => PRIORITY_ORDER[o.priority] <= 1), chosen.filter(o => PRIORITY_ORDER[o.priority] > 1)];
    const stops = []; let here = base, total = 0;
    tiers.forEach(left => {
      while (left.length) {
        let best = 0, bestD = Infinity;
        left.forEach((o, i) => { const d = distance(here, o); if (d < bestD) { bestD = d; best = i; } });
        const [next] = left.splice(best, 1); total += bestD; stops.push({ ...next, leg_m: Math.round(bestD) }); here = next;
      }
    });
    return { stops, straight_km: round(total / 1000, 2) };
  }

  /* Real Anatel market for one or more municipalities, merged by CNPJ. HHI is only meaningful inside one market. */
  function marketView(market, cityIds) {
    const cities = market.cities.filter(c => cityIds.includes(c.id)), providers = new Map(), sum = (a, b) => { Object.entries(b).forEach(([k, v]) => a[k] = (a[k] || 0) + v); return a; };
    cities.forEach(c => c.providers.forEach(p => {
      const merged = providers.get(p.cnpj) || { ...p, acessos: 0, acessos_12m_antes: 0, series: p.series.map(() => 0), cities: [] };
      merged.acessos += p.acessos; merged.acessos_12m_antes += p.acessos_12m_antes; merged.series = merged.series.map((v, i) => v + p.series[i]); merged.cities.push(c.id);
      providers.set(p.cnpj, merged);
    }));
    const total = cities.reduce((s, c) => s + c.total, 0), months = cities[0]?.series.map(s => s.month) || [];
    const list = [...providers.values()].map(p => ({ ...p, variacao_12m: p.acessos - p.acessos_12m_antes, share_pct: total ? round(p.acessos / total * 100, 2) : 0 })).sort((a, b) => b.acessos - a.acessos || a.cnpj.localeCompare(b.cnpj));
    return {
      cities: cities.map(c => c.id), total, total_12m_antes: cities.reduce((s, c) => s + c.total_12m_antes, 0), providers: list,
      hhi: cities.length === 1 ? cities[0].hhi_grupos : null,
      absent: cities.flatMap(c => (c.absent_in_reference || []).map(p => ({ ...p, city_id: c.id }))).sort((a, b) => b.ultimos_acessos - a.ultimos_acessos),
      tecnologia: cities.reduce((a, c) => sum(a, c.tecnologia), {}), tipo_pessoa: cities.reduce((a, c) => sum(a, c.tipo_pessoa), {}),
      series: months.map((month, i) => ({ month, total: cities.reduce((s, c) => s + c.series[i].total, 0) })),
    };
  }

  /* Commercial intelligence for one real company over its Minas Gerais footprint (Anatel accesses).
     Signals are rules on declared accesses and shares, not forecasts. */
  const SIGNAL = { lead: 30, move_pp: 2, room_share: 10, room_market: 2000 };
  const share = (a, t) => t ? a / t * 100 : null;
  function companyView(data, id) {
    const company = data.companies.find(c => c.id === id); if (!company) return null;
    const study = new Set(data.meta.study_municipalities), last = data.meta.series_months.length - 1;
    const rows = company.footprint.map(([code, ...series]) => {
      const total = data.municipalities[code].total, now = share(series[last], total[last]), before = share(series[0], total[0]);
      const r = { code, name: data.municipalities[code].name, study: study.has(code), series, acessos: series[last], acessos_antes: series[0], variacao: series[last] - series[0], mercado: total[last], mercado_antes: total[0], share_pct: now === null ? null : round(now, 2), share_antes_pct: before === null ? null : round(before, 2) };
      r.delta_pp = r.share_pct !== null && r.share_antes_pct !== null ? round(r.share_pct - r.share_antes_pct, 2) : null;
      r.absent = series[last] === 0;
      r.signal = r.absent ? 'absent' : r.share_pct >= SIGNAL.lead ? 'lead' : r.delta_pp <= -SIGNAL.move_pp && r.variacao < 0 ? 'defend' : r.delta_pp >= SIGNAL.move_pp ? 'grow' : r.share_pct < SIGNAL.room_share && r.mercado >= SIGNAL.room_market ? 'room' : 'stable';
      return r;
    }).sort((a, b) => b.acessos - a.acessos || a.code.localeCompare(b.code));
    const present = rows.filter(r => !r.absent), sum = (list, k) => list.reduce((s, r) => s + r[k], 0);
    const studyRows = present.filter(r => r.study);
    const pct = buckets => { const t = buckets.reduce((s, v) => s + v, 0); return t ? buckets.map(v => round(v / t * 100, 1)) : null; };
    const fast = mix => mix ? round(mix.slice(3).reduce((s, v) => s + v, 0), 1) : null; // ≥ 500 Mbps
    const speed = {};
    ['MG', ...data.meta.study_municipalities].forEach(code => { if (company.speed[code]) speed[code] = { company: pct(company.speed[code]), market: pct(data.market_speed[code]) }; });
    return {
      company, rows, months: data.meta.series_months,
      acessos: sum(present, 'acessos'), acessos_antes: sum(rows, 'acessos_antes'), municipios: present.length,
      counts: rows.reduce((a, r) => (a[r.signal] = (a[r.signal] || 0) + 1, a), {}),
      study_share: studyRows.length ? round(share(sum(studyRows, 'acessos'), sum(studyRows, 'mercado')), 2) : null,
      speed, fast_pct: fast(speed.MG?.company), market_fast_pct: fast(speed.MG?.market),
    };
  }
  /* Competitors in one municipality at the same company level, with share movement over the window. */
  function municipalityCompetition(data, code) {
    const total = data.municipalities[code]?.total, last = data.meta.series_months.length - 1;
    if (!total) return [];
    return data.companies.map(c => { const row = c.footprint.find(r => r[0] === code); if (!row) return null; const s = row.slice(1); return { id: c.id, name: c.name, porte: c.porte, series: s, acessos: s[last], variacao: s[last] - s[0], share_pct: round(share(s[last], total[last]), 2), delta_pp: round(share(s[last], total[last]) - share(s[0], total[0]), 2), share_series: s.map((v, i) => round(share(v, total[i]) || 0, 2)) }; })
      .filter(Boolean).sort((a, b) => b.acessos - a.acessos || a.id.localeCompare(b.id));
  }

  const api = { companyView, municipalityCompetition, SIGNAL, marketView, distance, revenueSeries, revenueBreakdown, capacityForecast, cellIndex, territoryCells, rankTerritory, buildWorkOrders, applyOverrides, autoAssign, dayRoute, isOverdue, SLA_HOURS, occupiedAt, billedAt };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.ManagementEngine = api;
})(typeof window !== 'undefined' ? window : globalThis);
