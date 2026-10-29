/* Management workspace: revenue, census penetration, capacity forecast and work orders. Synthetic operation; edits stay in this browser. */
'use strict';
const ME=window.ManagementEngine;
const MGMT_KEY='urbia-isp-gestao-v1';
const MGMT_TEAMS=[{id:'EQ-POU-A',name:'Equipe Pouso Alegre A',city_id:'pouso-alegre'},{id:'EQ-POU-B',name:'Equipe Pouso Alegre B',city_id:'pouso-alegre'},{id:'EQ-SAN-A',name:'Equipe Santa Rita',city_id:'santa-rita'},{id:'EQ-ITA-A',name:'Equipe Itajubá',city_id:'itajuba'}];
const orderTypes={corrective:'Corretiva',preventive:'Preventiva',survey:'Vistoria',project:'Projeto de ampliação',retention:'Retenção',manual:'Manual'};
const orderStatus={open:'Aberta',scheduled:'Agendada',field:'Em campo',done:'Concluída'};
const priorityNames={critical:'Crítica',high:'Alta',medium:'Média',low:'Baixa'};
const riskNames={full:'Sem porta',critical:'Crítica',watch:'Atenção',ok:'Folga'};
const territoryActions={capacity:'Ampliar capacidade',capture:'Campanha comercial',expand:'Estudar expansão'};
let mgmtTab='revenue',mgmtState={overrides:{},created:[]},mgmtBaseOrders=null,mgmtTerritory=null,mgmtTerritoryRows=null,mgmtMap=null,mgmtMapLayers=null,mgmtRouteMap=null,mgmtRouteLayers=null,mgmtColumnLimit={},mgmtStorageOk=true;
const mgmtNow=()=>db.meta.as_of+'T18:00:00-03:00';
const teamName=id=>MGMT_TEAMS.find(t=>t.id===id)?.name||'Sem equipe';
function loadMgmtState(){try{const raw=localStorage.getItem(MGMT_KEY);if(raw){const parsed=JSON.parse(raw);mgmtState={overrides:parsed.overrides||{},created:Array.isArray(parsed.created)?parsed.created:[]};}}catch(error){mgmtStorageOk=false;}}
function saveMgmtState(){try{localStorage.setItem(MGMT_KEY,JSON.stringify(mgmtState));}catch(error){if(mgmtStorageOk)toast('Não foi possível salvar neste navegador. As alterações valem até recarregar a página.');mgmtStorageOk=false;}}
function initManagement(){
  loadMgmtState();
  mgmtBaseOrders=ME.buildWorkOrders(db,db.meta.as_of);
  document.querySelectorAll('[data-mgmt-tab]').forEach(b=>b.onclick=()=>{mgmtTab=b.dataset.mgmtTab;renderManagement();});
  ['mgmt-radius','mgmt-target','mgmt-min-homes'].forEach(id=>$(id).onchange=()=>{mgmtTerritoryRows=null;renderManagement();});
  $('mgmt-map-mode').onchange=drawMgmtTerritoryMap;
  $('mgmt-territory-export').onclick=exportMgmtTerritory;
  ['mgmt-os-type','mgmt-os-team','mgmt-os-overdue'].forEach(id=>$(id).onchange=()=>{mgmtColumnLimit={};renderOrders();});
  $('mgmt-os-team').innerHTML='<option value="all">Todas as equipes</option><option value="none">Sem equipe</option>'+MGMT_TEAMS.map(t=>`<option value="${t.id}">${escapeHTML(t.name)}</option>`).join('');
  $('mgmt-route-team').innerHTML=MGMT_TEAMS.map(t=>`<option value="${t.id}">${escapeHTML(t.name)}</option>`).join('');
  $('mgmt-route-team').onchange=renderRoute;
  $('mgmt-auto-assign').onclick=()=>{const changes=ME.autoAssign(scopedOrders(),MGMT_TEAMS);const count=Object.keys(changes).length;Object.entries(changes).forEach(([id,c])=>mgmtState.overrides[id]={...mgmtState.overrides[id],...c,updated_at:new Date().toISOString()});saveMgmtState();renderOrders();toast(count?`${n(count)} ordens de campo distribuídas e agendadas por carga de cada equipe.`:'Nenhuma ordem aberta sem equipe neste recorte.');};
  $('mgmt-os-new').onclick=()=>{$('mgmt-os-form').hidden=!$('mgmt-os-form').hidden;};
  $('mgmt-os-form').onsubmit=createManualOrder;
  $('mgmt-os-export').onclick=exportOrders;
  $('mgmt-os-reset').onclick=()=>{if(!confirm('Descartar as alterações e as ordens manuais salvas neste navegador?'))return;mgmtState={overrides:{},created:[]};saveMgmtState();renderOrders();toast('Ordens restauradas para o retrato original.');};
  $('mgmt-os-ref').innerHTML=db.ctos.map(c=>`<option value="${c.id}">${c.id} · ${escapeHTML(c.street)}</option>`).join('');
}
function openManagement(){renderManagement();}
function renderManagement(){
  document.querySelectorAll('[data-mgmt-tab]').forEach(b=>{b.classList.toggle('active',b.dataset.mgmtTab===mgmtTab);b.setAttribute('aria-selected',b.dataset.mgmtTab===mgmtTab);});
  ['revenue','territory','capacity','orders','market'].forEach(t=>$('mgmt-'+t).hidden=t!==mgmtTab);
  ({revenue:renderRevenue,territory:renderMgmtTerritory,capacity:renderCapacity,orders:renderOrders,market:renderMarket})[mgmtTab]();
}

