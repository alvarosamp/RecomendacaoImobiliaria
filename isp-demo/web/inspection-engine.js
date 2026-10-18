/* Deterministic synthetic telemetry. This module never connects to network equipment. */
(function (root) {
  'use strict';
  const DURATION = 24;
  const round = (value, decimals = 1) => Number(value.toFixed(decimals));
  class InspectionSession {
    constructor({ cto, clients, profile = 'baseline', startedAt = new Date().toISOString() }) {
      if (!cto || !['baseline', 'normal', 'degraded', 'outage'].includes(profile)) throw new Error('Invalid inspection target or scenario');
      this.cto = { ...cto };
      this.clients = clients.filter(c => c.cto_id === cto.id && c.status !== 'cancelled').map(c => ({ ...c }));
      this.profile = profile === 'baseline' ? ({ offline: 'outage', maintenance: 'degraded' }[cto.status] || 'normal') : profile;
      this.requestedProfile = profile;
      this.startedAt = startedAt;
      this.state = 'idle';
      this.elapsed = 0;
      this.samples = [];
      this.events = [];
      this.seed = [...cto.id].reduce((sum, char) => sum + char.charCodeAt(0), 0);
    }
    start() {
      if (this.state !== 'idle') return false;
      this.state = 'running';
      this.event('Sessão fictícia iniciada. Nenhum equipamento real será consultado.', 'info');
      return true;
    }
    pause() {
      if (this.state !== 'running') return false;
      this.state = 'paused'; this.event('Inspeção pausada; geração de amostras suspensa.', 'info'); return true;
    }
    resume() {
      if (this.state !== 'paused') return false;
      this.state = 'running'; this.event('Inspeção retomada.', 'info'); return true;
    }
    stop() {
      if (!['running', 'paused'].includes(this.state)) return false;
      this.state = 'stopped'; this.event('Sessão interrompida. O resultado é parcial.', 'warning'); return true;
    }
    event(message, severity) { this.events.push({ second: this.elapsed, message, severity }); }
    tick() {
      if (this.state !== 'running') return null;
      this.elapsed += 1;
      const wave = Math.sin(this.elapsed * 1.7 + this.seed);
      const active = this.clients.filter(c => c.status === 'active').length;
      const optics = this.elapsed >= 5, network = this.elapsed >= 11;
      const outage = this.profile === 'outage', degraded = this.profile === 'degraded';
      const values = this.clients.map(c => c.optical_dbm).filter(v => typeof v === 'number' && Number.isFinite(v));
      const baseline = values.length ? Math.max(-24, Math.min(-19, values.reduce((a,b) => a+b, 0) / values.length)) : -21;
      const sample = {
        second: this.elapsed,
        optical_dbm: !optics || outage ? null : round(degraded ? -25.7 - this.elapsed / 12 + wave * .7 : baseline + wave * .3),
        latency_ms: !network || outage ? null : round(degraded ? 34 + (wave + 1) * 19 : 4 + (wave + 1) * 1.8),
        packet_loss_pct: !network ? null : outage ? 100 : round(degraded ? 3 + (wave + 1) * 2.5 : (wave + 1) * .1),
        responding: !network ? null : outage ? 0 : degraded ? Math.max(0, active - Math.ceil(active * .18)) : active,
        testable: active,
      };
      this.samples.push(sample);
      if (this.elapsed === 1) this.event(`Alvo identificado: ${this.cto.id}, origem ${this.cto.pop_id}.`, 'info');
      if (this.elapsed === 4) this.event(`Inventário fictício: ${this.clients.length}/${this.cto.capacity} portas ocupadas. Suspensões reservam porta e não recebem teste de sessão.`, 'info');
      if (this.elapsed === 8) this.event(outage ? 'Sem leitura óptica no cenário de rompimento.' : degraded ? 'Atenuação progressiva gerada no cenário de degradação.' : 'Leitura óptica estável no cenário normal.', outage || degraded ? 'warning' : 'success');
      if (this.elapsed === 12) this.event(outage ? 'Sem resposta simulada. Latência indisponível e perda de 100%.' : degraded ? 'Oscilação de latência e perda de pacotes simuladas.' : 'Respostas simuladas recebidas das instalações ativas.', outage || degraded ? 'warning' : 'success');
      if (this.elapsed === 18) this.event('Vínculos POP → CTO → porta conferidos no cadastro fictício; rota óptica real não foi medida.', 'info');
      if (this.elapsed === DURATION) { this.state = 'completed'; this.event('Inspeção simulada concluída. Resumo disponível para exportação.', 'success'); }
      return sample;
    }
    report() {
      return {
        synthetic: true, kind: 'simulated-inspection', version: 1,
        target_cto: this.cto.id, city_id: this.cto.city_id, pop_id: this.cto.pop_id,
        scenario: this.profile, requested_scenario: this.requestedProfile,
        started_at: this.startedAt, duration_simulated_seconds: this.elapsed,
        state: this.state, complete: this.state === 'completed',
        source_snapshot: '2026-10-18',
        occupied_ports: this.clients.length, capacity: this.cto.capacity,
        testable_installations: this.clients.filter(c => c.status === 'active').length,
        samples: this.samples.map(s => ({ ...s })), events: this.events.map(e => ({ ...e })),
        limitation: 'Valores inteiramente fictícios gerados no navegador. Sem consulta a OLT, ONU, SNMP, ICMP ou técnicos em campo. Não altera o inventário nem comprova disponibilidade real.',
      };
    }
  }
  const api = { InspectionSession, DURATION };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.InspectionSimulator = api;
})(typeof window !== 'undefined' ? window : globalThis);
