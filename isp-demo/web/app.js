/* Local, read-only ISP demonstration. No live monitoring or real subscriber data. */
'use strict';
const $ = id => document.getElementById(id);
const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const n = value => Number(value).toLocaleString('pt-BR');
const money = value => Number(value).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
const formatDate = value => value ? new Date(value+'T12:00:00').toLocaleDateString('pt-BR') : '—';
const paths = {
  dashboard:'<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  network:'<rect x="8" y="3" width="8" height="6" rx="1.5"/><rect x="2" y="16" width="7" height="5" rx="1.5"/><rect x="15" y="16" width="7" height="5" rx="1.5"/><path d="M12 9v4M5.5 16v-3h13v3"/>',
  pin:'<path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/>',
  spark:'<path d="m13 2-3 8H4l7 4-1 8 4-9h6l-7-4 0-7Z"/>',
  layers:'<path d="m12 3 10 5-10 5L2 8l10-5ZM2 12l10 5 10-5M2 16l10 5 10-5"/>',
  download:'<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
  info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10v.1"/>',
  expand:'<path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5"/>',
  search:'<circle cx="10" cy="10" r="6.5"/><path d="m15 15 6 6"/>',
  users:'<circle cx="9" cy="8" r="3"/><path d="M3 21v-3a6 6 0 0 1 12 0v3M16 5a3 3 0 0 1 0 6m2 3a5 5 0 0 1 3 5v2"/>',
  cable:'<path d="M7 2v4m4-4v4M5 6h8v4a4 4 0 0 1-8 0V6Zm4 8v3a4 4 0 0 0 8 0v-3m-2-3h4v3h-4z"/>',
  arrow:'<path d="M4 12h16m-6-6 6 6-6 6"/>',
  warning:'<path d="m12 3 10 18H2L12 3Z"/><path d="M12 9v5m0 3v.1"/>',
};
const icon = name => `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">${paths[name]||paths.info}</svg>`;
document.querySelectorAll('[data-icon]').forEach(el => el.innerHTML = icon(el.dataset.icon));
const titles = {overview:['Visão geral','Seu território, conectado.','Entenda onde estão seus clientes, sua rede e as próximas oportunidades.'],network:['Rede e capacidade','Sua rede, em perspectiva.','Acompanhe POPs, caixas de atendimento, enlaces e portas disponíveis.'],clients:['Instalações','Cada conexão tem um lugar.','Explore o cadastro fictício e o vínculo entre instalação, CTO e porta.'],opportunities:['Oportunidades','O próximo passo está no mapa.','Transforme capacidade e pedidos em uma agenda de investigação.'],planning:['Planejar expansão','Qual caminho leva ao próximo cliente?','Compare atendimento pela rede atual e locais para estudar uma ampliação.'],radar:['Radar de crescimento','Encontre mudanças perto da sua rede.','Compare cenas reais e transforme sinais territoriais em uma agenda de investigação.'],inspection:['Inspeção ao vivo','Inspecione a rede, passo a passo.','Acompanhe sinal, conectividade e vínculos em uma sessão inteiramente simulada.'],sources:['Dados e premissas','Transparência em cada camada.','Saiba o que é público, o que foi simulado e o que ainda precisa ser validado.']};
const labels = {active:'Ativa',suspended:'Suspensa',cancelled:'Cancelada',operational:'Operacional',maintenance:'Manutenção',offline:'Indisponível',survey:'Validar em vistoria',capacity:'Sem porta livre',outside:'Fora da triagem',incident:'Verificar incidente'};
const badge = status => `<span class="status ${escapeHTML(status)}">${labels[status]||escapeHTML(status)}</span>`;
let db, roads, map, tiles, groups = {}, selected = null, page = 0, view = 'overview', tileErrorShown = false;
let layers = {clients:true,ctos:true,fiber:true,pops:true,requests:false,basemap:true};
const PAGE_SIZE = 8;
const cityName = id => db.cities.find(c=>c.id===id)?.name || id;
const inScope = row => ($('city').value==='all'||row.city_id===$('city').value) && ($('sector').value==='all'||row.sector===$('sector').value);
const scoped = key => db[key].filter(inScope);
const connected = client => client.status !== 'cancelled';
const ctoClients = id => db.clients.filter(c=>c.cto_id===id&&connected(c));
const free = cto => cto.capacity - ctoClients(cto.id).length;
const isOccupied = (client, at) => client.installed_at <= at && (!client.cancelled_at || client.cancelled_at > at);
function clientRows(){const query=$('search').value.trim().toLocaleLowerCase('pt-BR');return scoped('clients').filter(c=>($('status').value==='all'||c.status===$('status').value)&&(!query||[c.id,c.street,c.cto_id,cityName(c.city_id)].join(' ').toLocaleLowerCase('pt-BR').includes(query)));}
function ctoRows(){const query=$('search').value.trim().toLocaleLowerCase('pt-BR');return scoped('ctos').filter(c=>!query||[c.id,c.street,c.sector,cityName(c.city_id)].join(' ').toLocaleLowerCase('pt-BR').includes(query));}
function scopeLinks(){const ids=new Set(scoped('ctos').map(c=>c.id));return db.links.filter(l=>l.cto_ids.some(id=>ids.has(id)));}
function toast(message){$('toast').textContent=message;$('toast').classList.add('visible');clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('toast').classList.remove('visible'),3500);}
function kpi(title,value,foot,symbol){return `<article class="kpi"><div class="kpi-head"><span>${title}</span><span>${icon(symbol)}</span></div><strong>${value}</strong><div class="kpi-foot">${foot}</div></article>`;}
function renderKPIs(){
  const clients=scoped('clients'), ctos=scoped('ctos'), active=clients.filter(c=>c.status==='active').length, suspended=clients.filter(c=>c.status==='suspended').length;
  const capacity=ctos.reduce((s,c)=>s+c.capacity,0), occupiedCount=clients.filter(connected).length, available=capacity-occupiedCount, ratio=capacity?occupiedCount/capacity*100:0;
  const km=scopeLinks().reduce((s,l)=>s+l.length_m,0)/1000;
  $('kpis').innerHTML = kpi('Contratos ativos',n(active),`<em>${n(suspended)} suspensos</em> · ${n(clients.filter(c=>c.status==='cancelled').length)} cancelados`,'users') + kpi('Ocupação das CTOs',`${n(ratio.toFixed(1))}%`,`<em>${n(available)} portas livres</em> em ${n(ctos.length)} caixas`,'network') + kpi('Traçado de fibra simulado',`${n(km.toFixed(1))} <span style="font-size:15px">km</span>`,'Trechos únicos sobre vias · sem drops','cable') + kpi('Pedidos em investigação',n(scoped('requests').length),'Triagem demonstrativa · não são vendas','pin');
}
function initMap(){
  map=L.map('map',{preferCanvas:true,zoomControl:true}).setView([-22.28,-45.73],10);
  map.attributionControl.addAttribution('Vias © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors');
  tiles=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19}).addTo(map);
  tiles.on('tileerror',()=>{if(!tileErrorShown){tileErrorShown=true;toast('Mapa base indisponível. As ruas locais e a simulação continuam disponíveis.');}});
  ['roads','fiber','clients','requests','ctos','pops','selection'].forEach(name=>groups[name]=L.layerGroup().addTo(map));
  $('map-loading').hidden=true;
  drawMap(true);
}
function point(row){return [row.lat,row.lng];}
function marker(row,kind,options){
  const layer=L.circleMarker(point(row),options).bindTooltip(escapeHTML(row.id)+(kind==='cto'?` · ${ctoClients(row.id).length}/${row.capacity} portas`:` · ${kind==='client'?labels[row.status]:kind==='pop'?'POP fictício':labels[row.triage]}`));
  layer.on('click',()=>selectEntity(kind,row.id));
  return layer;
}
function drawMap(fit=false){
  if(!map)return;
  $('map-caption').textContent = $('search').value || $('status').value!=='all' ? `${n(clientRows().length)} instalações após busca/situação · indicadores mantêm o recorte territorial` : 'Clientes e infraestrutura no mesmo território';
  Object.values(groups).forEach(g=>g.clearLayers());
  const cityIds=new Set($('city').value==='all'?db.cities.map(c=>c.id):[$('city').value]);
  roads.cities.filter(c=>cityIds.has(c.id)).forEach(city=>city.roads.forEach(road=>L.polyline(road.points,{color:'#c1ccc2',weight:1.1,opacity:layers.basemap?.24:.85,interactive:false}).addTo(groups.roads)));
  if(layers.fiber)scopeLinks().forEach(link=>L.polyline(link.points,{color:'#7297ba',weight:2.3,opacity:.7,interactive:false}).addTo(groups.fiber));
  if(layers.clients)clientRows().forEach(client=>marker(client,'client',{radius:3.5,color:'#fff',weight:.7,fillColor:client.status==='active'?'#308367':client.status==='suspended'?'#c59649':'#b47b75',fillOpacity:.8}).addTo(groups.clients));
  if(layers.requests)scoped('requests').forEach(req=>marker(req,'request',{radius:5,color:'#fff',weight:1.1,fillColor:'#d49b43',fillOpacity:1}).addTo(groups.requests));
  if(layers.ctos)scoped('ctos').forEach(cto=>marker(cto,'cto',{radius:5.7,color:cto.status==='offline'?'#b45e54':free(cto)===0?'#bd8d36':'#668ab0',weight:2.2,fillColor:'#fff',fillOpacity:1}).addTo(groups.ctos));
  if(layers.pops)db.pops.filter(p=>cityIds.has(p.city_id)).forEach(pop=>marker(pop,'pop',{radius:8,color:'#fff',weight:2,fillColor:'#24424a',fillOpacity:1}).addTo(groups.pops));
  if(selected)highlightSelection();
  if(fit)fitMap();
}
function fitMap(){const ctos=scoped('ctos');if(ctos.length)map.fitBounds(L.latLngBounds(ctos.map(point)),{padding:[32,32],maxZoom:14});}
function selectEntity(kind,id,focus=false){
  const entity=({cto:db.ctos,client:db.clients,pop:db.pops,request:db.requests}[kind]||[]).find(x=>x.id===id);
  if(!entity)return;
  if(kind==='request'&&!layers.requests){layers.requests=true;document.querySelector('[data-layer="requests"]').checked=true;drawMap();}
  selected={kind,id};
  renderDetail();highlightSelection();
  if(focus){if(!['overview','clients','network'].includes(view))setView('overview');map.invalidateSize();map.setView(point(entity),16);$('map-section').scrollIntoView({behavior:'smooth',block:'start'});}
}
function highlightSelection(){
  groups.selection.clearLayers();if(!selected)return;
  const row=({cto:db.ctos,client:db.clients,pop:db.pops,request:db.requests}[selected.kind]).find(r=>r.id===selected.id);
  L.circleMarker(point(row),{radius:12,color:'#243f32',weight:2,fill:false,interactive:false}).addTo(groups.selection);
  if(selected.kind==='client'){
    const cto=db.ctos.find(c=>c.id===row.cto_id);
    L.polyline([point(row),point(cto)],{color:'#3e7557',dashArray:'4 5',weight:2,interactive:false}).addTo(groups.selection);
  }
}
function detailRow(label,value){return `<div class="detail-row"><span>${label}</span><b>${value}</b></div>`;}
function renderDetail(){
  if(!selected){
    const ctos=scoped('ctos'), clients=scoped('clients'), capacity=ctos.reduce((s,c)=>s+c.capacity,0), used=clients.filter(connected).length;
    const pct=capacity?used/capacity*100:0, city=$('city').value==='all'?'Uma operação, três cidades.':cityName($('city').value);
    $('detail').innerHTML=`<div class="detail-eyebrow">LEITURA DO TERRITÓRIO ${icon('layers')}</div><h2>${escapeHTML(city)}</h2><p class="detail-sub">${$('sector').value==='all'?'Selecione uma instalação ou CTO no mapa para explorar os vínculos.':`Setor demonstrativo ${escapeHTML($('sector').value)}. Clique em um ponto para inspecionar.`}</p><div class="detail-summary"><strong>${n(used)}</strong><span>instalações conectadas<br>ativas + suspensas</span></div><div class="detail-stats">${detailRow('Capacidade instalada',`${n(capacity)} portas`)}${detailRow('Portas ocupadas',n(used))}${detailRow('Portas livres',n(capacity-used))}</div><div class="progress"><span style="width:${pct}%"></span></div><p class="mini-caption">${n(pct.toFixed(1))}% de ocupação física. Suspensões mantêm a porta reservada.</p><div class="detail-callout"><strong>${n(ctos.filter(c=>c.status!=='operational').length)} CTOs com ocorrência simulada</strong>Contrato ativo não significa conexão funcionando. Estado comercial e estado da rede são leituras diferentes.</div><p class="detail-bottom">Retrato fictício em ${formatDate(db.meta.as_of)}. Sem consulta a equipamentos reais.</p>`;
    return;
  }
  const {kind,id}=selected;
  const row=({cto:db.ctos,client:db.clients,pop:db.pops,request:db.requests}[kind]).find(r=>r.id===id);
  let html=`<button class="back-button" id="back-detail">← Resumo do território</button><div class="detail-eyebrow">${{cto:'CAIXA DE ATENDIMENTO',client:'INSTALAÇÃO FICTÍCIA',pop:'PONTO DE PRESENÇA',request:'PEDIDO FICTÍCIO'}[kind]}</div><h2>${escapeHTML(row.id)}</h2><p class="detail-sub">${escapeHTML(cityName(row.city_id))}${row.sector?' · Setor '+escapeHTML(row.sector):''}<br>${escapeHTML(row.street||row.name)}</p>`;
  if(kind==='cto'){
    const list=ctoClients(id);html+=`<div style="margin-top:15px">${badge(row.status)}</div><div class="detail-summary"><strong>${list.length}<span style="font-size:15px"> / ${row.capacity}</span></strong><span>portas<br>ocupadas</span></div><div class="ports">${Array.from({length:row.capacity},(_,i)=>{const c=list.find(c=>c.port===i+1);return `<span class="port ${c?'used '+(c.status==='suspended'?'suspended':''):''}" title="Porta ${i+1}: ${c?escapeHTML(c.id):'livre'}">${i+1}</span>`;}).join('')}</div><p class="mini-caption">Verde: ativa · âmbar: suspensa · cinza: livre</p><div class="detail-stats">${detailRow('POP de origem',escapeHTML(row.pop_id))}${detailRow('Portas livres',free(row))}${detailRow('Ativas',list.filter(c=>c.status==='active').length)}${detailRow('Suspensas',list.filter(c=>c.status==='suspended').length)}</div><div class="detail-list">${list.slice(0,8).map(c=>`<button data-client="${c.id}">${c.id}</button>`).join('')}</div>${row.incident?`<div class="detail-callout"><strong>Ocorrência simulada</strong>${escapeHTML(row.incident)} · ${list.length} vínculos potencialmente afetados.</div>`:''}<p class="detail-bottom">Clique em uma instalação acima para consultar seu vínculo. Não há medição ao vivo.</p>`;
  }else if(kind==='client'){
    const cto=db.ctos.find(c=>c.id===row.cto_id);
    html+=`<div style="margin-top:15px">${badge(row.status)}</div><div class="detail-stats">${detailRow('Plano',`${row.speed_mbps} Mbps`)}${detailRow('Mensalidade hipotética',money(row.monthly_price))}${detailRow('Instalação',formatDate(row.installed_at))}${detailRow('Cancelamento',formatDate(row.cancelled_at))}${detailRow('CTO',escapeHTML(row.cto_id))}${detailRow('Porta',row.port)}${detailRow('Sinal simulado',row.optical_dbm===null?'Sem leitura':`${row.optical_dbm} dBm`)}${detailRow('Estado atual da CTO',labels[cto.status])}</div><button class="button" id="go-cto" data-id="${cto.id}">Inspecionar CTO ${icon('arrow')}</button><div class="detail-callout"><strong>${row.status==='cancelled'?'Porta liberada após cancelamento':'Contrato e rede são estados distintos'}</strong>${row.status==='cancelled'?'O vínculo histórico permanece no cadastro; a porta pode ter sido reutilizada.':'A situação comercial não comprova disponibilidade técnica. Sinal óptico é uma hipótese da simulação.'}</div>`;
  }else if(kind==='pop'){
    const ctos=db.ctos.filter(c=>c.pop_id===id);html+=`<div class="detail-summary"><strong>${ctos.length}</strong><span>CTOs ligadas<br>a este POP</span></div><div class="detail-stats">${detailRow('Situação',labels[row.status])}${detailRow('Capacidade das CTOs',`${n(ctos.length*16)} portas`)}${detailRow('Instalações conectadas',n(db.clients.filter(c=>c.city_id===row.city_id&&connected(c)).length))}</div><div class="detail-callout"><strong>Topologia simplificada</strong>Um POP por cidade e caminhos pelo grafo viário. Sem projeto óptico, redundância, OLT ou orçamento de potência validados.</div>`;
  }else{
    html+=`<div style="margin-top:15px">${badge(row.triage)}</div><div class="detail-stats">${detailRow('Recebido em',formatDate(row.created_at))}${detailRow('CTO mais próxima',escapeHTML(row.nearest_cto))}${detailRow('Distância em linha reta',`${n(row.distance_m)} m`)}${detailRow('Mensalidade hipotética',money(row.monthly_price))}</div><button class="button" id="go-cto" data-id="${row.nearest_cto}">Inspecionar CTO ${icon('arrow')}</button><div class="detail-callout"><strong>Apenas triagem</strong>A proximidade não garante atendimento. Investigar rota de drop, postes, capacidade óptica e condições de instalação.</div>`;
  }
  if(kind==='cto')html+='<button class="button inspection-primary" id="inspect-cto">Iniciar inspeção simulada</button>';
  $('detail').innerHTML=html;
  $('inspect-cto')?.addEventListener('click',()=>openInspection(id));
  $('back-detail').onclick=()=>{selected=null;groups.selection.clearLayers();renderDetail();};
  $('go-cto')?.addEventListener('click',event=>selectEntity('cto',event.currentTarget.dataset.id,true));
  $('detail').querySelectorAll('[data-client]').forEach(el=>el.onclick=()=>selectEntity('client',el.dataset.client,true));
}
function renderHistory(){
  const rows=scoped('clients'), months=[...new Set(db.history.map(h=>h.month))].sort();
  const history=months.map(at=>({at,entries:rows.filter(c=>c.installed_at.slice(0,7)===at.slice(0,7)&&c.installed_at<=at).length,exits:rows.filter(c=>c.cancelled_at&&c.cancelled_at.slice(0,7)===at.slice(0,7)&&c.cancelled_at<=at).length,connected:rows.filter(c=>isOccupied(c,at)).length}));
  const max=Math.max(1,...history.map(h=>Math.max(h.entries,h.exits)));
  $('history').innerHTML=`<div class="chart" aria-label="Histórico mensal de instalações e cancelamentos">${history.map(h=>{const month=new Date(h.at+'T12:00:00').toLocaleDateString('pt-BR',{month:'short'}).replace('.','');const label=`${formatDate(h.at)}: ${h.entries} instalações, ${h.exits} cancelamentos, ${h.connected} conectadas`;return `<div class="chart-month" tabindex="0" aria-label="${label}" data-tip="${label}"><div class="chart-bars"><div class="bar in" style="height:${h.entries/max*100}%"></div><div class="bar out" style="height:${h.exits/max*100}%"></div></div><span>${month}${h.at.slice(5,7)==='01'?'/26':''}</span></div>`;}).join('')}</div><div class="chart-legend"><span><i style="background:#9fc69a"></i>Instalações</span><span><i style="background:#e0b7a0"></i>Cancelamentos</span><strong>Base atual: ${n(history.at(-1).connected)}</strong></div><p class="mini-caption" style="margin-top:9px">Última competência parcial até 18/10. Base inclui suspensos; eventos usam a data de cada registro.</p>`;
}
function opportunities(){
  const ctos=scoped('ctos'), requests=scoped('requests');
  return [
    {type:'incident',icon:'warning',title:'Investigar ocorrências na rede',value:ctos.filter(c=>c.status!=='operational').length,unit:'CTOs com ocorrência fictícia',description:`${ctos.filter(c=>c.status!=='operational').reduce((s,c)=>s+ctoClients(c.id).length,0)} instalações vinculadas a caixas indisponíveis ou em manutenção. Conferir alcance e prioridade.`,action:'Inspecionar ocorrência',entity:ctos.find(c=>c.status!=='operational'),kind:'cto'},
    {type:'capacity',icon:'network',title:'Revisar caixas sem capacidade',value:ctos.filter(c=>free(c)===0).length,unit:'CTOs com as 16 portas ocupadas',description:`${requests.filter(r=>r.triage==='capacity').length} pedidos têm como CTO mais próxima uma caixa cheia. Verificar alternativas antes de dimensionar ampliação.`,action:'Localizar CTO cheia',entity:ctos.find(c=>free(c)===0),kind:'cto'},
    {type:'survey',icon:'spark',title:'Priorizar vistorias comerciais',value:requests.filter(r=>r.triage==='survey').length,unit:'pedidos próximos a CTO operacional com porta',description:'Até 350 m em linha reta. A triagem identifica pedidos para investigar; não representa venda, demanda de todo o bairro ou atendimento aprovado.',action:'Explorar pedido',entity:requests.find(r=>r.triage==='survey'),kind:'request'},
    {type:'outside',icon:'pin',title:'Estudar áreas além da rede',value:requests.filter(r=>r.triage==='outside').length,unit:'pedidos além do raio de triagem',description:'Solicitações com mais de 350 m até a CTO mais próxima. Confirmar endereços e agrupamentos antes de estimar implantação.',action:'Ver pedido distante',entity:requests.find(r=>r.triage==='outside'),kind:'request'},
  ];
}
function renderOpportunities(){
  const items=opportunities();
  $('quick-actions').innerHTML=items.slice(0,3).map((item,index)=>`<div class="quick-action"><div class="action-icon">${icon(item.icon)}</div><div><strong>${item.title}</strong><p>${n(item.value)} ${item.unit}</p></div><button data-op="${index}" aria-label="${item.action}" ${item.entity?'':'disabled'}>${icon('arrow')}</button></div>`).join('');
  $('opportunity-cards').innerHTML=items.map((item,index)=>`<article class="panel opportunity-card"><span class="detail-eyebrow">${icon(item.icon)} TRIAGEM ${index+1}</span><h3>${item.title}</h3><div class="metric">${n(item.value)}<small>${item.unit}</small></div><p>${item.description}</p><button class="button" data-op="${index}" ${item.entity?'':'disabled'}>${item.action} ${icon('arrow')}</button></article>`).join('');
  document.querySelectorAll('[data-op]').forEach(button=>button.onclick=()=>{const item=items[Number(button.dataset.op)];if(item.entity)selectEntity(item.kind,item.entity.id,true);});
  const requests=scoped('requests');$('request-count').textContent=`${requests.length} pedidos fictícios`;
  $('request-list').innerHTML=requests.map(r=>`<div class="request-row"><button data-request="${r.id}">${r.id} ↗</button><span>${escapeHTML(r.street)}<small>${escapeHTML(cityName(r.city_id))} · Setor ${r.sector}</small></span><span>${badge(r.triage)}</span><span>${n(r.distance_m)} m até CTO</span></div>`).join('')||'<div class="empty">Nenhum pedido neste recorte.</div>';
  document.querySelectorAll('[data-request]').forEach(button=>button.onclick=()=>{layers.requests=true;document.querySelector('[data-layer="requests"]').checked=true;drawMap();selectEntity('request',button.dataset.request,true);});
}
function renderTable(){
  const network=view==='network';
  $('table-title').textContent=network?'Caixas e capacidade de atendimento':'Instalações no território';
  $('table-subtitle').textContent=network?'A ocupação inclui ativas e suspensas; cancelamentos liberam a porta.':'Filtros abaixo afetam a lista, os pontos de instalações e a exportação; indicadores mantêm o recorte territorial.';
  $('status').hidden=network;
  $('search').placeholder=network?'Buscar CTO, rua ou setor':'Buscar ID, rua ou CTO';
  const rows=network?ctoRows():clientRows();
  const pages=Math.max(1,Math.ceil(rows.length/PAGE_SIZE));page=Math.min(page,pages-1);
  const slice=rows.slice(page*PAGE_SIZE,(page+1)*PAGE_SIZE);
  $('table-head').innerHTML='<tr>'+(network?['CTO / cidade','Localização','Portas ocupadas','Livres','Estado','Detalhes']:['Instalação / cidade','Rua / setor','CTO · porta','Plano','Situação','Ativação']).map(t=>`<th scope="col">${t}</th>`).join('')+'</tr>';
  $('table-body').innerHTML=slice.map(row=>network?`<tr><td><button data-cto="${row.id}"><strong>${row.id} ↗</strong></button><small>${escapeHTML(cityName(row.city_id))}</small></td><td>${escapeHTML(row.street)}<small>Setor demonstrativo ${row.sector}</small></td><td>${ctoClients(row.id).length} / ${row.capacity}<div class="progress"><span style="width:${ctoClients(row.id).length/row.capacity*100}%"></span></div></td><td>${free(row)}</td><td>${badge(row.status)}</td><td><button data-cto="${row.id}">Inspecionar →</button></td></tr>`:`<tr><td><button data-client="${row.id}"><strong>${row.id} ↗</strong></button><small>${escapeHTML(cityName(row.city_id))}</small></td><td>${escapeHTML(row.street)}<small>Setor demonstrativo ${row.sector}</small></td><td><button data-cto="${row.cto_id}">${row.cto_id}</button><small>Porta ${row.port}</small></td><td>${row.speed_mbps} Mbps<small>${money(row.monthly_price)} / mês</small></td><td>${badge(row.status)}</td><td>${formatDate(row.installed_at)}</td></tr>`).join('')||'<tr><td colspan="6" class="empty">Nenhum registro para os filtros escolhidos.</td></tr>';
  $('table-count').textContent=`${rows.length? page*PAGE_SIZE+1:0}–${Math.min((page+1)*PAGE_SIZE,rows.length)} de ${n(rows.length)} ${network?'CTOs':'instalações'} · dados fictícios`;
  $('page-count').textContent=`${page+1} / ${pages}`;$('previous').disabled=page===0;$('next').disabled=page===pages-1;
  $('table-body').querySelectorAll('[data-client]').forEach(el=>el.onclick=()=>selectEntity('client',el.dataset.client,true));
  $('table-body').querySelectorAll('[data-cto]').forEach(el=>el.onclick=()=>selectEntity('cto',el.dataset.cto,true));
}
function renderSources(){
  $('sources-section').innerHTML=`<div class="section-intro"><h2>Geografia real. Operação inteiramente fictícia.</h2><p>Esta demonstração não representa os clientes, a rede ou a participação de mercado de nenhum provedor.</p></div><div class="sources-grid">${db.meta.sources.map(source=>`<article class="panel source-card"><h3>${escapeHTML(source.name)}</h3><p>${escapeHTML(source.role)}</p><a href="${escapeHTML(source.url)}" target="_blank" rel="noopener">Consultar referência pública ↗</a></article>`).join('')}</div><div class="panel assumptions"><h2>Hipóteses e limites do cenário</h2><ul>${db.meta.assumptions.map(a=>`<li>${escapeHTML(a)}</li>`).join('')}</ul><p class="mini-caption">Coleta de ruas: ${escapeHTML(new Date(db.meta.road_retrieved_at).toLocaleString('pt-BR',{timeZone:'America/Sao_Paulo'}))}. Retrato operacional: ${formatDate(db.meta.as_of)}. Gerador determinístico com semente ${db.meta.seed}. Coordenadas fictícias junto às ruas não comprovam imóveis existentes.</p></div><div class="architecture"><strong>O que esta versão entrega</strong><br>Mapa de instalações e infraestrutura, vínculos por porta, histórico de ativações/cancelamentos, filtros, exportação CSV, triagem explicada de pedidos e sessões de inspeção com telemetria fictícia.<br><br><strong>Próxima etapa com um provedor parceiro</strong><br>Validar o inventário e o fluxo de trabalho; depois conectar cadastro e rede, com acesso por equipe, histórico de alterações e atualização controlada. Sem integração com ERP, importação de dados reais ou monitoramento nesta versão.</div>`;
}
function setView(next){
  if(view==='inspection'&&next!=='inspection'&&inspectionSession?.state==='running'){inspectionSession.pause();clearInspectionTimer();renderInspection();}
  view=next;page=0;const [label,title,subtitle]=titles[next];
  $('breadcrumb').textContent=label;$('page-title').textContent=title;$('page-subtitle').textContent=subtitle;
  document.querySelectorAll('[data-view]').forEach(el=>{el.classList.toggle('active',el.dataset.view===next);el.setAttribute('aria-current',el.dataset.view===next?'page':'false');});
  $('map-section').hidden=!['overview','network','clients'].includes(next);
  $('overview-section').hidden=next!=='overview';$('table-section').hidden=!['overview','network','clients'].includes(next);
  $('opportunities-section').hidden=next!=='opportunities';$('sources-section').hidden=next!=='sources';
  $('inspection-section').hidden=next!=='inspection';
  $('radar-section').hidden=next!=='radar';
  $('planning-section').hidden=next!=='planning';
  $('kpis').hidden=['sources','inspection','radar','planning'].includes(next);$('filters').hidden=['sources','radar','planning'].includes(next);$('export').hidden=['sources','inspection','radar','planning'].includes(next);
  if(next==='planning')openPlanning();
  if(next==='radar')openRadar();
  if(next==='inspection'){refreshInspectionTargets();renderInspection();}
  renderTable();if(map&&!$('map-section').hidden){map.invalidateSize();drawMap();}
}
function renderAll(fit=false){refreshInspectionTargets();renderKPIs();renderDetail();renderHistory();renderTable();renderOpportunities();drawMap(fit);}
function exportCSV(){
  const columns=['id','city_id','sector','street','lat','lng','cto_id','port','status','installed_at','cancelled_at','speed_mbps','monthly_price','synthetic'];
  const rows=clientRows();
  const quote=v=>'"'+String(v??'').replace(/"/g,'""')+'"';
  const csv='\ufeff'+[columns,...rows.map(r=>columns.map(c=>r[c]))].map(r=>r.map(quote).join(';')).join('\r\n');
  const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));
  const a=document.createElement('a');a.href=url;a.download=`SIMULACAO-urbia-instalacoes-${$('city').value}.csv`;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);toast(`${n(rows.length)} instalações fictícias exportadas.`);
}
async function boot(){
  try{
    const responses=await Promise.all([fetch('/api/simulation'),fetch('/api/roads')]);
    if(responses.some(r=>!r.ok))throw new Error('A API local não respondeu corretamente.');
    [db,roads]=await Promise.all(responses.map(r=>r.json()));
    if(!db.meta.synthetic)throw new Error('Esta interface aceita somente a demonstração sintética.');
    db.cities.forEach(city=>{const option=document.createElement('option');option.value=city.id;option.textContent=city.name;$('city').append(option);});
    document.querySelectorAll('[data-view]').forEach(button=>button.onclick=()=>setView(button.dataset.view));
    ['city','sector'].forEach(id=>$(id).onchange=()=>{selected=null;page=0;renderAll(true);});
    $('clear-filters').onclick=()=>{$('city').value='all';$('sector').value='all';$('search').value='';$('status').value='all';selected=null;page=0;renderAll(true);};
    $('search').oninput=()=>{page=0;renderTable();drawMap();};$('status').onchange=()=>{page=0;renderTable();drawMap();};
    $('previous').onclick=()=>{page--;renderTable();};$('next').onclick=()=>{page++;renderTable();};
    $('layers').querySelectorAll('input').forEach(input=>input.onchange=()=>{layers[input.dataset.layer]=input.checked;if(input.dataset.layer==='basemap'){if(input.checked)tiles.addTo(map);else map.removeLayer(tiles);}drawMap();});
    $('fit-map').onclick=fitMap;$('export').onclick=exportCSV;$('see-sources').onclick=()=>setView('sources');$('all-opportunities').onclick=()=>setView('opportunities');
    initMap();initInspection();initPlanning();renderSources();renderAll();
    initRadar().catch(handleRadarError);
    window.ISP_DEMO={getSummary:()=>({city:$('city').value,sector:$('sector').value,clients:clientRows().length,ctos:scoped('ctos').length,requests:scoped('requests').length,view}),selectEntity};
  }catch(error){$('fatal-error').hidden=false;$('fatal-error').textContent=`Não foi possível carregar a simulação. ${error.message} Recarregue a página ou verifique o serviço Docker.`;console.error(error);}
}
boot();
