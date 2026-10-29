/* CRM workspace: pipeline board, deal detail, agenda and dashboard. Deals are synthetic demo leads; edits stay in this browser. */
'use strict';
const CE=window.CrmEngine;
const CRM_KEY='urbia-isp-crm-v1';
const CRM_OWNERS=['Comercial A','Comercial B','Comercial C'];
let crmTab='dashboard',crmSeed=null,crmDeals=null,crmSeq=0,crmSelected=null,crmColumnLimit={},crmStorageOk=true,crmProviders={};
const crmToday=()=>new Date().toLocaleDateString('sv-SE',{timeZone:'America/Sao_Paulo'});
const stageName=id=>CE.STAGES.find(s=>s.id===id)?.name||id;
function crmLoad(){
  crmSeed=CE.seedDeals(db.requests,db.meta.as_of);
  let state={deals:[],seq:0};
  try{const raw=localStorage.getItem(CRM_KEY);if(raw)state=CE.validateImport({format:'urbia-isp-crm',...JSON.parse(raw)});}catch(error){crmStorageOk=false;}
  crmDeals=CE.mergeState(crmSeed,state);crmSeq=state.seq;
}
function crmSave(){
  const touched=crmDeals.filter(d=>d.id.startsWith('CRM-N')||d.history.length>1);
  try{localStorage.setItem(CRM_KEY,JSON.stringify({deals:touched,seq:crmSeq}));}catch(error){if(crmStorageOk)toast('Não foi possível salvar neste navegador. As alterações valem até recarregar.');crmStorageOk=false;}
}
function crmAct(id,action){
  const i=crmDeals.findIndex(d=>d.id===id);
  try{crmDeals[i]=CE.applyAction(crmDeals[i],action,new Date().toISOString());}catch(error){toast(error.message);return false;}
  if(action.type==='win'&&!crmDeals[i].order_id){
    const d=crmDeals[i],order=addOrder({type:'installation',priority:'medium',title:`Instalação do negócio ganho · ${d.title}`,city_id:d.city_id,lat:d.lat,lng:d.lng,ref:{kind:'deal',id:d.id}});
    crmDeals[i]=CE.applyAction(d,{type:'link_order',order_id:order},new Date().toISOString());
  }
  crmSave();renderCrm();return true;
}
function crmScoped(){
  const owner=$('crm-owner').value,type=$('crm-type').value,q=$('crm-search').value.trim().toLocaleLowerCase('pt-BR'),city=$('city').value;
  return crmDeals.filter(d=>(city==='all'||d.city_id===city)&&(owner==='all'||(owner==='none'?!d.owner:d.owner===owner))&&(type==='all'||d.type===type)&&(!q||[d.id,d.title,d.street,d.competitor?.name,d.contact?.name].join(' ').toLocaleLowerCase('pt-BR').includes(q)));
}
async function crmLoadProviders(){
  try{await loadMarket();mgmtMarket.cities.forEach(c=>crmProviders[c.id]=c.providers.map(p=>p.empresa));}catch(error){/* competitor suggestions are optional */}
}
function initCrm(){
  crmLoad();
  document.querySelectorAll('[data-crm-tab]').forEach(b=>b.onclick=()=>{crmTab=b.dataset.crmTab;renderCrm();});
  $('crm-owner').innerHTML='<option value="all">Todos os responsáveis</option><option value="none">Sem responsável</option>'+CRM_OWNERS.map(o=>`<option>${o}</option>`).join('');
  $('crm-type').innerHTML='<option value="all">Todos os tipos</option>'+Object.entries(CE.TYPES).map(([k,v])=>`<option value="${k}">${v}</option>`).join('');
  ['crm-owner','crm-type'].forEach(id=>$(id).onchange=()=>{crmColumnLimit={};renderCrm();});$('crm-search').oninput=()=>{crmColumnLimit={};renderCrm();};
  $('crm-new').onclick=()=>openCrmForm();$('crm-form').onsubmit=submitCrmForm;$('crm-form-cancel').onclick=()=>{$('crm-form').hidden=true;};
  $('crm-form-city').innerHTML=db.cities.map(c=>`<option value="${c.id}">${escapeHTML(c.name)}</option>`).join('');$('crm-form-city').onchange=refreshCrmFormCity;
  $('crm-form-owner').innerHTML='<option value="">Sem responsável</option>'+CRM_OWNERS.map(o=>`<option>${o}</option>`).join('');
  $('crm-form-type').innerHTML=Object.entries(CE.TYPES).map(([k,v])=>`<option value="${k}">${v}</option>`).join('');
  $('crm-export').onclick=exportCrmCsv;$('crm-backup').onclick=backupCrm;$('crm-import').onchange=importCrm;
  $('crm-reset').onclick=()=>{if(!confirm('Descartar todos os negócios criados e alterações do CRM salvos neste navegador?'))return;crmDeals=crmSeed.slice();crmSeq=0;crmSelected=null;crmSave();renderCrm();toast('CRM restaurado para os pedidos originais.');};
  $('crm-drawer-close').onclick=()=>{crmSelected=null;renderCrmDrawer();};
}
function openCrm(){crmLoadProviders().then(()=>{if(crmSelected)renderCrmDrawer();});renderCrm();}
function renderCrm(){
  if(!crmDeals)return;
  document.querySelectorAll('[data-crm-tab]').forEach(b=>{b.classList.toggle('active',b.dataset.crmTab===crmTab);b.setAttribute('aria-selected',b.dataset.crmTab===crmTab);});
  ['dashboard','board','list','agenda'].forEach(t=>$('crm-'+t).hidden=t!==crmTab);
  ({dashboard:renderCrmDashboard,board:renderCrmBoard,list:renderCrmList,agenda:renderCrmAgenda})[crmTab]();
  renderCrmDrawer();
  $('crm-storage-note').textContent=crmStorageOk?'Negócios, etapas, checklists e notas ficam salvos somente neste navegador. Use “Backup JSON” para guardar ou levar para outro navegador. Não há contas de usuário nem sincronização.':'Armazenamento local indisponível: as alterações valem até recarregar a página.';
}
const followBadge={overdue:['Atrasado','late'],today:['Hoje','today'],upcoming:['Agendado','ok'],missing:['Sem próxima ação','none']};
function crmCard(d,today){
  const f=CE.followUpState(d,today),c=CE.checklistStatus(d);
  return `<article class="crm-card ${d.outcome||''}" draggable="${!d.outcome}" data-deal="${escapeHTML(d.id)}" tabindex="0"><div class="crm-card-head"><span>${escapeHTML(CE.TYPES[d.type])}</span><b>${money(d.mrr)}</b></div><strong>${escapeHTML(d.title)}</strong><small>${escapeHTML(cityName(d.city_id))}${d.owner?' · '+escapeHTML(d.owner):''}${d.competitor?.name?' · usa '+escapeHTML(d.competitor.name):''}</small><div class="crm-card-foot">${d.outcome?`<span class="crm-outcome ${d.outcome}">${CE.OUTCOMES[d.outcome]}${d.lost_reason?' · '+CE.LOST_REASONS[d.lost_reason]:''}</span>`:`<span class="crm-follow ${followBadge[f][1]}">${followBadge[f][0]}${d.next_action?.date&&f!=='missing'?' · '+formatDate(d.next_action.date):''}</span>`}<span>✓ ${c.done}/${c.total}</span></div></article>`;
}
function bindCrmCards(container){
  container.querySelectorAll('[data-deal]').forEach(el=>{
    el.onclick=()=>{crmSelected=el.dataset.deal;renderCrmDrawer();};
    el.onkeydown=e=>{if(e.key==='Enter'){crmSelected=el.dataset.deal;renderCrmDrawer();}};
    el.ondragstart=e=>{e.dataTransfer.setData('text/plain',el.dataset.deal);el.classList.add('dragging');};
    el.ondragend=()=>el.classList.remove('dragging');
  });
}
function renderCrmBoard(){
  const deals=crmScoped(),today=crmToday();
  $('crm-board').innerHTML=CE.STAGES.map(s=>{
    const list=deals.filter(d=>d.stage===s.id).sort((a,b)=>s.id==='result'?String(b.closed_at).localeCompare(String(a.closed_at)):({overdue:0,today:1,upcoming:2,missing:3}[CE.followUpState(a,today)]-{overdue:0,today:1,upcoming:2,missing:3}[CE.followUpState(b,today)])||b.mrr-a.mrr);
    const limit=crmColumnLimit[s.id]||12,mrr=list.reduce((t,d)=>t+d.mrr,0);
    return `<section class="crm-column" data-stage="${s.id}" aria-label="${s.name}"><header><strong>${s.name}</strong><span>${n(list.length)}</span></header><p class="crm-column-sum">${money(mrr)}/mês${s.probability!==null?` · ${Math.round(s.probability*100)}%`:''}</p>${list.slice(0,limit).map(d=>crmCard(d,today)).join('')||'<p class="empty">Vazio</p>'}${list.length>limit?`<button class="button mgmt-more" data-crm-more="${s.id}">Mostrar mais ${n(Math.min(12,list.length-limit))}</button>`:''}</section>`;
  }).join('');
  bindCrmCards($('crm-board'));
  $('crm-board').querySelectorAll('[data-crm-more]').forEach(b=>b.onclick=()=>{crmColumnLimit[b.dataset.crmMore]=(crmColumnLimit[b.dataset.crmMore]||12)+12;renderCrmBoard();});
  $('crm-board').querySelectorAll('.crm-column').forEach(col=>{
    col.ondragover=e=>{if(col.dataset.stage!=='result'){e.preventDefault();col.classList.add('over');}};
    col.ondragleave=()=>col.classList.remove('over');
    col.ondrop=e=>{e.preventDefault();col.classList.remove('over');const id=e.dataTransfer.getData('text/plain');if(id)crmAct(id,{type:'move',stage:col.dataset.stage});};
  });
}
function renderCrmList(){
  const deals=crmScoped().sort((a,b)=>b.updated_at.localeCompare(a.updated_at)),today=crmToday();
  $('crm-list').innerHTML=`<div class="panel">${mgmtTable(['Negócio','Etapa','Valor mensal','Responsável','Próxima ação','Concorrente atual','Atualizado'],deals.slice(0,crmColumnLimit.list||25).map(d=>{const f=CE.followUpState(d,today);return `<tr><td><button data-open="${escapeHTML(d.id)}"><strong>${escapeHTML(d.title)}</strong></button><small>${escapeHTML(d.id)} · ${escapeHTML(cityName(d.city_id))} · ${escapeHTML(CE.TYPES[d.type])}</small></td><td>${d.outcome?`<span class="crm-outcome ${d.outcome}">${CE.OUTCOMES[d.outcome]}</span>`:escapeHTML(stageName(d.stage))}</td><td>${money(d.mrr)}</td><td>${escapeHTML(d.owner||'—')}</td><td>${f?`<span class="crm-follow ${followBadge[f][1]}">${followBadge[f][0]}</span><small>${d.next_action?escapeHTML(d.next_action.text||'')+' '+formatDate(d.next_action.date):''}</small>`:'—'}</td><td>${escapeHTML(d.competitor?.name||'—')}${d.competitor?.price?`<small>${money(d.competitor.price)}</small>`:''}</td><td>${new Date(d.updated_at).toLocaleDateString('pt-BR')}</td></tr>`;}),'Nenhum negócio para os filtros.')}${deals.length>(crmColumnLimit.list||25)?`<div class="mgmt-pad"><button class="button mgmt-more" id="crm-list-more">Mostrar mais</button></div>`:''}</div>`;
  $('crm-list').querySelectorAll('[data-open]').forEach(b=>b.onclick=()=>{crmSelected=b.dataset.open;renderCrmDrawer();});
  $('crm-list-more')?.addEventListener('click',()=>{crmColumnLimit.list=(crmColumnLimit.list||25)+25;renderCrmList();});
}
function renderCrmAgenda(){
  const deals=crmScoped().filter(d=>!d.outcome),today=crmToday(),group=s=>deals.filter(d=>CE.followUpState(d,today)===s).sort((a,b)=>String(a.next_action?.date).localeCompare(String(b.next_action?.date))||b.mrr-a.mrr);
  const block=(title,list,cls,limit=20)=>`<div class="panel crm-agenda-block ${cls}"><div class="panel-heading"><div><h2>${title}</h2><p>${n(list.length)} negócio(s) · ${money(list.reduce((t,d)=>t+d.mrr,0))}/mês</p></div></div><ul>${list.slice(0,limit).map(d=>`<li><button data-open="${escapeHTML(d.id)}">${escapeHTML(d.title)}</button><span>${d.next_action?`${formatDate(d.next_action.date)} · ${escapeHTML(d.next_action.text||'')}`:escapeHTML(stageName(d.stage))}</span><small>${escapeHTML(d.owner||'Sem responsável')} · ${money(d.mrr)}</small></li>`).join('')||'<li class="empty">Nada aqui.</li>'}</ul>${list.length>limit?`<p class="mini-caption mgmt-pad">e mais ${n(list.length-limit)}.</p>`:''}</div>`;
  $('crm-agenda').innerHTML=`<div class="crm-agenda">${block('Atrasados',group('overdue'),'late')}${block('Hoje',group('today'),'today')}${block('Próximos',group('upcoming'),'ok')}${block('Sem próxima ação',group('missing'),'none',12)}</div>`;
  $('crm-agenda').querySelectorAll('[data-open]').forEach(b=>b.onclick=()=>{crmSelected=b.dataset.open;renderCrmDrawer();});
}
function renderCrmDashboard(){
  const deals=crmScoped(),dash=CE.dashboard(deals,crmToday()),max=Math.max(1,...dash.by_stage.map(s=>s.count));
  $('crm-dashboard').innerHTML=`<div class="kpis">${kpi('Negócios abertos',n(dash.open),`${money(dash.pipeline_mrr)}/mês no funil`,'users')}${kpi('Previsão ponderada',money(dash.forecast_mrr),'Valor mensal × probabilidade da etapa','spark')}${kpi('Taxa de ganho',dash.win_rate===null?'—':`${n(dash.win_rate)}%`,`${n(dash.won)} ganhos · ${n(dash.lost)} perdidos · ${n(dash.discarded)} descartados`,'network')}${kpi('Follow-ups atrasados',n(dash.follow_up.overdue),`${n(dash.follow_up.today)} hoje · ${n(dash.follow_up.missing)} sem próxima ação`,'warning')}</div>
  <div class="mgmt-grid"><div class="panel"><div class="panel-heading"><div><h2>Funil por etapa</h2><p>Quantidade e valor mensal dos negócios abertos</p></div></div><div class="mgmt-pad">${dash.by_stage.map(s=>`<div class="mgmt-bar-row"><span>${s.name}</span><div class="mgmt-bar"><i style="width:${s.count/max*100}%"></i></div><b>${n(s.count)}</b></div><small class="crm-stage-mrr">${money(s.mrr)}/mês · probabilidade ${Math.round(s.probability*100)}%</small>`).join('')}</div></div>
  <div class="panel"><div class="panel-heading"><div><h2>Ganhos e perdas por concorrente</h2><p>Provedor que o cliente usava, informado no negócio</p></div></div>${mgmtTable(['Concorrente','Ganhos de','Perdidos para'],dash.competitors.map(c=>`<tr><td><strong>${escapeHTML(c.name)}</strong></td><td class="mgmt-pos">${n(c.won)}</td><td class="mgmt-neg">${n(c.lost)}</td></tr>`),'Encerre negócios informando o concorrente para ver este quadro.')}<div class="mgmt-pad"><h3 class="crm-subtitle">Motivos de perda</h3>${Object.entries(dash.lost_by_reason).sort((a,b)=>b[1]-a[1]).map(([k,v])=>`<span class="small-tag">${CE.LOST_REASONS[k]} · ${n(v)}</span>`).join(' ')||'<p class="empty">Nenhuma perda registrada.</p>'}</div></div></div>
  <p class="mgmt-footnote">Probabilidades por etapa são premissas do funil (5% a 90%), não histórico real. Os leads iniciais vêm dos pedidos fictícios; concorrentes sugeridos vêm da lista real da Anatel para a cidade.</p>`;
}
function crmCompetitorOptions(city){return (crmProviders[city]||[]).map(p=>`<option value="${escapeHTML(p)}"></option>`).join('');}
function renderCrmDrawer(){
  const d=crmDeals?.find(x=>x.id===crmSelected);$('crm-drawer').hidden=!d;if(!d)return;
  const c=CE.checklistStatus(d),today=crmToday();
  $('crm-drawer-body').innerHTML=`<span class="detail-eyebrow">${escapeHTML(d.id)} · ${escapeHTML(CE.TYPES[d.type])} · ${escapeHTML(cityName(d.city_id))}</span><h2>${escapeHTML(d.title)}</h2>
  <div class="crm-drawer-status">${d.outcome?`<span class="crm-outcome ${d.outcome}">${CE.OUTCOMES[d.outcome]}${d.lost_reason?' · '+CE.LOST_REASONS[d.lost_reason]:''}</span>`:`<label>Etapa<select id="crm-d-stage">${CE.STAGES.filter(s=>s.id!=='result').map(s=>`<option value="${s.id}" ${s.id===d.stage?'selected':''}>${s.name}</option>`).join('')}</select></label>`}<strong>${money(d.mrr)}/mês</strong></div>
  <div class="crm-drawer-actions">${d.outcome?'<button class="button" id="crm-d-reopen">Reabrir</button>':'<button class="button planning-primary" id="crm-d-win">Marcar ganho</button><button class="button" id="crm-d-lose-open">Perdido</button><button class="button" id="crm-d-discard">Descartar</button>'}<button class="button" id="crm-d-plan">Estudar viabilidade →</button>${d.source?.kind==='request'?'<button class="button" id="crm-d-map">Ver no mapa</button>':''}</div>
  ${d.order_id?`<p class="crm-linked">Ordem de instalação: <strong>${escapeHTML(d.order_id)}</strong> · em Gestão › Ordens de serviço.</p>`:''}
  ${d.triage?`<p class="mini-caption">Triagem do pedido: ${escapeHTML(labels[d.triage]||d.triage)} · CTO mais próxima ${escapeHTML(d.nearest_cto)}.</p>`:''}
  <form id="crm-d-lose" class="crm-inline" hidden><label>Motivo<select id="crm-d-reason">${Object.entries(CE.LOST_REASONS).map(([k,v])=>`<option value="${k}">${v}</option>`).join('')}</select></label><label>Concorrente<input id="crm-d-lose-comp" list="crm-providers" value="${escapeHTML(d.competitor?.name||'')}"></label><label>Observação<input id="crm-d-lose-note" maxlength="200"></label><button class="button" type="submit">Confirmar perda</button></form>
  <h3 class="crm-subtitle">Checklist · ${c.done}/${c.total}</h3><ul class="crm-checklist">${CE.CHECKLISTS[d.type].map(([id,label,req])=>`<li><label><input type="checkbox" data-check="${id}" ${d.checklist[id]?'checked':''} ${d.outcome?'disabled':''}>${escapeHTML(label)}${req?'':' <small>(opcional)</small>'}</label></li>`).join('')}</ul>${c.required_missing.length&&!d.outcome?`<p class="mini-caption">Obrigatórios para ganhar: ${c.required_missing.map(i=>escapeHTML(i.label)).join('; ')}.</p>`:''}
  <h3 class="crm-subtitle">Dados do negócio</h3>
  <form id="crm-d-form" class="crm-fields"><label>Título<input id="crm-d-title" value="${escapeHTML(d.title)}" maxlength="120"></label><label>Tipo<select id="crm-d-type">${Object.entries(CE.TYPES).map(([k,v])=>`<option value="${k}" ${k===d.type?'selected':''}>${v}</option>`).join('')}</select></label><label>Valor mensal (R$)<input id="crm-d-mrr" type="number" min="0" step="0.01" value="${d.mrr}"></label><label>Responsável<select id="crm-d-owner"><option value="">Sem responsável</option>${CRM_OWNERS.map(o=>`<option ${o===d.owner?'selected':''}>${o}</option>`).join('')}</select></label><label>Contato (fictício)<input id="crm-d-contact" value="${escapeHTML(d.contact?.name||'')}" maxlength="80" placeholder="Nome de teste"></label><label>Provedor atual do cliente<input id="crm-d-comp" list="crm-providers" value="${escapeHTML(d.competitor?.name||'')}"></label><label>Preço do concorrente (R$)<input id="crm-d-comp-price" type="number" min="0" step="0.01" value="${d.competitor?.price??''}"></label><label>Próxima ação · data<input id="crm-d-next-date" type="date" value="${d.next_action?.date||''}"></label><label class="wide">Próxima ação · o quê<input id="crm-d-next-text" value="${escapeHTML(d.next_action?.text||'')}" maxlength="120" placeholder="Ex.: ligar para confirmar proposta"></label><button class="button planning-primary" type="submit">Salvar dados</button></form>
  ${d.type==='residential'&&d.competitor?.price&&d.competitor.price<d.mrr?`<p class="crm-hint">Concorrente cobra ${money(d.competitor.price)}, ${money(d.mrr-d.competitor.price)} a menos que a proposta.</p>`:''}
  <h3 class="crm-subtitle">Histórico</h3><form id="crm-d-note" class="crm-inline"><input id="crm-d-note-text" maxlength="500" placeholder="Registrar nota, ligação ou visita"><button class="button" type="submit">Adicionar</button></form>
  <ol class="crm-history">${d.history.slice().reverse().map(h=>`<li><time>${new Date(h.at).toLocaleString('pt-BR',{timeZone:'America/Sao_Paulo',day:'2-digit',month:'2-digit',year:'2-digit',hour:'2-digit',minute:'2-digit'})}</time><span>${escapeHTML(h.action)}${h.detail?` · <small>${escapeHTML(h.detail)}</small>`:''}</span></li>`).join('')}</ol>
  <datalist id="crm-providers">${crmCompetitorOptions(d.city_id)}</datalist>`;
  const id=d.id;
  $('crm-d-stage')?.addEventListener('change',e=>crmAct(id,{type:'move',stage:e.target.value}));
  $('crm-d-win')?.addEventListener('click',()=>{if(crmAct(id,{type:'win'}))toast('Negócio ganho. Ordem de instalação criada em Gestão › Ordens de serviço.');});
  $('crm-d-lose-open')?.addEventListener('click',()=>{$('crm-d-lose').hidden=false;$('crm-d-reason').focus();});
  $('crm-d-lose')?.addEventListener('submit',e=>{e.preventDefault();crmAct(id,{type:'lose',reason:$('crm-d-reason').value,competitor:$('crm-d-lose-comp').value.trim()||undefined,note:$('crm-d-lose-note').value.trim()});});
  $('crm-d-discard')?.addEventListener('click',()=>crmAct(id,{type:'discard'}));
  $('crm-d-reopen')?.addEventListener('click',()=>crmAct(id,{type:'reopen'}));
  $('crm-d-plan').onclick=()=>openPlannerAt(d.city_id,d.lat,d.lng,`Lead ${d.id} · ${d.title}. Calcule para comparar o atendimento.`);
  $('crm-d-map')?.addEventListener('click',()=>selectEntity('request',d.source.id,true));
  $('crm-drawer-body').querySelectorAll('[data-check]').forEach(cb=>cb.onchange=()=>crmAct(id,{type:'check',item:cb.dataset.check,done:cb.checked}));
  $('crm-d-form').onsubmit=e=>{e.preventDefault();const comp=$('crm-d-comp').value.trim(),price=$('crm-d-comp-price').value,date=$('crm-d-next-date').value,text=$('crm-d-next-text').value.trim(),contact=$('crm-d-contact').value.trim();
    if(crmAct(id,{type:'update',fields:{title:$('crm-d-title').value.trim()||d.title,type:$('crm-d-type').value,mrr:Number($('crm-d-mrr').value),owner:$('crm-d-owner').value||null,contact:contact?{name:contact}:null,competitor:comp?{name:comp,price:price===''?null:Number(price)}:null,next_action:date?{date,text}:null}}))toast('Negócio atualizado.');};
  $('crm-d-note').onsubmit=e=>{e.preventDefault();if(crmAct(id,{type:'note',text:$('crm-d-note-text').value}))$('crm-d-note-text').value='';};
}
function openCrmForm(prefill={}){
  $('crm-form').hidden=false;$('crm-form').reset();
  $('crm-form-city').value=prefill.city_id||($('city').value!=='all'?$('city').value:db.cities[0].id);refreshCrmFormCity();
  if(prefill.title)$('crm-form-title').value=prefill.title;if(prefill.type)$('crm-form-type').value=prefill.type;
  if(prefill.lat!==undefined){$('crm-form-place').value='point';$('crm-form-place').dataset.lat=prefill.lat;$('crm-form-place').dataset.lng=prefill.lng;$('crm-form-place').dataset.source=JSON.stringify(prefill.source||null);}
  $('crm-form').scrollIntoView({behavior:'smooth',block:'center'});$('crm-form-title').focus();
}
function refreshCrmFormCity(){
  const city=$('crm-form-city').value;delete $('crm-form-place').dataset.lat;
  $('crm-form-place').innerHTML=db.ctos.filter(c=>c.city_id===city).map(c=>`<option value="${c.id}">Próximo à ${c.id} · ${escapeHTML(c.street)}</option>`).join('')+'<option value="point" hidden>Ponto informado</option>';
  $('crm-form-providers').innerHTML=crmCompetitorOptions(city);
}
function submitCrmForm(e){
  e.preventDefault();
  const place=$('crm-form-place'),cto=db.ctos.find(c=>c.id===place.value),point=place.value==='point'&&place.dataset.lat!==undefined;
  const comp=$('crm-form-comp').value.trim(),date=$('crm-form-next-date').value;
  try{
    const deal=CE.createDeal({title:$('crm-form-title').value,type:$('crm-form-type').value,mrr:Number($('crm-form-mrr').value),city_id:$('crm-form-city').value,lat:point?Number(place.dataset.lat):cto?.lat,lng:point?Number(place.dataset.lng):cto?.lng,street:cto?.street||'',owner:$('crm-form-owner').value||null,competitor:comp?{name:comp,price:null}:null,next_action:date?{date,text:$('crm-form-next-text').value.trim()}:null,source:point?JSON.parse(place.dataset.source||'null')||{kind:'manual',id:null}:{kind:'manual',id:cto?.id||null}},new Date().toISOString(),crmSeq+1);
    crmSeq++;crmDeals.push(deal);crmSave();$('crm-form').hidden=true;crmSelected=deal.id;renderCrm();toast(`${deal.id} criado em Novo lead.`);
  }catch(error){toast(error.message);}
}
function createLeadFromCell(r){setView('crm');openCrmForm({city_id:r.city_id,title:`Campanha · célula ${r.id.split(':').slice(1).join(':')} · ${n(r.homes)} domicílios`,type:'residential',lat:r.lat,lng:r.lng,source:{kind:'cell',id:r.id}});}
function exportCrmCsv(){
  const cols=['id','title','type','city','stage','outcome','lost_reason','mrr','owner','competitor','competitor_price','next_action_date','next_action','checklist','created_at','updated_at','order_id'];
  const rows=crmScoped().map(d=>{const c=CE.checklistStatus(d);return {...d,type:CE.TYPES[d.type],city:cityName(d.city_id),stage:stageName(d.stage),outcome:d.outcome?CE.OUTCOMES[d.outcome]:'',lost_reason:d.lost_reason?CE.LOST_REASONS[d.lost_reason]:'',competitor:d.competitor?.name||'',competitor_price:d.competitor?.price??'',next_action_date:d.next_action?.date||'',next_action:d.next_action?.text||'',checklist:`${c.done}/${c.total}`};});
  downloadCSV(`SIMULACAO-urbia-crm-${crmToday()}.csv`,cols,rows);toast(`${n(rows.length)} negócios exportados.`);
}
function backupCrm(){
  const data={format:'urbia-isp-crm',version:1,exported_at:new Date().toISOString(),seq:crmSeq,deals:crmDeals.filter(d=>d.id.startsWith('CRM-N')||d.history.length>1)};
  const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,1)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=`urbia-crm-backup-${crmToday()}.json`;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
  toast(`${n(data.deals.length)} negócios alterados ou criados no backup.`);
}
function importCrm(e){
  const file=e.target.files[0];e.target.value='';if(!file)return;
  if(file.size>5_000_000){toast('Backup acima de 5 MB não é aceito.');return;}
  file.text().then(text=>{const state=CE.validateImport(JSON.parse(text));if(!confirm(`Substituir o CRM deste navegador por ${state.deals.length} negócio(s) do backup?`))return;crmDeals=CE.mergeState(crmSeed,state);crmSeq=Math.max(state.seq,...state.deals.filter(d=>d.id.startsWith('CRM-N')).map(d=>Number(d.id.slice(5))||0),0);crmSelected=null;crmSave();renderCrm();toast('Backup importado.');}).catch(error=>toast('Backup não importado: '+error.message));
}