/* Real market: Anatel fixed-broadband accesses per provider. Kept apart from the synthetic operation. */
let mgmtMarket=null,mgmtMarketPromise=null,mgmtMarketLimit=15;
const monthLabel=m=>`${m.slice(5)}/${m.slice(2,4)}`;
async function loadMarket(){
  if(!mgmtMarketPromise)mgmtMarketPromise=fetch('/api/market').then(async r=>{if(!r.ok)throw new Error('Base da Anatel indisponível.');const data=await r.json();if(data.meta.synthetic!==false)throw new Error('A base de mercado deve ter origem pública real.');mgmtMarket=data;}).catch(error=>{mgmtMarketPromise=null;throw error;});
  await mgmtMarketPromise;
}
async function renderMarket(){
  try{await loadMarket();}catch(error){$('mgmt-market-status').textContent=error.message;return;}
  const meta=mgmtMarket.meta,ids=mgmtTerritoryCities(),view=ME.marketView(mgmtMarket,ids),leader=view.providers[0],change=view.total-view.total_12m_antes;
  const pf=view.tipo_pessoa['Pessoa Física']||0,ftth=view.tecnologia.FTTH||0;
  let homes=null;try{await loadKnowledge();homes=knowledgeTerritory.cities.filter(c=>ids.includes(c.id)).reduce((s,c)=>s+c.mapped_residential_addresses,0);}catch(error){/* IBGE comparison is optional */}
  const sim=db.clients.filter(c=>ids.includes(c.city_id)&&c.status!=='cancelled').length;
  $('mgmt-market-status').textContent=`Mês de referência ${monthLabel(meta.reference_month)}, comparado com ${monthLabel(meta.comparison_month)}. Arquivo de ${formatDate(meta.source_last_modified)}, coletado em ${formatDate(meta.retrieved_at)}. A SerraLink e sua rede continuam fictícias.`;
  $('mgmt-market-kpis').innerHTML=kpi('Acessos fixos reais',n(view.total),`<em>${change>=0?'+':''}${n(change)}</em> em 12 meses · ${n((ftth/view.total*100).toFixed(1))}% FTTH`,'network')+kpi('Prestadoras ativas',n(view.providers.length),view.hhi===null?'Três mercados municipais somados':`Concentração HHI ${n(view.hhi)} · ${view.hhi>2500?'alta':view.hhi>1500?'moderada':'baixa'}`,'users')+kpi('Líder',escapeHTML(leader.empresa),`${n(leader.share_pct)}% dos acessos · ${escapeHTML(leader.porte)}`,'spark')+kpi('Acessos residenciais ÷ domicílios IBGE',homes?`${n(Math.round(pf/homes*100))}%`:'—',homes?`${n(pf)} acessos PF · ${n(homes)} domicílios mapeados (teto, não taxa exata)`:'Camada IBGE indisponível','pin');
  const absentTotal=view.absent.reduce((s,p)=>s+p.ultimos_acessos,0);
  $('mgmt-market-absent').hidden=!view.absent.length;
  $('mgmt-market-absent').innerHTML=view.absent.length?`<strong>${n(view.absent.length)} prestadora(s) sem declaração em ${monthLabel(meta.reference_month)}, que somavam ${n(absentTotal)} acessos no último mês declarado.</strong> Parte da variação do total pode ser declaração ausente ou atrasada, não perda de clientes. <ul>${view.absent.slice(0,6).map(p=>`<li>${escapeHTML(p.empresa)} · ${escapeHTML(cityName(p.city_id))} · ${n(p.ultimos_acessos)} acessos em ${monthLabel(p.ultimo_mes)}</li>`).join('')}</ul>`:'';
  const top=view.providers.slice(0,8),rest=view.providers.slice(8),restTotal=rest.reduce((s,p)=>s+p.acessos,0),max=Math.max(1,top[0]?.acessos||1,restTotal);
  $('mgmt-market-share-caption').textContent=`${monthLabel(meta.reference_month)} · ${ids.length===1?cityName(ids[0]):'três cidades somadas'} · simulação SerraLink: ${n(sim)} conexões ≈ ${n((sim/view.total*100).toFixed(1))}% do total real`;
  $('mgmt-market-share').innerHTML=top.map(p=>`<div class="mgmt-bar-row"><span title="${escapeHTML(p.empresa)} · CNPJ ${escapeHTML(p.cnpj)}">${escapeHTML(p.empresa)}</span><div class="mgmt-bar"><i style="width:${p.acessos/max*100}%" class="${p.porte==='Grande Porte'?'large':''}"></i></div><b>${n(p.share_pct)}%</b></div>`).join('')+(rest.length?`<div class="mgmt-bar-row muted"><span>Demais ${n(rest.length)} prestadoras</span><div class="mgmt-bar"><i style="width:${restTotal/max*100}%"></i></div><b>${n((restTotal/view.total*100).toFixed(1))}%</b></div>`:'')+'<div class="chart-legend"><span><i style="background:#5f9c7f"></i>Pequeno porte</span><span><i style="background:#668bba"></i>Grande porte</span></div>';
  const smax=Math.max(...view.series.map(s=>s.total)),smin=Math.min(...view.series.map(s=>s.total))*.97;
  $('mgmt-market-series').innerHTML=`<div class="mgmt-chart mgmt-chart-dense">${view.series.map(s=>{const label=`${monthLabel(s.month)}: ${n(s.total)} acessos`;return `<div class="mgmt-chart-col" tabindex="0" aria-label="${label}" data-tip="${label}"><div class="mgmt-chart-stack"><i class="mrr" style="height:${(s.total-smin)/(smax-smin||1)*92+8}%"></i></div><span>${s.month.endsWith('-01')||s.month===view.series.at(-1).month?monthLabel(s.month):''}</span></div>`;}).join('')}</div><p class="mini-caption">Eixo vertical a partir de ${n(Math.round(smin))} acessos para evidenciar a variação.</p>`;
  $('mgmt-market-mix').innerHTML=Object.entries(view.tecnologia).slice(0,5).map(([k,v])=>`<span class="small-tag">${escapeHTML(k)} ${n((v/view.total*100).toFixed(1))}%</span>`).join(' ')+` <span class="small-tag">Pessoa jurídica ${n(((view.tipo_pessoa['Pessoa Jurídica']||0)/view.total*100).toFixed(1))}%</span>`;
  renderMarketTable(view);
  $('mgmt-market-search').oninput=()=>{mgmtMarketLimit=15;renderMarketTable(view);};
  $('mgmt-market-export').onclick=()=>{downloadCSV(`ANATEL-banda-larga-fixa-${meta.reference_month}-${$('city').value}.csv`,['empresa','cnpj','grupo','porte','acessos','share_pct','acessos_12m_antes','variacao_12m','cidades'],view.providers.map(p=>({...p,cidades:p.cities.map(cityName).join(' | ')})));toast(`${n(view.providers.length)} prestadoras exportadas · fonte Anatel.`);};
  $('mgmt-market-method').innerHTML=`<p>Arquivos ${meta.files.map(escapeHTML).join(', ')} do pacote <a href="${escapeHTML(meta.url)}" target="_blank" rel="noopener noreferrer">acessos_banda_larga_fixa.zip ↗</a> (<a href="${escapeHTML(meta.panel_url)}" target="_blank" rel="noopener noreferrer">dados abertos da Anatel ↗</a>). Filtro pelo código IBGE do município; soma de todas as linhas por CNPJ e mês. SHA-256 do arquivo: <code>${escapeHTML(meta.source_sha256.slice(0,16))}…</code>. Reproduzir com <code>python3 collect_market.py --download</code>.</p><ul>${meta.limitations.map(l=>`<li>${escapeHTML(l)}</li>`).join('')}</ul><p>A razão entre acessos de pessoa física e domicílios do IBGE é um teto: o Censo é de 2022 e a camada exclui endereços com coordenada aproximada; um domicílio pode ter mais de um acesso.</p>`;
}
function renderMarketTable(view){
  const q=$('mgmt-market-search').value.trim().toLocaleLowerCase('pt-BR'),rows=view.providers.filter(p=>!q||[p.empresa,p.cnpj,p.grupo].join(' ').toLocaleLowerCase('pt-BR').includes(q));
  const spark=s=>{const max=Math.max(...s),min=Math.min(...s),w=72,h=20;return `<svg class="mgmt-spark" viewBox="0 0 ${w} ${h}" aria-hidden="true"><polyline points="${s.map((v,i)=>`${(i/(s.length-1)*w).toFixed(1)},${(h-2-(max===min?.5:(v-min)/(max-min))*(h-4)).toFixed(1)}`).join(' ')}"/></svg>`;};
  $('mgmt-market-table').innerHTML=mgmtTable(['Prestadora','Grupo · porte','Acessos','Fatia','12 meses','Últimos 13 meses'],rows.slice(0,mgmtMarketLimit).map(p=>`<tr><td><strong>${escapeHTML(p.empresa)}</strong><small>CNPJ ${escapeHTML(p.cnpj)}${view.cities.length>1?' · '+p.cities.map(cityName).map(escapeHTML).join(', '):''}</small></td><td>${escapeHTML(p.grupo)}<small>${escapeHTML(p.porte)}</small></td><td>${n(p.acessos)}</td><td>${n(p.share_pct)}%<div class="progress"><span style="width:${Math.min(100,p.share_pct)}%"></span></div></td><td class="${p.variacao_12m<0?'mgmt-neg':'mgmt-pos'}">${p.variacao_12m>=0?'+':''}${n(p.variacao_12m)}${p.acessos_12m_antes===0?'<small>sem acessos 12 meses antes neste CNPJ</small>':''}</td><td>${spark(p.series)}</td></tr>`),'Nenhuma prestadora encontrada.')+(rows.length>mgmtMarketLimit?`<div class="mgmt-pad"><button class="button mgmt-more" id="mgmt-market-more">Mostrar mais ${n(Math.min(15,rows.length-mgmtMarketLimit))} de ${n(rows.length-mgmtMarketLimit)}</button></div>`:'');
  $('mgmt-market-more')?.addEventListener('click',()=>{mgmtMarketLimit+=15;renderMarketTable(view);});
}
function mgmtTable(head,rows,empty='Nenhum registro neste recorte.'){return `<div class="table-scroll"><table><thead><tr>${head.map(h=>`<th scope="col">${h}</th>`).join('')}</tr></thead><tbody>${rows.join('')||`<tr><td colspan="${head.length}" class="empty">${empty}</td></tr>`}</tbody></table></div>`;}

