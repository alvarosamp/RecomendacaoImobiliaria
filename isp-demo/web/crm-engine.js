/* Sales CRM for the ISP demo: pipeline, checklists, competitors, follow-ups and history. Pure functions; the caller
   persists the state. Inspired by the RagMatch CRM (staged pipeline, outcomes, required checklist, competitors,
   history log and fulfillment after a win). */
(function (root) {
  'use strict';
  const STAGES = [
    { id: 'new', name: 'Novo lead', probability: 0.05 },
    { id: 'qualification', name: 'Qualificação', probability: 0.15 },
    { id: 'viability', name: 'Viabilidade', probability: 0.3 },
    { id: 'proposal', name: 'Proposta', probability: 0.5 },
    { id: 'negotiation', name: 'Negociação', probability: 0.7 },
    { id: 'installation', name: 'Instalação', probability: 0.9 },
    { id: 'result', name: 'Resultado', probability: null },
  ];
  const OUTCOMES = { won: 'Ganho', lost: 'Perdido', discarded: 'Descartado' };
  const LOST_REASONS = { price: 'Preço', no_viability: 'Sem viabilidade técnica', competitor: 'Ficou com concorrente', no_answer: 'Sem retorno', gave_up: 'Desistiu', other: 'Outro' };
  const TYPES = { residential: 'Residencial', business: 'Empresarial', condo: 'Condomínio' };
  const CHECKLISTS = {
    residential: [['viability', 'Viabilidade confirmada (CTO com porta)', true], ['plan', 'Plano e valor aceitos', true], ['contract', 'Contrato/aceite registrado', true], ['schedule', 'Instalação agendada', true], ['docs', 'Documento conferido', false]],
    business: [['visit', 'Visita técnica feita', true], ['viability', 'Viabilidade e projeto confirmados', true], ['proposal', 'Proposta enviada', true], ['contract', 'Contrato assinado', true], ['sla', 'SLA e IP fixo definidos', false], ['schedule', 'Ativação agendada', true]],
    condo: [['meeting', 'Reunião com síndico', true], ['authorization', 'Autorização de passagem', true], ['project', 'Projeto de cabeamento interno', true], ['proposal', 'Proposta coletiva aprovada', true], ['schedule', 'Obra agendada', true]],
  };
  const stageIndex = id => STAGES.findIndex(s => s.id === id);
  const round = (v, d = 2) => Number(v.toFixed(d));
  const dayOf = iso => String(iso).slice(0, 10);

  /* Leads seeded from the synthetic installation requests; nothing invented beyond the request itself. */
  function seedDeals(requests, asOf) {
    const start = { survey: 'qualification', capacity: 'qualification', incident: 'qualification', outside: 'new' };
    return requests.map(r => ({
      id: `CRM-${r.id}`, title: `Pedido ${r.id} · ${r.street}`, type: 'residential', city_id: r.city_id, street: r.street, lat: r.lat, lng: r.lng,
      source: { kind: 'request', id: r.id }, stage: start[r.triage] || 'new', outcome: null, lost_reason: null,
      mrr: r.monthly_price, owner: null, contact: null, competitor: null, next_action: null, checklist: {},
      triage: r.triage, nearest_cto: r.nearest_cto, created_at: `${r.created_at}T09:00:00-03:00`, updated_at: `${r.created_at}T09:00:00-03:00`,
      history: [{ at: `${r.created_at}T09:00:00-03:00`, action: 'Lead criado a partir do pedido de instalação', detail: `Triagem: ${r.triage}` }],
      order_id: null, seeded_as_of: asOf,
    }));
  }

  function checklistStatus(deal) {
    const items = CHECKLISTS[deal.type] || [];
    const done = items.filter(([id]) => deal.checklist?.[id]);
    const missing = items.filter(([id, , required]) => required && !deal.checklist?.[id]);
    return { total: items.length, done: done.length, required_missing: missing.map(([id, label]) => ({ id, label })) };
  }

  /* All changes go through here: returns a new deal or throws a readable error. */
  function applyAction(deal, action, at) {
    const next = { ...deal, checklist: { ...deal.checklist }, history: deal.history.slice(), updated_at: at };
    const log = (text, detail) => next.history.push({ at, action: text, detail: detail ?? null });
    switch (action.type) {
      case 'move': {
        if (stageIndex(action.stage) < 0 || action.stage === 'result') throw new Error('Etapa inválida. Use ganho, perdido ou descartado para encerrar.');
        if (deal.outcome) throw new Error('Negócio encerrado. Reabra antes de mover.');
        if (action.stage === deal.stage) return deal;
        if (action.stage === 'installation' && checklistStatus(deal).required_missing.some(i => i.id !== 'schedule')) throw new Error('Conclua os itens obrigatórios do checklist (exceto o agendamento) antes da instalação.');
        next.stage = action.stage; log(`Etapa: ${STAGES[stageIndex(deal.stage)].name} → ${STAGES[stageIndex(action.stage)].name}`); break;
      }
      case 'win': {
        if (deal.outcome) throw new Error('Negócio já encerrado.');
        const missing = checklistStatus(deal).required_missing;
        if (missing.length) throw new Error(`Itens obrigatórios pendentes: ${missing.map(i => i.label).join('; ')}.`);
        next.stage = 'result'; next.outcome = 'won'; next.closed_at = at; next.closed_from = deal.stage; log('Ganho', `MRR ${deal.mrr}`); break;
      }
      case 'lose': {
        if (deal.outcome) throw new Error('Negócio já encerrado.');
        if (!LOST_REASONS[action.reason]) throw new Error('Informe o motivo da perda.');
        if (action.reason === 'competitor' && !(action.competitor || deal.competitor?.name)) throw new Error('Informe o concorrente que ficou com o cliente.');
        next.stage = 'result'; next.outcome = 'lost'; next.lost_reason = action.reason; next.closed_at = at; next.closed_from = deal.stage;
        if (action.competitor) next.competitor = { ...(deal.competitor || {}), name: action.competitor };
        log(`Perdido: ${LOST_REASONS[action.reason]}`, action.note || null); break;
      }
      case 'discard': {
        if (deal.outcome) throw new Error('Negócio já encerrado.');
        next.stage = 'result'; next.outcome = 'discarded'; next.closed_at = at; next.closed_from = deal.stage; log('Descartado', action.note || null); break;
      }
      case 'reopen': {
        if (!deal.outcome) return deal;
        next.stage = deal.closed_from || 'qualification'; next.outcome = null; next.lost_reason = null; next.closed_at = null; log('Reaberto'); break;
      }
      case 'check': {
        const item = (CHECKLISTS[deal.type] || []).find(([id]) => id === action.item);
        if (!item) throw new Error('Item de checklist inexistente.');
        next.checklist[action.item] = Boolean(action.done); log(`${action.done ? 'Concluído' : 'Reaberto'}: ${item[1]}`); break;
      }
      case 'update': {
        const allowed = ['title', 'type', 'mrr', 'owner', 'contact', 'competitor', 'next_action', 'plan_mbps'];
        const changed = Object.keys(action.fields).filter(k => allowed.includes(k) && JSON.stringify(action.fields[k]) !== JSON.stringify(deal[k]));
        if (action.fields.mrr !== undefined && !(Number(action.fields.mrr) >= 0)) throw new Error('Valor mensal inválido.');
        if (action.fields.type !== undefined && !TYPES[action.fields.type]) throw new Error('Tipo inválido.');
        changed.forEach(k => { next[k] = k === 'mrr' ? Number(action.fields[k]) : action.fields[k]; });
        if (action.fields.type && action.fields.type !== deal.type) next.checklist = {};
        if (!changed.length) return deal;
        log(`Atualizado: ${changed.join(', ')}`); break;
      }
      case 'note': {
        if (!String(action.text || '').trim()) throw new Error('Nota vazia.');
        log('Nota', String(action.text).trim().slice(0, 500)); break;
      }
      case 'link_order': next.order_id = action.order_id; log('Ordem de instalação criada', action.order_id); break;
      default: throw new Error('Ação desconhecida.');
    }
    return next;
  }

  function createDeal(fields, at, seq) {
    if (!String(fields.title || '').trim()) throw new Error('Informe um título.');
    if (!TYPES[fields.type]) throw new Error('Tipo inválido.');
    if (!(Number(fields.mrr) >= 0)) throw new Error('Valor mensal inválido.');
    if (!Number.isFinite(fields.lat) || !Number.isFinite(fields.lng)) throw new Error('Localização inválida.');
    return {
      id: `CRM-N${String(seq).padStart(4, '0')}`, title: String(fields.title).trim().slice(0, 120), type: fields.type, city_id: fields.city_id, street: fields.street || '',
      lat: fields.lat, lng: fields.lng, source: fields.source || { kind: 'manual', id: null }, stage: 'new', outcome: null, lost_reason: null,
      mrr: Number(fields.mrr), owner: fields.owner || null, contact: fields.contact || null, competitor: fields.competitor || null, next_action: fields.next_action || null,
      checklist: {}, created_at: at, updated_at: at, history: [{ at, action: 'Lead criado', detail: fields.source?.kind || 'manual' }], order_id: null,
    };
  }

  const followUpState = (deal, today) => deal.outcome ? null : !deal.next_action?.date ? 'missing' : deal.next_action.date < today ? 'overdue' : deal.next_action.date === today ? 'today' : 'upcoming';

  function dashboard(deals, today) {
    const open = deals.filter(d => !d.outcome), closed = deals.filter(d => d.outcome && d.outcome !== 'discarded');
    const won = deals.filter(d => d.outcome === 'won'), lost = deals.filter(d => d.outcome === 'lost');
    const byStage = STAGES.filter(s => s.id !== 'result').map(s => { const list = open.filter(d => d.stage === s.id); return { ...s, count: list.length, mrr: round(list.reduce((t, d) => t + d.mrr, 0)) }; });
    const count = (list, key) => list.reduce((a, d) => { const k = key(d); a[k] = (a[k] || 0) + 1; return a; }, {});
    const competitors = {};
    deals.filter(d => d.competitor?.name && d.outcome && d.outcome !== 'discarded').forEach(d => { const c = competitors[d.competitor.name] ||= { name: d.competitor.name, won: 0, lost: 0 }; c[d.outcome === 'won' ? 'won' : 'lost']++; });
    const follow = count(open, d => followUpState(d, today));
    return {
      open: open.length, pipeline_mrr: round(open.reduce((t, d) => t + d.mrr, 0)),
      forecast_mrr: round(open.reduce((t, d) => t + d.mrr * STAGES[stageIndex(d.stage)].probability, 0)),
      won: won.length, won_mrr: round(won.reduce((t, d) => t + d.mrr, 0)), lost: lost.length, discarded: deals.filter(d => d.outcome === 'discarded').length,
      win_rate: closed.length ? round(won.length / closed.length * 100, 1) : null,
      by_stage: byStage, lost_by_reason: count(lost, d => d.lost_reason),
      competitors: Object.values(competitors).sort((a, b) => (b.won + b.lost) - (a.won + a.lost) || a.name.localeCompare(b.name)),
      follow_up: { overdue: follow.overdue || 0, today: follow.today || 0, upcoming: follow.upcoming || 0, missing: follow.missing || 0 },
    };
  }

  /* Persisted state = seed + local changes; only changed or created deals are stored. */
  function mergeState(seed, state) {
    const changed = new Map((state.deals || []).map(d => [d.id, d]));
    return seed.map(d => changed.get(d.id) || d).concat((state.deals || []).filter(d => !seed.some(s => s.id === d.id)));
  }
  function validateImport(data) {
    if (!data || data.format !== 'urbia-isp-crm' || !Array.isArray(data.deals)) throw new Error('Arquivo não é um backup do CRM Urbia.');
    data.deals.forEach(d => { if (!d.id || !STAGES.some(s => s.id === d.stage) || !Array.isArray(d.history) || !TYPES[d.type]) throw new Error(`Negócio inválido no backup: ${d.id || '?'}`); });
    return { deals: data.deals, seq: Number(data.seq) || 0 };
  }

  const api = { STAGES, OUTCOMES, LOST_REASONS, TYPES, CHECKLISTS, seedDeals, checklistStatus, applyAction, createDeal, followUpState, dashboard, mergeState, validateImport };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.CrmEngine = api;
})(typeof window !== 'undefined' ? window : globalThis);
