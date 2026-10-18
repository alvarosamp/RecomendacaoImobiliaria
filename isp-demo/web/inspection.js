/* Presentation and timer controls for the synthetic inspection session. */
'use strict';
let inspectionSession = null, inspectionTimer = null;
const sessionStates = { idle:'Pronta para iniciar', running:'Inspeção em andamento', paused:'Inspeção pausada', completed:'Inspeção concluída', stopped:'Inspeção interrompida' };
const scenarioNames = { normal:'Operação normal', degraded:'Degradação óptica', outage:'Rompimento de fibra' };
const sessionTime = value => new Date(value).toLocaleTimeString('pt-BR', {timeZone:'America/Sao_Paulo'});

function initInspection() {
  $('inspection-start').onclick = startInspection;
  $('inspection-pause').onclick = () => {
    if (!inspectionSession) return;
    if (inspectionSession.state === 'running') { inspectionSession.pause(); clearInspectionTimer(); }
    else if (inspectionSession.state === 'paused') { inspectionSession.resume(); scheduleInspection(); }
    renderInspection();
  };
  $('inspection-stop').onclick = () => { if(inspectionSession) { inspectionSession.stop(); clearInspectionTimer(); renderInspection(); } };
  $('inspection-download').onclick = downloadInspection;
  $('inspection-target').onchange = renderInspection;
  $('inspection-scenario').onchange = renderInspection;
  document.addEventListener('visibilitychange', () => {
    if (document.hidden && inspectionSession?.state === 'running') {
      inspectionSession.pause(); clearInspectionTimer(); renderInspection();
    }
  });
  window.addEventListener('pagehide', clearInspectionTimer);
  refreshInspectionTargets();
}
function clearInspectionTimer() { if(inspectionTimer !== null)clearInterval(inspectionTimer); inspectionTimer = null; }
function scheduleInspection() {
  clearInspectionTimer();
  inspectionTimer = setInterval(() => {
    inspectionSession.tick();
    if(inspectionSession.state !== 'running') clearInspectionTimer();
    renderInspection();
  }, 1000);
}
function inspectionBusy() { return ['running','paused'].includes(inspectionSession?.state); }
function refreshInspectionTargets() {
  const current = $('inspection-target').value;
  const targets = scoped('ctos');
  $('inspection-target').innerHTML = targets.map(c => `<option value="${escapeHTML(c.id)}">${escapeHTML(c.id)} · ${escapeHTML(cityName(c.city_id))}</option>`).join('');
  if(targets.some(c=>c.id===current))$('inspection-target').value=current;
  renderInspection();
}
function openInspection(ctoId) {
  if (inspectionBusy() && inspectionSession.cto.id !== ctoId) {
    setView('inspection'); toast('Encerre a sessão atual antes de trocar o alvo.'); return;
  }
  const cto = db.ctos.find(c=>c.id===ctoId);
  if(cto && !inspectionBusy()) {
    if(inspectionSession&&inspectionSession.cto.id!==cto.id)inspectionSession=null;
    if(!inScope(cto)) { $('city').value=cto.city_id; $('sector').value='all'; selected=null; renderAll(true); }
    $('inspection-target').value=cto.id;
  }
  setView('inspection'); renderInspection();
  $('inspection-section').scrollIntoView({behavior:'smooth',block:'start'});
}
function startInspection() {
  if(inspectionBusy())return;
  const cto = db.ctos.find(c=>c.id===$('inspection-target').value);
  if(!cto)return;
  inspectionSession = new InspectionSimulator.InspectionSession({cto, clients:db.clients, profile:$('inspection-scenario').value});
  inspectionSession.start(); scheduleInspection(); renderInspection();
}
function inspectionMetric(label, value, unit, note) {
  return `<article class="inspection-metric"><span>${label}</span><strong>${value}<small>${unit}</small></strong><p>${note}</p></article>`;
}
function sparkline(samples, key, color) {
  const valid=samples.filter(s=>s[key]!==null);
  if(!valid.length){const measured=(samples.at(-1)?.second||0)>=(key==='optical_dbm'?5:11);return `<div class="inspection-chart-empty">${measured?'Sem leitura disponível no cenário escolhido.':'Aguardando a etapa de medição simulada…'}</div>`;}
  const values=valid.map(s=>s[key]), min=Math.min(...values)-.5, max=Math.max(...values)+.5;
  const points=valid.map(s=>`${12+(s.second-1)/23*556},${94-(s[key]-min)/(max-min)*72}`).join(' ');
  return `<svg viewBox="0 0 580 112" role="img" aria-label="Evolução das amostras fictícias"><path d="M12 22H568M12 58H568M12 94H568" stroke="#e7eee7" stroke-dasharray="3 5"/><polyline points="${points}" fill="none" stroke="${color}" stroke-width="2.5" stroke-linecap="round"/><text x="12" y="110">0 s</text><text x="544" y="110">24 s</text></svg>`;
}
function renderInspection() {
  if(!$('inspection-target'))return;
  const session=inspectionSession, busy=inspectionBusy();
  const target=session ? session.cto : db.ctos.find(c=>c.id===$('inspection-target').value);
  const latest=session?.samples.at(-1), state=session?.state||'idle', elapsed=session?.elapsed||0;
  $('inspection-target').disabled=busy;
  $('inspection-scenario').disabled=busy;
  $('inspection-start').disabled=busy||!$('inspection-target').value;
  $('inspection-start').textContent=session&&!busy?'Iniciar nova inspeção':'Iniciar inspeção';
  $('inspection-pause').disabled=!busy;
  $('inspection-pause').textContent=state==='paused'?'Retomar':'Pausar';
  $('inspection-stop').disabled=!busy;
  $('inspection-download').disabled=!session||!session.samples.length;
  // Lock territorial filters while a session is active: its captured target cannot change silently.
  ['city','sector','clear-filters'].forEach(id=>$(id).disabled=busy);
  $('inspection-state').textContent=sessionStates[state];
  $('inspection-state').className='inspection-state '+state;
  $('inspection-clock').textContent=`${String(elapsed).padStart(2,'0')} / 24 s simulados`;
  $('inspection-progress').style.width=`${elapsed/24*100}%`;
  $('inspection-progress-track').setAttribute('aria-valuenow',elapsed);
  $('inspection-context').textContent=session ? `${session.cto.id} · ${cityName(session.cto.city_id)} · ${scenarioNames[session.profile]} · sessão às ${sessionTime(session.startedAt)} (Brasília)` : 'Escolha uma CTO e um cenário para acompanhar uma sessão de 24 segundos.';
  const disconnected=session?.profile==='outage'&&elapsed>=5;
  $('inspection-metrics').innerHTML = inspectionMetric('Sinal óptico',latest?.optical_dbm===null||!latest?'—':n(latest.optical_dbm),'dBm',disconnected?'Sem leitura no cenário de rompimento':'Leitura fictícia · não é medição de ONU') + inspectionMetric('Latência',latest?.latency_ms===null||!latest?'—':n(latest.latency_ms),'ms',disconnected&&elapsed>=11?'Sem resposta; latência indisponível':'Teste fictício · nenhum pacote é enviado') + inspectionMetric('Perda de pacotes',latest?.packet_loss_pct===null||!latest?'—':n(latest.packet_loss_pct),'%',elapsed<11?'Aguardando etapa de conectividade':'Percentual inteiramente simulado') + inspectionMetric('Instalações respondendo',latest?.responding===null||!latest?'—':`${latest.responding}/${latest.testable}`,'', 'Somente contratos ativos; suspensos excluídos');
  const stages=['Identificar alvo','Verificar sinal','Testar conectividade','Consolidar evidências'];
  const cutoffs=[4,10,18,24];
  $('inspection-steps').innerHTML=stages.map((label,i)=>`<li class="${elapsed>=cutoffs[i]?'done':elapsed>=(i?cutoffs[i-1]:0)&&busy?'current':''}"><span>${elapsed>=cutoffs[i]?'✓':i+1}</span>${label}</li>`).join('');
  $('inspection-optical-chart').innerHTML=sparkline(session?.samples||[],'optical_dbm','#629876');
  $('inspection-latency-chart').innerHTML=sparkline(session?.samples||[],'latency_ms','#6a93b6');
  const clients=session?session.clients:target?ctoClients(target.id):[];
  $('inspection-ports-title').textContent=target?`${target.id} · ${clients.length}/${target.capacity} portas ocupadas`:'Nenhuma CTO neste recorte';
  $('inspection-ports').innerHTML=target?Array.from({length:target.capacity},(_,i)=>{
    const client=clients.find(c=>c.port===i+1);
    const tech=!client?'free':client.status==='suspended'?'suspended':elapsed<11?'pending':session.profile==='outage'?'down':session.profile==='degraded'?'alert':'online';
    const desc={free:'Livre',suspended:'Suspensa; sem teste',pending:'Aguardando teste',down:'Sem resposta simulada',alert:'Cenário degradado',online:'Resposta simulada'}[tech];
    return `<div class="inspection-port ${tech}"><strong>${String(i+1).padStart(2,'0')}</strong><span>${client?escapeHTML(client.id):'Porta livre'}</span><small>${desc}</small></div>`;
  }).join(''):'';
  $('inspection-events').innerHTML=session?session.events.slice().reverse().map(event=>`<li class="${event.severity}"><time>+${String(event.second).padStart(2,'0')}s</time><span>${escapeHTML(event.message)}</span></li>`).join(''):'<li class="inspection-empty">Os eventos aparecerão aqui ao iniciar a inspeção.</li>';
  const summary=$('inspection-summary');
  summary.hidden=!session||!['completed','stopped'].includes(state);
  if(!summary.hidden) {
    const result={normal:'O cenário terminou com respostas simuladas estáveis. Isso não comprova disponibilidade real.',degraded:'O cenário apresentou atenuação, perda e respostas parciais. Em uma operação real, investigar conectores, emendas e medições de campo.',outage:'O cenário apresentou ausência de leitura e resposta. Em uma operação real, confirmar a falha e seu alcance antes de atribuir causa.'}[session.profile];
    summary.innerHTML=`<strong>${state==='completed'?'Conclusão da simulação':'Sessão interrompida · evidência parcial'}</strong><p>${state==='completed'?result:'A inspeção não foi concluída. As amostras parciais podem ser exportadas, sem conclusão de disponibilidade.'}</p><small>${session.samples.length} amostras temporais geradas · o inventário original permanece intacto.</small>`;
  }
}
function downloadInspection() {
  if(!inspectionSession?.samples.length)return;
  const report=inspectionSession.report();
  const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'}));
  const a=document.createElement('a');a.href=url;a.download=`SIMULACAO-inspecao-${report.target_cto}-${report.state}.json`;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
  toast('Relatório fictício exportado com cenário, amostras e eventos.');
}