/* Revenue */
function renderRevenue(){
  const clients=scoped('clients'),series=ME.revenueSeries(clients,db.meta.as_of),last=series.at(-1),closed=series.slice(0,-1).filter(s=>s.churn_pct!==null).slice(-3);
  const churn=closed.length?closed.reduce((s,x)=>s+x.churn_pct,0)/closed.length:null,arpu=last.billed?last.mrr/last.billed:0,prev=series.at(-2);
  $('mgmt-revenue-kpis').innerHTML=kpi('Receita recorrente faturável',money(last.mrr),`${n(last.billed)} contratos sem suspensão${prev?` · <em>${last.mrr>=prev.mrr?'+':''}${money(last.mrr-prev.mrr)}</em> vs. ${prev.month.slice(5)}/${prev.month.slice(2,4)}`:''}`,'spark')+kpi('Receita em risco',money(last.at_risk),`${n(last.connected-last.billed)} suspensos mantêm porta`,'warning')+kpi('Ticket médio (ARPU)',money(arpu),'Mensalidade hipotética por contrato faturável','users')+kpi('Churn mensal médio',churn===null?'—':`${n(churn.toFixed(2))}%`,'Últimas 3 competências fechadas','network');
  const max=Math.max(1,...series.map(s=>s.mrr+s.at_risk));
  $('mgmt-revenue-chart').innerHTML=`<div class="mgmt-chart">${series.map(s=>{const label=`${s.month}: ${money(s.mrr)} faturável, ${money(s.at_risk)} em risco, ${s.entries} entradas, ${s.exits} saídas${s.churn_pct===null?'':`, churn ${n(s.churn_pct)}%`}`;return `<div class="mgmt-chart-col" tabindex="0" aria-label="${label}" data-tip="${label}"><div class="mgmt-chart-stack"><i class="risk" style="height:${s.at_risk/max*100}%"></i><i class="mrr" style="height:${s.mrr/max*100}%"></i></div><span>${s.month.slice(5)}/${s.month.slice(2,4)}</span></div>`;}).join('')}</div><div class="chart-legend"><span><i style="background:#5f9c7f"></i>Faturável</span><span><i style="background:#e0b37a"></i>Em risco (suspensos)</span><strong>Outubro parcial até ${formatDate(db.meta.as_of)}</strong></div>`;
  const byCity=ME.revenueBreakdown(clients,db.meta.as_of,c=>c.city_id),byPlan=ME.revenueBreakdown(clients,db.meta.as_of,c=>c.speed_mbps),total=byCity.reduce((s,g)=>s+g.mrr,0)||1;
  const row=(label,g)=>`<tr><td><strong>${label}</strong></td><td>${n(g.contracts)}</td><td>${money(g.mrr)}<div class="progress"><span style="width:${g.mrr/total*100}%"></span></div></td><td>${money(g.at_risk)}</td><td>${g.arpu===null?'—':money(g.arpu)}</td></tr>`;
  const head=['Recorte','Contratos conectados','Receita faturável','Em risco','ARPU'];
  $('mgmt-revenue-city').innerHTML=mgmtTable(head,byCity.map(g=>row(escapeHTML(cityName(g.id)),g)));
  $('mgmt-revenue-plan').innerHTML=mgmtTable(head,byPlan.map(g=>row(`${g.id} Mbps`,g)));
  $('mgmt-revenue-months').innerHTML=mgmtTable(['Competência','Entradas','Saídas','Saldo','Base conectada','Churn'],series.slice().reverse().map(s=>`<tr><td>${s.month.slice(5)}/${s.month.slice(0,4)}${s.at===db.meta.as_of?' <small>parcial</small>':''}</td><td>${n(s.entries)}</td><td>${n(s.exits)}</td><td>${s.net>=0?'+':''}${n(s.net)}</td><td>${n(s.connected)}</td><td>${s.churn_pct===null?'—':n(s.churn_pct)+'%'}</td></tr>`));
}

