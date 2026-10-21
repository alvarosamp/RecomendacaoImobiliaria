/* Public aggregated census data and source-linked documentary screening. */
'use strict';
let knowledgeTerritory=null,knowledgeCatalog=null,knowledgePromise=null,knowledgeMap=null,knowledgeCells=null;
const legalStatus={pending:'Documento ou validação pendente',scope_unknown:'Incidência a confirmar',declared_absent:'Ausência declarada · não verificada'};
async function loadKnowledge(){
  if(!knowledgePromise)knowledgePromise=Promise.all([fetch('/api/territory'),fetch('/api/regulations')]).then(async responses=>{
    if(responses.some(r=>!r.ok))throw new Error('As bases públicas não responderam. Tente novamente.');
    [knowledgeTerritory,knowledgeCatalog]=await Promise.all(responses.map(r=>r.json()));
    if(knowledgeTerritory.meta.synthetic!==false)throw new Error('A camada territorial deve ter origem pública real.');
  }).catch(error=>{knowledgePromise=null;throw error;});
  await knowledgePromise;
}
function initKnowledge(){
  $('knowledge-city').innerHTML=db.cities.map(c=>`<option value="${escapeHTML(c.id)}">${escapeHTML(c.name)}</option>`).join('');
  $('knowledge-city').onchange=()=>{if(knowledgeTerritory)renderKnowledge();};
  $('knowledge-scope').onchange=renderKnowledgeReferences;$('knowledge-search').oninput=renderKnowledgeReferences;
  $('knowledge-export').onclick=exportKnowledge;
  $('plan-show-territory').onchange=()=>{drawPlanningTerritory();if(planningData?.proposals.length)drawPlanningRoute(planningData.proposals[planningSelection]);};
}
async function openKnowledge(){
  $('knowledge-status').textContent='Carregando bases públicas e referências…';$('knowledge-error').hidden=true;
  try{await loadKnowledge();$('knowledge-content').hidden=false;$('knowledge-export').disabled=false;renderKnowledge();$('knowledge-status').textContent='IBGE/Censo 2022 · referências consultadas em '+formatDate(knowledgeCatalog.meta.checked_on)+'.';}
  catch(error){$('knowledge-error').hidden=false;$('knowledge-error').textContent=error.message;$('knowledge-status').textContent='Fontes não carregadas.';}
}
function renderKnowledge(){
  const city=knowledgeTerritory.cities.find(c=>c.id===$('knowledge-city').value);
  $('knowledge-kpis').innerHTML=kpi('Endereços únicos mapeados',n(city.mapped_addresses),'Coordenada original do Censo · NV=1','pin')+kpi('Domicílio particular',n(city.mapped_residential_addresses),'Endereços, não pessoas ou assinantes','users')+kpi('Fora da camada',n(city.excluded_non_original_coordinates),'IDs com coordenada de nível diferente de 1','info')+kpi('Células de 200 m',n(city.cells.length),'Agregação espacial · referência 2022','layers');
  if(!knowledgeMap){knowledgeMap=L.map('knowledge-map',{preferCanvas:true});L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap contributors'}).addTo(knowledgeMap);knowledgeCells=L.layerGroup().addTo(knowledgeMap);}
  knowledgeCells.clearLayers();
  city.cells.forEach(cell=>L.rectangle(cell.bounds,{color:'#698bad',weight:.5,fillColor:cellColor(cell.residential),fillOpacity:.6}).bindTooltip(`${n(cell.residential)} endereços de domicílio particular · Censo 2022`).on('click',()=>renderKnowledgeCell(city,cell)).addTo(knowledgeCells));
  knowledgeMap.invalidateSize();knowledgeMap.setView(city.center,13);renderKnowledgeCell(city,null);
  $('knowledge-method').innerHTML=`<p>${n(city.raw_records)} registros brutos → ${n(city.unique_address_ids)} códigos únicos → ${n(city.mapped_addresses)} endereços com coordenada original publicados como contagens em grade. ${n(city.duplicate_records)} registros repetidos por código foram deduplicados; ${n(city.invalid_records)} registros inválidos foram descartados.</p><p>Um código é contado uma vez. Um endereço é classificado como residencial se alguma finalidade tiver COD_ESPECIE=1 (domicílio particular). Apartamentos com códigos diferentes podem compartilhar coordenadas.</p><ul>${knowledgeTerritory.meta.limitations.map(l=>`<li>${escapeHTML(l)}</li>`).join('')}</ul><p><a href="${escapeHTML(city.source_url)}" target="_blank" rel="noopener noreferrer">Arquivo municipal original ↗</a> · <a href="${escapeHTML(knowledgeTerritory.meta.methodology_url)}" target="_blank" rel="noopener noreferrer">Metodologia do IBGE ↗</a></p><p class="knowledge-hash">SHA-256 do ZIP: ${escapeHTML(city.source_sha256)}</p>`;
  renderKnowledgeReferences();
  $('knowledge-projects').innerHTML=knowledgeCatalog.projects.filter(p=>p.city_id===city.id).map(p=>`<article class="panel knowledge-reference"><span class="knowledge-tag">${escapeHTML(p.type)}</span><h3>${escapeHTML(p.title)}</h3><p>${escapeHTML(p.summary)}</p><p>Data da referência: ${formatDate(p.date)}.</p><a href="${escapeHTML(p.url)}" target="_blank" rel="noopener noreferrer">Consultar documento histórico ↗</a></article>`).join('');
  $('knowledge-external').innerHTML='<h2>Dados setoriais da Anatel</h2>'+knowledgeCatalog.external_data.map(s=>`<p>${escapeHTML(s.status)} ${escapeHTML(s.use)}</p><a href="${escapeHTML(s.url)}" target="_blank" rel="noopener noreferrer">${escapeHTML(s.title)} ↗</a>`).join('');
}
function renderKnowledgeCell(city,cell){
  $('knowledge-cell').innerHTML=cell?`<span class="knowledge-tag">CÉLULA · IBGE 2022</span><h2>${n(cell.residential)} endereços de domicílio particular</h2><p>${n(cell.total)} endereços únicos de todas as finalidades nesta célula.</p><p>Referência: ${escapeHTML(cell.id)}. Seleção de coordenadas originais e agregação em 200 m.</p><p>Não representa clientes disponíveis, imóveis vagos, adesão futura ou cobertura de internet.</p>`:`<span class="knowledge-tag">${escapeHTML(city.name)}</span><h2>Clique em uma célula para consultar</h2><p>Esta camada usa dados públicos históricos e não contém o cadastro de assinantes de um provedor.</p><p>Em Planejar expansão, você pode ligar a camada e comparar o entorno das alternativas com as pendências regulatórias.</p>`;
}
function cellColor(count){return count>150?'#385d83':count>60?'#638bae':count>15?'#97b4cf':'#d3e1ed';}
function renderKnowledgeReferences(){
  if(!knowledgeCatalog)return;
  const city=$('knowledge-city').value,scope=$('knowledge-scope').value,q=$('knowledge-search').value.trim().toLocaleLowerCase('pt-BR');
  const refs=knowledgeCatalog.references.filter(r=>(!r.city_id||r.city_id===city)&&(scope==='all'||scope===r.scope)&&(!q||[r.title,r.summary,r.articles].join(' ').toLocaleLowerCase('pt-BR').includes(q)));
  $('knowledge-references').innerHTML=refs.map(r=>`<article class="panel knowledge-reference"><span class="knowledge-tag">${escapeHTML(r.kind)}</span><h3>${escapeHTML(r.title)}</h3><p>${escapeHTML(r.summary)}</p><p><strong>Trecho de referência:</strong> ${escapeHTML(r.articles)}</p><details><summary>Consulta e limites de aplicação</summary><p>Consulta: ${formatDate(r.checked_on)}. ${escapeHTML(r.review_note)}</p></details><a href="${escapeHTML(r.url)}" target="_blank" rel="noopener noreferrer">Abrir fonte oficial ↗</a></article>`).join('')||'<p class="empty">Nenhuma referência para estes filtros.</p>';
}
function exportKnowledge(){
  const city=knowledgeTerritory.cities.find(c=>c.id===$('knowledge-city').value);
  const result={type:'FeatureCollection',metadata:{...knowledgeTerritory.meta,city:city.name,source_url:city.source_url,source_sha256:city.source_sha256},features:city.cells.map(c=>{const [[s,w],[n,e]]=c.bounds;return{type:'Feature',geometry:{type:'Polygon',coordinates:[[[w,s],[e,s],[e,n],[w,n],[w,s]]]},properties:{id:c.id,addresses:c.total,residential_addresses:c.residential,reference_year:2022}};})};
  const url=URL.createObjectURL(new Blob([JSON.stringify(result)],{type:'application/geo+json'}));const a=document.createElement('a');a.href=url;a.download=`IBGE-CNEFE-2022-celulas-${city.id}.geojson`;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);toast('Células agregadas exportadas com fonte e metodologia.');
}
async function drawPlanningTerritory(){
  if(!planningMap)return;
  planningLayers.territory?.clearLayers();
  if(!$('plan-show-territory').checked)return;
  try{await loadKnowledge();if(!$('plan-show-territory').checked)return;
    if(!planningLayers.territory)planningLayers.territory=L.layerGroup().addTo(planningMap);
    planningLayers.territory.clearLayers();
    const city=knowledgeTerritory.cities.find(c=>c.id===$('plan-city').value);
    city.cells.forEach(c=>L.rectangle(c.bounds,{color:'#698bad',weight:.5,fillColor:cellColor(c.residential),fillOpacity:.25,interactive:false}).addTo(planningLayers.territory));
    // Keep cable routes and the customer above the census layer.
    planningLayers.route.eachLayer(l=>l.bringToFront?.());planningLayers.target.eachLayer(l=>l.bringToFront?.());
  }catch(error){$('plan-show-territory').checked=false;toast('Camada IBGE não carregada. O estudo e suas fontes permanecem disponíveis.');}
}
function renderPlanningKnowledge(option){
  const t=option?.real_territory;
  $('plan-territory').hidden=!t;
  if(t)$('plan-territory').innerHTML=`<span class="knowledge-tag">DADO REAL · IBGE / CNEFE 2022</span><h2>${n(t.residential_addresses)} endereços de domicílio particular no entorno</h2><p>Células com centro a até ${n(t.radius_m)} m em <strong>linha reta</strong> da CTO estudada. O valor não é contagem pelo percurso do cabo, não é limitado pelas portas e não entra na ordenação das alternativas.</p><p>Faixa geométrica aproximada pelas bordas das células: ${n(t.cell_boundary_min)} a ${n(t.cell_boundary_max)} endereços. Células de ${t.grid_m} m; somente coordenadas originais do Censo.</p><p>Não representa assinantes, cobertura atual ou adesão futura. <a href="${escapeHTML(t.source_url)}" target="_blank" rel="noopener noreferrer">Consultar arquivo do IBGE ↗</a></p>`;
  const r=option?.regulatory||planningData?.regulatory;$('plan-regulation').hidden=!r;
  if(!r)return;
  $('plan-regulation').innerHTML=`<div class="knowledge-reg-heading"><div><span class="knowledge-tag">ANÁLISE DOCUMENTAL · PENDENTE</span><h2>${r.pending_count} pontos para conferir antes de executar</h2></div><span class="small-tag">Fontes consultadas em ${formatDate(r.checked_on)}</span></div><p>${escapeHTML(r.notice)}</p><p>As condições foram informadas no formulário; não houve cruzamento automático com postes, faixas de domínio, zoneamento ou áreas protegidas.</p><div class="knowledge-checklist">${r.checks.map(c=>`<article><span class="knowledge-check-status">${legalStatus[c.status]}</span><h3>${escapeHTML(c.title)}</h3><p>${escapeHTML(c.action)}</p><details><summary>Base e evidência necessária</summary>${c.references.map(ref=>`<p><a href="${escapeHTML(ref.url)}" target="_blank" rel="noopener noreferrer">${escapeHTML(ref.title)} ↗</a><br><small>${escapeHTML(ref.articles)}. ${escapeHTML(ref.review_note)}</small></p>`).join('')}</details></article>`).join('')}</div>`;
}
