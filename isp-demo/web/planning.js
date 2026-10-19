/* Street-path planning over public OSM geometry and a fictional ISP inventory. */
'use strict';
let planningMap=null, planningLayers=null, planningData=null, planningSelection=0, planningGeneration=0, planningAbort=null;
const planningCoordinates=()=>({lat:Number($('plan-lat').value),lng:Number($('plan-lng').value)});
function initPlanning(){
  $('plan-city').innerHTML=db.cities.map(c=>`<option value="${escapeHTML(c.id)}">${escapeHTML(c.name)}</option>`).join('');
  $('plan-city').onchange=()=>{refreshPlanningCity();invalidatePlanning('Cidade alterada. Marque o pedido e calcule novamente.');};
  $('plan-request').onchange=()=>{
    const request=db.requests.find(r=>r.id===$('plan-request').value);
    if(request){$('plan-lat').value=request.lat;$('plan-lng').value=request.lng;}
    invalidatePlanning('Pedido alterado; calcule as alternativas.');
    drawPlanningTarget();
    if(planningMap)planningMap.setView([Number($('plan-lat').value),Number($('plan-lng').value)],16);
  };
  ['plan-lat','plan-lng','plan-max-drop','plan-slack','plan-drop-cost','plan-fiber-cost','plan-cto-cost','plan-priority'].forEach(id=>$(id).oninput=()=>{
    if(['plan-lat','plan-lng'].includes(id)){$('plan-request').value='manual';drawPlanningTarget();}
    invalidatePlanning('Premissas alteradas. Recalcule para comparar as rotas.');
  });
  $('plan-form').onsubmit=event=>{event.preventDefault();calculatePlanning();};
  $('plan-find-street').onclick=findPlanningStreet;
  $('plan-export').onclick=exportPlanning;
  $('plan-show-route').onclick=()=>$('planning-map').scrollIntoView({behavior:'smooth',block:'center'});
  refreshPlanningCity();
}
function refreshPlanningCity(){
  const city=$('plan-city').value;
  const requests=db.requests.filter(r=>r.city_id===city);
  $('plan-request').innerHTML='<option value="manual">Ponto marcado no mapa / coordenadas</option>'+requests.map(r=>`<option value="${r.id}">${r.id} · ${escapeHTML(r.street)}</option>`).join('');
  if(requests.length){$('plan-request').value=requests[0].id;$('plan-lat').value=requests[0].lat;$('plan-lng').value=requests[0].lng;}
  else{const center=db.cities.find(c=>c.id===city).center;$('plan-lat').value=center[0];$('plan-lng').value=center[1];}
  $('plan-street').value='';
  const streetNames=[...new Set(roads.cities.find(c=>c.id===city).roads.map(r=>r.name))].filter(name=>name!=='Via sem nome no OSM').sort((a,b)=>a.localeCompare(b,'pt-BR'));
  $('plan-streets').innerHTML=streetNames.map(name=>`<option value="${escapeHTML(name)}"></option>`).join('');
  if(planningMap){drawPlanningBase();drawPlanningTarget();fitPlanningCity();}
}
function openPlanning(){
  if(!planningMap){
    if($('city').value!=='all'){$('plan-city').value=$('city').value;refreshPlanningCity();}
    planningMap=L.map('planning-map',{preferCanvas:true}).setView(db.cities.find(c=>c.id===$('plan-city').value).center,14);
    planningMap.attributionControl.addAttribution('Vias © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors');
    const tiles=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19}).addTo(planningMap);
    let errorShown=false;tiles.on('tileerror',()=>{if(!errorShown){toast('Mapa base indisponível. Vias e rotas locais continuam disponíveis.');errorShown=true;}});
    planningLayers={base:L.layerGroup().addTo(planningMap),route:L.layerGroup().addTo(planningMap),target:L.layerGroup().addTo(planningMap)};
    planningMap.on('click',event=>{
      $('plan-request').value='manual';$('plan-lat').value=event.latlng.lat.toFixed(7);$('plan-lng').value=event.latlng.lng.toFixed(7);
      invalidatePlanning('Ponto marcado. Calcule para encontrar as alternativas.');drawPlanningTarget();
    });
    drawPlanningBase();drawPlanningTarget();fitPlanningCity();
  }
  planningMap.invalidateSize();
  if(planningData?.proposals.length)drawPlanningRoute(planningData.proposals[planningSelection]);
}
function invalidatePlanning(message){
  planningGeneration++;
  planningAbort?.abort();planningAbort=null;planningData=null;
  $('plan-calculate').disabled=false;$('plan-calculate').textContent='Comparar rotas e ampliação';
  $('plan-status').textContent=message;$('plan-export').disabled=true;
  $('plan-results').hidden=true;$('plan-error').hidden=true;
  planningLayers?.route.clearLayers();
}
function drawPlanningBase(){
  if(!planningMap)return;
  planningLayers.base.clearLayers();
  const city=$('plan-city').value;
  roads.cities.find(c=>c.id===city).roads.forEach(road=>L.polyline(road.points,{color:'#b5c5b8',weight:1,opacity:.55,interactive:false}).addTo(planningLayers.base));
  db.links.filter(l=>l.city_id===city).forEach(link=>L.polyline(link.points,{color:'#628bb3',weight:2.2,opacity:.65,interactive:false}).addTo(planningLayers.base));
  db.ctos.filter(c=>c.city_id===city).forEach(cto=>{
    const color=cto.status!=='operational'?'#bd7860':free(cto)===0?'#b99b53':'#678ab4';
    L.circleMarker([cto.lat,cto.lng],{radius:5,color,weight:2,fillColor:'white',fillOpacity:1}).bindTooltip(`${escapeHTML(cto.id)} · ${free(cto)} portas livres · ${labels[cto.status]}`).addTo(planningLayers.base);
  });
  db.requests.filter(r=>r.city_id===city).forEach(r=>L.circleMarker([r.lat,r.lng],{radius:3,color:'#fff',weight:.5,fillColor:'#ba9f61',fillOpacity:.8}).bindTooltip(escapeHTML(r.id)+' · pedido fictício').addTo(planningLayers.base));
}
function drawPlanningTarget(){
  if(!planningMap)return;
  planningLayers.target.clearLayers();const p=planningCoordinates();
  if(Number.isFinite(p.lat)&&Number.isFinite(p.lng)&&Math.abs(p.lat)<=90&&Math.abs(p.lng)<=180){
    L.circleMarker([p.lat,p.lng],{radius:8,color:'white',weight:2,fillColor:'#bd6555',fillOpacity:1}).bindTooltip('Pedido em estudo · posição informada').addTo(planningLayers.target);
  }
}
function fitPlanningCity(){
  const ctos=db.ctos.filter(c=>c.city_id===$('plan-city').value);
  if(ctos.length)planningMap.fitBounds(L.latLngBounds(ctos.map(c=>[c.lat,c.lng])),{padding:[35,35],maxZoom:14});
}
function findPlanningStreet(){
  const query=$('plan-street').value.trim().toLocaleLowerCase('pt-BR');
  if(!query){toast('Digite ou escolha o nome de uma rua.');return;}
  const city=roads.cities.find(c=>c.id===$('plan-city').value);
  const matches=city.roads.filter(r=>r.name.toLocaleLowerCase('pt-BR')===query);
  if(!matches.length){toast('Selecione um nome completo da lista de ruas armazenadas.');return;}
  planningMap.fitBounds(L.latLngBounds(matches.flatMap(r=>r.points)),{padding:[50,50],maxZoom:17});
  toast('Rua localizada. Clique na posição aproximada do cliente; nenhum número de imóvel foi geocodificado.');
}
async function calculatePlanning(){
  if(!$('plan-form').reportValidity())return;
  invalidatePlanning('Calculando caminhos no grafo de ruas…');
  const version=planningGeneration;
  planningAbort=new AbortController();
  $('plan-calculate').disabled=true;$('plan-calculate').textContent='Calculando alternativas…';
  const p=planningCoordinates();
  const payload={city_id:$('plan-city').value,...p,request_id:$('plan-request').value==='manual'?null:$('plan-request').value,max_drop_m:$('plan-max-drop').value,slack_pct:$('plan-slack').value,priority:$('plan-priority').value,drop_per_m:$('plan-drop-cost').value,fiber_per_m:$('plan-fiber-cost').value,new_cto_cost:$('plan-cto-cost').value};
  try{
    const response=await fetch('/api/plan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),signal:planningAbort.signal});
    const result=await response.json();
    if(version!==planningGeneration)return;
    if(!response.ok)throw new Error(result.error||'Não foi possível calcular as rotas.');
    planningData=result;planningSelection=0;$('plan-results').hidden=false;$('plan-export').disabled=false;
    $('plan-status').textContent=result.status==='study'?'Alternativas calculadas · validação técnica pendente.':'Sem rota conectada no cadastro disponível.';
    renderPlanningResults();
  }catch(error){
    if(error.name==='AbortError'||version!==planningGeneration)return;
    $('plan-error').hidden=false;$('plan-error').textContent=error.message;$('plan-status').textContent='Cálculo não concluído; reveja os dados.';
  }finally{
    if(version===planningGeneration){$('plan-calculate').disabled=false;$('plan-calculate').textContent='Comparar rotas e ampliação';planningAbort=null;}
  }
}
function renderPlanningResults(){
  const result=planningData;if(!result)return;
  const options=result.proposals;
  $('plan-summary').innerHTML=`<div class="planning-evidence-label">PRIMEIRA ALTERNATIVA PARA ESTUDAR</div><h2>${escapeHTML(result.recommendation)}</h2><p>Pedido em ${escapeHTML(result.target.street)}. Acesso até a rua: ${n(result.target.access_gap_m)} m, indicativo e ainda não validado. Ordenação: ${result.parameters.priority==='current'?'atender o pedido atual, priorizando CTO existente':'agrupar outros pedidos, limitado pelas portas'}; comparação por ${result.metadata.ranking_metric==='declared_cost'?'custos informados':'metragem de cabo com reserva (custos completos não informados)'}.</p>`;
  $('plan-nearest').innerHTML=result.nearest_ctos.length?result.nearest_ctos.map(c=>`<tr><td>${escapeHTML(c.id)}</td><td>${n(c.cable_distance_m)} m</td><td>${c.free_ports}</td><td>${badge(c.status)}</td><td>${c.status!=='operational'?'Verificar ocorrência':c.free_ports===0?'Sem porta livre':c.cable_distance_m>result.parameters.max_drop_m?'Além do limite adotado':'Candidata a atendimento'}</td></tr>`).join(''):'<tr><td colspan="5">Não há CTO conectada ao ponto no grafo viário disponível.</td></tr>';
  $('plan-options').innerHTML=options.map((option,index)=>`<button class="planning-option ${index===planningSelection?'selected':''}" data-plan-option="${index}"><span class="planning-option-kind">${option.kind==='existing'?'CTO EXISTENTE':'NOVA CTO · HIPÓTESE DE 16 PORTAS'}</span><strong>${option.kind==='existing'?escapeHTML(option.cto_id):'Local '+(index+1)+' para estudar'}</strong><p>${n(option.drop_cable_m)} m de percurso de drop · ${n(option.fiber_extension_m)} m de extensão</p><span>${option.additional_by_ports} outros endereços em estudo, limitados por portas</span><b>${option.estimated_cost===null?'Custo pendente':money(option.estimated_cost)}</b><small>Engenharia e disponibilidade física pendentes</small></button>`).join('')||'<div class="empty">Nenhuma alternativa conectada ao traçado cadastrado. Amplie o inventário ou a malha viária antes de estimar uma implantação.</div>';
  $('plan-options').querySelectorAll('[data-plan-option]').forEach(button=>button.onclick=()=>{planningSelection=Number(button.dataset.planOption);renderPlanningResults();});
  $('plan-selected').hidden=!options.length;
  if(options.length){renderPlanningDetail(options[planningSelection]);drawPlanningRoute(options[planningSelection]);}
}
function renderPlanningDetail(option){
  $('plan-metrics').innerHTML=kpi('Cabo com reserva',`${n(option.cable_with_slack_m)} m`,`${planningData.parameters.slack_pct}% de reserva adotada · drop + extensão`,'cable')+kpi('Outros pedidos pelo trajeto',n(option.compatible_request_ids.length),'IDs únicos · não são vendas confirmadas','users')+kpi('Limite adicional por portas',n(option.additional_by_ports),`${option.ports_after_current} portas após o pedido atual · hipótese`,'network')+kpi('Sinais históricos próximos',n(option.historical_signal_ids.length),'Células do radar em até 500 m · não são clientes','layers');
  const itinerary=(label,route)=>`<div><h3>${label}</h3>${route.streets.length?'<ol>'+route.streets.map(s=>`<li><span>${escapeHTML(s.street)}</span><b>${n(s.length_m)} m</b></li>`).join('')+'</ol>':'<p>O local coincide com o traçado cadastrado; derivação e fibra livre ainda não verificadas.</p>'}</div>`;
  $('plan-itinerary').innerHTML=(option.kind==='new_cto'?itinerary('Fibra: ponto de origem → local da CTO',option.fiber_route):'')+itinerary('Drop: CTO → projeção do pedido na rua',option.drop_route);
  $('plan-interpretation').innerHTML=`<h3>Por que esta alternativa entrou</h3><p>${escapeHTML(option.reason)}</p><p>${option.compatible_request_ids.length} outros pedidos fictícios estão dentro do limite de ${n(planningData.parameters.max_drop_m)} m por ruas a partir deste local. Após reservar uma porta para o pedido atual, o teto inicial é ${option.additional_by_ports}; isso não confirma capacidade óptica ou adesão.</p><p>${option.historical_signal_ids.length} células do radar de 2024/2025 ficam a até 500 m em linha reta. Elas orientam investigação territorial e não aumentam a quantidade de clientes estimada.</p><h3>Antes de executar</h3><ul><li>Conferir número do imóvel, entrada e percurso de acesso.</li><li>Validar postes/dutos, travessias e autorização de implantação.</li><li>Confirmar porta, fibra de origem, derivação, split e orçamento óptico.</li><li>Levantar materiais, mão de obra e demais custos; confirmar os pedidos.</li></ul><div class="detail-callout"><strong>${option.estimated_cost===null?'Orçamento pendente':'Estimativa com suas referências: '+money(option.estimated_cost)}</strong>${option.estimated_cost===null?'Preencha os custos necessários. Uma nova CTO exige valores de drop/m, fibra/m e CTO instalada; atendimento existente exige drop/m.':'Cabo com a reserva adotada × custo por metro, mais CTO instalada quando aplicável. Não inclui postes, travessias, equipamentos ativos, licenças, deslocamentos, impostos ou contingências.'}</div>`;
}
function drawPlanningRoute(option){
  planningLayers.route.clearLayers();
  const city=radarData?.cities.find(c=>c.id===$('plan-city').value);
  if(city)city.regions.filter(r=>option.historical_signal_ids.includes(r.id)).forEach(r=>L.polygon(r.polygon,{color:'#b9a557',weight:1,fillOpacity:.12,interactive:false}).addTo(planningLayers.route));
  if(option.fiber_route.points.length>1)L.polyline(option.fiber_route.points,{color:'#d48f4d',weight:5,opacity:.95}).bindTooltip('Extensão de fibra proposta · pendente').addTo(planningLayers.route);
  if(option.drop_route.points.length>1)L.polyline(option.drop_route.points,{color:'#2c9066',weight:4,opacity:.95}).bindTooltip('Percurso de drop pelas ruas · pendente').addTo(planningLayers.route);
  L.polyline(option.access_guide,{color:'#8b8076',dashArray:'4 5',weight:2,interactive:false}).addTo(planningLayers.route);
  L.circleMarker(option.site,{radius:8,color:'#fff',weight:2,fillColor:option.kind==='existing'?'#426e95':'#d48f4d',fillOpacity:1}).bindTooltip(option.kind==='existing'?option.cto_id:'Local proposto para CTO · não é poste verificado').addTo(planningLayers.route);
  if(option.kind==='new_cto')L.circleMarker(option.network_origin,{radius:6,color:'#426e95',weight:2,fillColor:'white',fillOpacity:1}).bindTooltip('Ponto no traçado para investigar derivação; fibra livre desconhecida').addTo(planningLayers.route);
  const points=[...option.drop_route.points,...option.fiber_route.points,...option.access_guide];
  if(points.length)planningMap.fitBounds(L.latLngBounds(points),{padding:[45,45],maxZoom:17});
}
function exportPlanning(){
  if(!planningData)return;
  const result={...planningData,selected_proposal:planningData.proposals[planningSelection]?.id||null,exported_at:new Date().toISOString(),purpose:'Estudo preliminar sobre inventário e pedidos fictícios; não é projeto aprovado.'};
  const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=`ESTUDO-expansao-${result.city_id}.json`;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);toast('Estudo exportado com rotas, premissas e pendências.');
}