/* Territory: real IBGE homes × synthetic installations × real satellite screening */
async function loadMgmtTerritory(){
  await loadKnowledge();
  if(!radarData){try{const r=await fetch('/api/radar');if(r.ok)radarData=await r.json();}catch(error){/* satellite context is optional */}}
}
function mgmtTerritoryCities(){return $('city').value==='all'?db.cities.map(c=>c.id):[$('city').value];}
function computeMgmtTerritory(){
  const options={radius:Number($('mgmt-radius').value),target:Number($('mgmt-target').value)/100,minHomes:Number($('mgmt-min-homes').value)};
  const regions=radarData?radarData.cities.flatMap(c=>c.regions):[];
  mgmtTerritoryRows=mgmtTerritoryCities().flatMap(id=>ME.territoryCells(id,{cells:knowledgeTerritory.cities.find(c=>c.id===id).cells,clients:db.clients,ctos:db.ctos,radarRegions:regions},options));
  mgmtTerritoryRows.key=$('city').value+'|'+JSON.stringify(options);
}
async function renderMgmtTerritory(){
  $('mgmt-territory-status').textContent='Carregando IBGE/Censo 2022 e radar Sentinel-2…';
  try{await loadMgmtTerritory();}catch(error){$('mgmt-territory-status').textContent='Camada IBGE indisponível. '+error.message;return;}
  const key=$('city').value+'|'+JSON.stringify({radius:Number($('mgmt-radius').value),target:Number($('mgmt-target').value)/100,minHomes:Number($('mgmt-min-homes').value)});
  if(!mgmtTerritoryRows||mgmtTerritoryRows.key!==key)computeMgmtTerritory();
  const rows=mgmtTerritoryRows,covered=rows.filter(r=>r.covered),homes=covered.reduce((s,r)=>s+r.homes,0),subs=covered.reduce((s,r)=>s+r.subscribers,0),ranked=ME.rankTerritory(rows);
  const count=a=>ranked.filter(r=>r.action===a).length,sat=ranked.filter(r=>r.satellite_regions.length).length;
  $('mgmt-territory-status').textContent=radarData?'IBGE/CNEFE 2022 real · radar Sentinel-2 2024/2025 real · rede e instalações fictícias.':'IBGE/CNEFE 2022 real · radar indisponível nesta sessão · rede e instalações fictícias.';
  $('mgmt-territory-kpis').innerHTML=kpi('Domicílios na área atendível',n(homes),`Células a até ${$('mgmt-radius').value} m de CTO operacional com porta`,'pin')+kpi('Penetração na área atendível',homes?`${n((subs/homes*100).toFixed(1))}%`:'—',`${n(subs)} instalações conectadas fictícias`,'users')+kpi('Células priorizadas',n(ranked.length),`${n(count('capture'))} campanha · ${n(count('capacity'))} capacidade · ${n(count('expand'))} expansão`,'spark')+kpi('Com sinal de satélite',n(sat),'Mudança espectral 2024→2025 a até 300 m','layers');
  drawMgmtTerritoryMap();
  $('mgmt-territory-list').innerHTML=mgmtTable(['Célula / cidade','Ação sugerida','Domicílios IBGE','Instalações','Penetração','Lacuna até a meta','CTO mais próxima','Satélite',''],ranked.slice(0,15).map(r=>`<tr><td><button data-cell="${escapeHTML(r.id)}"><strong>${escapeHTML(r.id.split(':').slice(1).join(':'))} ↗</strong></button><small>${escapeHTML(cityName(r.city_id))}</small></td><td><span class="mgmt-action ${r.action}">${territoryActions[r.action]}</span></td><td>${n(r.homes)}</td><td>${n(r.subscribers)}</td><td>${n(r.penetration)}%</td><td>${n(r.gap)}</td><td>${escapeHTML(r.nearest_cto)}<small>${n(r.nearest_cto_m)} m em linha reta · ${n(r.free_ports_in_radius)} portas no raio</small></td><td>${r.satellite_regions.length?`${n(r.satellite_changed_ha)} ha sinalizados`:'—'}</td><td><button data-cell-plan="${escapeHTML(r.id)}">Planejar →</button>${r.action!=='capacity'?`<button data-cell-os="${escapeHTML(r.id)}">Criar vistoria</button>`:''}</td></tr>`),'Nenhuma célula atende aos critérios escolhidos.')+`<p class="mini-caption mgmt-pad">${n(ranked.length)} células no total; exibidas as 15 primeiras. Ordem: capacidade esgotada, campanha, expansão; dentro de cada ação, células com sinal de satélite e maior lacuna até a meta. A lacuna é domicílios × meta − instalações, não previsão de vendas.</p>`;
  const find=id=>rows.find(r=>r.id===id);
  $('mgmt-territory-list').querySelectorAll('[data-cell]').forEach(b=>b.onclick=()=>{const r=find(b.dataset.cell);mgmtMap.setView([r.lat,r.lng],16);$('mgmt-map').scrollIntoView({behavior:'smooth',block:'center'});});
  $('mgmt-territory-list').querySelectorAll('[data-cell-plan]').forEach(b=>b.onclick=()=>{const r=find(b.dataset.cellPlan);openPlannerAt(r.city_id,r.lat,r.lng,`Centro da célula IBGE ${r.id}. Marque um imóvel ou calcule a partir deste ponto.`);});
  $('mgmt-territory-list').querySelectorAll('[data-cell-os]').forEach(b=>b.onclick=()=>{const r=find(b.dataset.cellOs);addOrder({type:'survey',priority:'medium',title:`${territoryActions[r.action]} · célula ${r.id.split(':').slice(1).join(':')} · ${n(r.homes)} domicílios`,city_id:r.city_id,lat:r.lat,lng:r.lng,ref:{kind:'cell',id:r.id}});b.disabled=true;});
}
function drawMgmtTerritoryMap(){
  if(!mgmtTerritoryRows)return;
  if(!mgmtMap){mgmtMap=L.map('mgmt-map',{preferCanvas:true});L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap contributors'}).addTo(mgmtMap);mgmtMapLayers={cells:L.layerGroup().addTo(mgmtMap),net:L.layerGroup().addTo(mgmtMap)};}
  mgmtMap.invalidateSize();mgmtMapLayers.cells.clearLayers();mgmtMapLayers.net.clearLayers();
  const mode=$('mgmt-map-mode').value,actionColor={capacity:'#c0804a',capture:'#3f9a72',expand:'#6c86b8'};
  mgmtTerritoryRows.forEach(r=>{
    let color,opacity;
    if(mode==='action'){if(!r.action)return;color=actionColor[r.action];opacity=.55;}
    else{if(!r.homes)return;const p=r.penetration;color=p===0?'#e6ece9':p<5?'#c9e4d4':p<15?'#8cc4a6':p<30?'#4f9c78':'#226a4f';opacity=.6;}
    L.rectangle(r.bounds,{color:r.satellite_regions.length?'#c9a634':color,weight:r.satellite_regions.length?1.6:.4,fillColor:color,fillOpacity:opacity}).bindTooltip(`${n(r.homes)} domicílios IBGE · ${n(r.subscribers)} instalações · ${r.penetration===null?'—':n(r.penetration)+'%'}${r.action?' · '+territoryActions[r.action]:''}${r.satellite_regions.length?' · sinal de satélite':''}`).addTo(mgmtMapLayers.cells);
  });
  const cities=new Set(mgmtTerritoryCities());
  db.ctos.filter(c=>cities.has(c.city_id)).forEach(c=>L.circleMarker([c.lat,c.lng],{radius:4,color:c.status!=='operational'?'#b45e54':free(c)===0?'#bd8d36':'#466e96',weight:2,fillColor:'#fff',fillOpacity:1}).bindTooltip(`${escapeHTML(c.id)} · ${free(c)} portas livres`).addTo(mgmtMapLayers.net));
  const pts=db.ctos.filter(c=>cities.has(c.city_id)).map(c=>[c.lat,c.lng]);
  if(pts.length&&mgmtMapLayers.fitKey!==[...cities].join()){mgmtMap.fitBounds(L.latLngBounds(pts),{padding:[40,40],maxZoom:14});mgmtMapLayers.fitKey=[...cities].join();}
  $('mgmt-map-legend').innerHTML=mode==='action'?'<span><i style="background:#c0804a"></i>Ampliar capacidade</span><span><i style="background:#3f9a72"></i>Campanha comercial</span><span><i style="background:#6c86b8"></i>Estudar expansão</span><span><i class="outline"></i>Sinal de satélite</span>':'<span><i style="background:#e6ece9"></i>0%</span><span><i style="background:#c9e4d4"></i>&lt;5%</span><span><i style="background:#8cc4a6"></i>5–15%</span><span><i style="background:#4f9c78"></i>15–30%</span><span><i style="background:#226a4f"></i>≥30%</span><span><i class="outline"></i>Sinal de satélite</span>';
}
function exportMgmtTerritory(){
  if(!mgmtTerritoryRows)return;
  const ranked=ME.rankTerritory(mgmtTerritoryRows),cols=['id','city_id','action','homes','addresses','subscribers','penetration','gap','nearest_cto','nearest_cto_m','free_ports_in_radius','satellite_changed_ha','lat','lng'];
  downloadCSV(`URBIA-gestao-territorio-${$('city').value}.csv`,cols,ranked.map(r=>({...r,action:territoryActions[r.action]})));
  toast(`${n(ranked.length)} células exportadas. Domicílios: IBGE 2022 real; instalações: simulação.`);
}

/* Capacity forecast */
function renderCapacity(){
  const rows=ME.capacityForecast(scoped('ctos'),db.clients,db.requests,db.meta.as_of),count=r=>rows.filter(x=>x.risk===r).length;
  $('mgmt-capacity-kpis').innerHTML=kpi('CTOs sem porta livre',n(count('full')),'Ocupação de 16/16 portas','network')+kpi('Esgotam em até 2 meses',n(count('critical')),'Ritmo recente ou pedidos ≥ portas livres','warning')+kpi('Atenção · até 6 meses',n(count('watch')),'Tendência linear dos últimos 90 dias','spark')+kpi('Pedidos aguardando porta',n(rows.reduce((s,r)=>s+r.pending_requests,0)),'Vistoria ou sem capacidade na CTO mais próxima','pin');
  $('mgmt-capacity-table').innerHTML=mgmtTable(['CTO / cidade','Portas','Saldo 90 dias','Ritmo / mês','Esgota em','Pedidos','Risco',''],rows.map(r=>`<tr><td><button data-cap-cto="${r.id}"><strong>${r.id} ↗</strong></button><small>${escapeHTML(cityName(r.city_id))} · ${escapeHTML(r.street)}</small></td><td>${r.used} / ${r.capacity}<div class="progress"><span style="width:${r.used/r.capacity*100}%"></span></div></td><td>${r.net_window>=0?'+':''}${r.net_window}</td><td>${n(r.net_per_month)}</td><td>${r.months_to_full===0?'Esgotada':r.months_to_full===null?'Sem tendência':`${n(r.months_to_full)} meses`}</td><td>${r.pending_requests}</td><td><span class="mgmt-risk ${r.risk}">${riskNames[r.risk]}</span>${r.status!=='operational'?`<small>${labels[r.status]}</small>`:''}</td><td>${r.risk!=='ok'?`<button data-cap-plan="${r.id}">Planejar ampliação →</button>`:''}</td></tr>`));
  $('mgmt-capacity-table').querySelectorAll('[data-cap-cto]').forEach(b=>b.onclick=()=>selectEntity('cto',b.dataset.capCto,true));
  $('mgmt-capacity-table').querySelectorAll('[data-cap-plan]').forEach(b=>b.onclick=()=>{const c=db.ctos.find(x=>x.id===b.dataset.capPlan);openPlannerAt(c.city_id,c.lat,c.lng,`Ponto na ${c.id}. Use “Aproveitar outros pedidos próximos” para comparar uma nova CTO.`);});
}
function openPlannerAt(city,lat,lng,message){
  setView('planning');
  if($('plan-city').value!==city){$('plan-city').value=city;refreshPlanningCity();}
  $('plan-request').value='manual';$('plan-lat').value=Number(lat).toFixed(7);$('plan-lng').value=Number(lng).toFixed(7);
  invalidatePlanning(message);drawPlanningTarget();planningMap?.setView([lat,lng],16);
  $('plan-form').scrollIntoView({behavior:'smooth',block:'start'});
}

/* Work orders */
function allOrders(){return ME.applyOverrides(mgmtBaseOrders,mgmtState);}
function scopedOrders(){const cities=new Set(mgmtTerritoryCities());return allOrders().filter(o=>cities.has(o.city_id));}
function addOrder(o){
  const id=`OS-MAN-${String(mgmtState.created.length+1).padStart(4,'0')}-${Date.now().toString(36).slice(-4).toUpperCase()}`;
  const created_at=mgmtNow();
  mgmtState.created.push({id,status:'open',team:null,affected:0,ref:null,...o,type:o.type||'manual',created_at,due_at:new Date(new Date(created_at).getTime()+ME.SLA_HOURS[o.priority]*3600000).toISOString(),manual:true});
  saveMgmtState();toast(`${id} criada. Consulte em Gestão › Ordens de serviço.`);
  if(mgmtTab==='orders')renderOrders();
}
function createManualOrder(event){
  event.preventDefault();
  const cto=db.ctos.find(c=>c.id===$('mgmt-os-ref').value),title=$('mgmt-os-title').value.trim();
  if(!title){$('mgmt-os-title').focus();return;}
  addOrder({type:$('mgmt-os-kind').value,priority:$('mgmt-os-priority').value,title,city_id:cto.city_id,lat:cto.lat,lng:cto.lng,ref:{kind:'cto',id:cto.id}});
  $('mgmt-os-form').reset();$('mgmt-os-form').hidden=true;
}
function updateOrder(id,change){mgmtState.overrides[id]={...mgmtState.overrides[id],...change,updated_at:new Date().toISOString()};saveMgmtState();renderOrders();}
function filteredOrders(){
  const type=$('mgmt-os-type').value,team=$('mgmt-os-team').value,overdue=$('mgmt-os-overdue').checked,now=mgmtNow();
  return scopedOrders().filter(o=>(type==='all'||o.type===type)&&(team==='all'||(team==='none'?!o.team:o.team===team))&&(!overdue||ME.isOverdue(o,now)));
}
function orderCard(o,now){
  const late=ME.isOverdue(o,now),due=new Date(o.due_at).toLocaleString('pt-BR',{timeZone:'America/Sao_Paulo',day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'});
  const teams=MGMT_TEAMS.filter(t=>t.city_id===o.city_id);
  return `<article class="mgmt-card ${o.priority}${late?' late':''}"><div class="mgmt-card-head"><span class="mgmt-priority ${o.priority}">${priorityNames[o.priority]}</span><span>${orderTypes[o.type]||o.type}</span></div><strong>${escapeHTML(o.title)}</strong><small>${escapeHTML(o.id)} · ${escapeHTML(cityName(o.city_id))}${o.affected?` · ${o.affected} vínculo(s)`:''}</small><small class="${late?'mgmt-late':''}">${late?'Atrasada · ':''}SLA ${due}</small><div class="mgmt-card-controls"><select data-os-status="${escapeHTML(o.id)}" aria-label="Situação da ordem ${escapeHTML(o.id)}">${Object.entries(orderStatus).map(([k,v])=>`<option value="${k}" ${o.status===k?'selected':''}>${v}</option>`).join('')}</select>${o.field===false?'<span class="mgmt-office">Escritório</span>':`<select data-os-team="${escapeHTML(o.id)}" aria-label="Equipe da ordem ${escapeHTML(o.id)}"><option value="">Sem equipe</option>${teams.map(t=>`<option value="${t.id}" ${o.team===t.id?'selected':''}>${escapeHTML(t.name)}</option>`).join('')}</select>`}</div>${o.ref&&['cto','client','request'].includes(o.ref.kind)?`<button class="text-button" data-os-ref="${o.ref.kind}:${escapeHTML(o.ref.id)}">Ver ${escapeHTML(o.ref.id)} no mapa ↗</button>`:''}</article>`;
}
function renderOrders(){
  const now=mgmtNow(),scope=scopedOrders(),open=scope.filter(o=>o.status!=='done'),rows=filteredOrders();
  $('mgmt-orders-kpis').innerHTML=kpi('Ordens abertas',n(open.length),`${n(open.filter(o=>!o.team&&o.field!==false).length)} de campo sem equipe`,'pin')+kpi('Atrasadas no SLA',n(open.filter(o=>ME.isOverdue(o,now)).length),'Relógio do retrato: 18/10/2026 18h','warning')+kpi('Críticas e altas',n(open.filter(o=>['critical','high'].includes(o.priority)).length),`${n(open.filter(o=>o.type==='corrective').reduce((s,o)=>s+o.affected,0))} vínculos afetados por corretivas`,'network')+kpi('Em campo agora',n(open.filter(o=>o.status==='field').length),`${n(scope.filter(o=>o.status==='done').length)} concluídas neste navegador`,'users');
  $('mgmt-kanban').innerHTML=Object.entries(orderStatus).map(([status,label])=>{const list=rows.filter(o=>o.status===status),limit=mgmtColumnLimit[status]||12;return `<section class="mgmt-column" aria-label="${label}"><header><strong>${label}</strong><span>${n(list.length)}</span></header>${list.slice(0,limit).map(o=>orderCard(o,now)).join('')||'<p class="empty">Nenhuma ordem.</p>'}${list.length>limit?`<button class="button mgmt-more" data-more="${status}">Mostrar mais ${n(Math.min(12,list.length-limit))}</button>`:''}</section>`;}).join('');
  $('mgmt-kanban').querySelectorAll('[data-os-status]').forEach(s=>s.onchange=()=>updateOrder(s.dataset.osStatus,{status:s.value}));
  $('mgmt-kanban').querySelectorAll('[data-os-team]').forEach(s=>s.onchange=()=>{const o=allOrders().find(x=>x.id===s.dataset.osTeam);updateOrder(o.id,{team:s.value||null,status:s.value&&o.status==='open'?'scheduled':o.status});});
  $('mgmt-kanban').querySelectorAll('[data-more]').forEach(b=>b.onclick=()=>{mgmtColumnLimit[b.dataset.more]=(mgmtColumnLimit[b.dataset.more]||12)+12;renderOrders();});
  $('mgmt-kanban').querySelectorAll('[data-os-ref]').forEach(b=>b.onclick=()=>{const [kind,id]=b.dataset.osRef.split(':');selectEntity(kind,id,true);});
  $('mgmt-storage-note').textContent=mgmtStorageOk?'Situação, equipe e ordens manuais ficam salvas somente neste navegador. Não há sincronização entre usuários ou com ERP.':'Armazenamento local indisponível: as alterações valem até recarregar a página.';
  const cities=new Set(mgmtTerritoryCities());
  if(!cities.has(MGMT_TEAMS.find(t=>t.id===$('mgmt-route-team').value).city_id))$('mgmt-route-team').value=MGMT_TEAMS.find(t=>cities.has(t.city_id)).id;
  renderRoute();
}
function renderRoute(){
  const team=MGMT_TEAMS.find(t=>t.id===$('mgmt-route-team').value),pop=db.pops.find(p=>p.city_id===team.city_id);
  const route=ME.dayRoute(pop,allOrders().filter(o=>o.team===team.id));
  if(!mgmtRouteMap){mgmtRouteMap=L.map('mgmt-route-map',{preferCanvas:true});L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap contributors'}).addTo(mgmtRouteMap);mgmtRouteLayers=L.layerGroup().addTo(mgmtRouteMap);}
  mgmtRouteMap.invalidateSize();mgmtRouteLayers.clearLayers();
  const pts=[[pop.lat,pop.lng],...route.stops.map(s=>[s.lat,s.lng])];
  if(route.stops.length)L.polyline(pts,{color:'#2d5545',weight:2.4,dashArray:'6 6',interactive:false}).addTo(mgmtRouteLayers);
  L.circleMarker([pop.lat,pop.lng],{radius:8,color:'#fff',weight:2,fillColor:'#24424a',fillOpacity:1}).bindTooltip('Base: '+escapeHTML(pop.name)).addTo(mgmtRouteLayers);
  route.stops.forEach((s,i)=>L.marker([s.lat,s.lng],{icon:L.divIcon({className:'mgmt-stop '+s.priority,html:String(i+1),iconSize:[22,22]})}).bindTooltip(`${i+1}. ${escapeHTML(s.title)}`).addTo(mgmtRouteLayers));
  if(route.stops.length)mgmtRouteMap.fitBounds(L.latLngBounds(pts),{padding:[30,30],maxZoom:16});else mgmtRouteMap.setView([pop.lat,pop.lng],13);
  $('mgmt-route-list').innerHTML=route.stops.length?`<p class="mgmt-route-total"><strong>${route.stops.length} paradas</strong> · ${n(route.straight_km)} km em linha reta a partir do POP</p><ol>${route.stops.map(s=>`<li><span class="mgmt-priority ${s.priority}">${priorityNames[s.priority]}</span> ${escapeHTML(s.title)}<small>${escapeHTML(s.id)} · +${n(s.leg_m)} m</small></li>`).join('')}</ol>`:'<p class="empty">Nenhuma ordem de campo atribuída a esta equipe. Use “Distribuir automaticamente” ou escolha a equipe em um cartão.</p>';
}
function exportOrders(){
  const cols=['id','type','priority','status','team','city_id','title','created_at','due_at','overdue','ref_kind','ref_id','lat','lng','manual'],now=mgmtNow();
  const rows=filteredOrders().map(o=>({...o,type:orderTypes[o.type]||o.type,priority:priorityNames[o.priority],status:orderStatus[o.status],team:o.team?teamName(o.team):'',overdue:ME.isOverdue(o,now)?'sim':'não',ref_kind:o.ref?.kind||'',ref_id:o.ref?.id||'',manual:o.manual?'sim':'não'}));
  downloadCSV(`SIMULACAO-urbia-ordens-${$('city').value}.csv`,cols,rows);toast(`${n(rows.length)} ordens fictícias exportadas.`);
}
function downloadCSV(name,columns,rows){
  const quote=v=>'"'+String(v??'').replace(/"/g,'""')+'"';
  const csv='﻿'+[columns,...rows.map(r=>columns.map(c=>r[c]))].map(r=>r.map(quote).join(';')).join('\r\n');
  const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
