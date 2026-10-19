/* Real satellite screening; ISP inventory remains explicitly synthetic. */
'use strict';
let radarData=null, radarSelectedId=null, radarPage=0;
const RADAR_PAGE=6;
const radarCity=()=>radarData?.cities.find(c=>c.id===$('radar-city').value);
function radarRegions(){
  const city=radarCity();if(!city)return [];
  const radius=$('radar-radius').value;
  const action=$('radar-action').value;
  return city.regions.filter(r=>(radius==='all'||r.network_distance_m<=Number(radius))&&(action==='all'||r.action===action));
}
async function initRadar(){
  const response=await fetch('/api/radar');
  if(!response.ok)throw new Error('Radar indisponível');
  radarData=await response.json();
  $('radar-city').innerHTML=radarData.cities.map(c=>`<option value="${escapeHTML(c.id)}">${escapeHTML(c.name)}</option>`).join('');
  ['radar-city','radar-radius','radar-action'].forEach(id=>$(id).onchange=()=>{radarPage=0;radarSelectedId=null;renderRadar();});
  $('radar-swipe').oninput=()=>{$('radar-after-layer').style.clipPath=`inset(0 0 0 ${$('radar-swipe').value}%)`;$('radar-divider').style.left=$('radar-swipe').value+'%';$('radar-swipe').setAttribute('aria-valuetext',`${$('radar-swipe').value}% de 2024 à esquerda; ${100-Number($('radar-swipe').value)}% de 2025 à direita`);};
  $('radar-show-ctos').onchange=renderRadar;
  $('radar-show-regions').onchange=renderRadar;
  $('radar-previous').onclick=()=>{radarPage--;renderRadarList();};
  $('radar-next').onclick=()=>{radarPage++;renderRadarList();};
  $('radar-export').onclick=exportRadar;
  $('radar-content').hidden=false;$('radar-loading').hidden=true;$('radar-error').hidden=true;
  renderRadar();
}
function handleRadarError(error){
  $('radar-loading').hidden=true;$('radar-content').hidden=true;$('radar-error').hidden=false;
  $('radar-error').innerHTML='<strong>Não foi possível carregar o radar.</strong><p>O catálogo local ou as cenas estão indisponíveis. Os demais módulos continuam disponíveis.</p><button class="button" id="radar-retry">Tentar novamente</button>';
  $('radar-retry').onclick=()=>initRadar().catch(handleRadarError);
  console.error('Radar:',error);
}
function openRadar(){
  if(!radarData)return;
  if($('city').value!=='all'&&radarData.cities.some(c=>c.id===$('city').value))$('radar-city').value=$('city').value;
  renderRadar();
}
function renderRadar(){
  if(!radarData)return;
  const city=radarCity(),regions=radarRegions();
  if(!regions.some(r=>r.id===radarSelectedId))radarSelectedId=regions[0]?.id||null;
  const requests=new Set(regions.flatMap(r=>r.nearby_request_ids));
  $('radar-kpis').innerHTML=kpi('Áreas para investigar',n(regions.length),'Células de 200 × 200 m · triagem exploratória','search')+kpi('Superfície com sinal espectral',`${n(regions.reduce((sum,r)=>sum+r.changed_area_ha,0).toFixed(2))} <span style="font-size:15px">ha</span>`,'Soma de pixels sinalizados · não é área construída','layers')+kpi('Pedidos próximos · fictícios',n(requests.size),'IDs únicos em até 500 m do centro das células','pin')+kpi('Pixels utilizáveis nas 4 cenas',`${n(city.valid_area_pct)}%`,'Inclui exclusão de água, nuvens e sombras','dashboard');
  $('radar-before').src=city.images.before;$('radar-after').src=city.images.after;
  $('radar-before').alt=`Composição Sentinel-2 real de 2024 em ${city.name}`;
  $('radar-after').alt=`Composição Sentinel-2 real de 2025 em ${city.name}`;
  const dates=period=>city.sources[period].map(s=>formatDate(s.datetime.slice(0,10))).join(' + ');
  $('radar-before-date').textContent=dates('before');$('radar-after-date').textContent=dates('after');
  $('radar-image-caption').textContent=`${city.name} · recorte de 6,4 × 6,4 km · grade de análise de 20 m. Composições reais de duas cenas por época; mesma escala de cores. Deslize para comparar.`;
  renderRadarOverlay();renderRadarDetail();renderRadarList();
  $('radar-provenance').innerHTML=`<h3>Cenas utilizadas e condição dos dados</h3><div class="radar-sources-grid">${['before','after'].map(p=>`<div><strong>${p==='before'?'Referência 2024':'Observações 2025'}</strong>${city.sources[p].map(s=>`<a href="${escapeHTML(s.stac_url)}" target="_blank" rel="noopener">${escapeHTML(s.id)} ↗</a><small>${formatDate(s.datetime.slice(0,10))} · ${n(s.scene_cloud_pct)}% de nuvem na cena inteira; ${n(s.local_usable_pct)}% de pixels utilizáveis no recorte.</small>`).join('')}</div>`).join('')}</div><p>${city.eligible_cells} de ${city.screened_cells} células têm pelo menos 80% de pixels utilizáveis nas quatro cenas. ${city.candidate_count} passaram na regra espectral antes dos filtros de proximidade. Nuvem da cena inteira não é nuvem do recorte.</p><h3>Como interpretar</h3><ol><li>Comparar mediana de duas cenas de julho–setembro de 2024 com duas observações de julho–setembro de 2025.</li><li>Manter apenas pixels SCL de vegetação ou superfície não vegetada, válidos em todas as cenas.</li><li>Sinalizar aumento de NDBI de pelo menos 0,10 e queda de NDVI de pelo menos 0,12 nas duas observações posteriores. Uma célula só entra com ao menos 12 pixels sinalizados (0,48 ha).</li><li>Ordenar áreas por pedidos próximos, distância da rede e condição da CTO. “Priorizar visita” exige pedido a até 500 m, rede e CTO a até 500 m, CTO operacional e porta livre no cadastro fictício.</li></ol><p><strong>Hipótese a validar:</strong> esta regra detecta sinais espectrais persistentes; não é um modelo validado de crescimento urbano. Solo exposto, agricultura e sazonalidade podem gerar falsos positivos. Não detecta casas individuais, moradores, renda, adesão ou concorrentes.</p><p><strong>Datas distintas:</strong> satélite de 2024/2025; rede e pedidos fictícios no retrato de 18/10/2026. As relações comerciais servem para demonstrar o produto, sem comprovar oportunidade atual.</p><p>Dados Copernicus Sentinel (2024–2025), processados com <a href="https://earth-search.aws.element84.com/v1" target="_blank" rel="noopener">Earth Search / Element 84</a>. Bandas RGB/NIR agregadas e SWIR em grade comum de 20 m; escala e offset do catálogo aplicados. Versão: ${escapeHTML(radarData.meta.algorithm)}.</p>`;
}
function renderRadarOverlay(){
  const city=radarCity(),regions=radarRegions();
  const polygons=$('radar-show-regions').checked?regions.map((r,index)=>`<g class="radar-region ${r.id===radarSelectedId?'chosen':''}" data-region="${escapeHTML(r.id)}" role="button" tabindex="0" aria-label="Selecionar área ${index+1}"><polygon points="${r.display_polygon.map(p=>p.join(',')).join(' ')}"/><title>${escapeHTML(r.id)} · ${n(r.changed_area_ha)} ha com sinal espectral</title></g>`).join(''):'';
  const ctos=$('radar-show-ctos').checked?city.ctos.map(c=>`<circle class="radar-cto ${c.status==='offline'?'offline':''}" cx="${c.display_point[0]}" cy="${c.display_point[1]}" r="1.5"><title>${escapeHTML(c.id)} · CTO fictícia</title></circle>`).join(''):'';
  const fiber=$('radar-show-ctos').checked?(city.fiber||[]).map(line=>`<polyline class="radar-fiber" points="${line.map(p=>p.join(',')).join(' ')}"/>`).join(''):'';
  $('radar-overlay').innerHTML=fiber+polygons+ctos;
  $('radar-overlay').querySelectorAll('[data-region]').forEach(el=>{
    const choose=()=>{radarSelectedId=el.dataset.region;renderRadarOverlay();renderRadarDetail();renderRadarList();};
    el.onclick=choose;el.onkeydown=event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();choose();}};
  });
}
function selectRadarRegion(id){radarSelectedId=id;renderRadarOverlay();renderRadarDetail();renderRadarList();}
function renderRadarDetail(){
  const region=radarRegions().find(r=>r.id===radarSelectedId);
  if(!region){$('radar-detail').innerHTML='<div class="detail-eyebrow">NENHUMA ÁREA NESTE RECORTE</div><h2>Sem sinal para investigar.</h2><p class="detail-sub">Nenhuma célula atende simultaneamente à qualidade, à regra espectral e aos filtros escolhidos. Isso não comprova ausência de crescimento. Experimente ampliar a distância ou consultar a qualidade das cenas.</p>';return;}
  const title=region.action;
  const capacityReason=region.free_ports>0?`${region.free_ports} portas livres na CTO mais próxima (fictícia).`:'A CTO mais próxima não tem porta livre no cadastro fictício.';
  $('radar-detail').innerHTML=`<div class="detail-eyebrow">ÁREA PARA INVESTIGAÇÃO · NÃO VALIDADA</div><h2>${escapeHTML(title)}</h2><p class="detail-sub">${escapeHTML(region.id)}<br>Setor ${escapeHTML(region.sector)} associado à CTO · não é bairro oficial.</p><div class="radar-evidence-title">Evidência de satélite · real</div><div class="detail-stats">${detailRow('Superfície sinalizada',`${n(region.changed_area_ha)} ha de 4 ha`)}${detailRow('Pixels utilizáveis',`${n(region.valid_pct)}%`)}${detailRow('NDVI médio da célula',`${n(region.ndvi_before)} → ${n(region.ndvi_after)}`)}${detailRow('NDBI médio da célula',`${n(region.ndbi_before)} → ${n(region.ndbi_after)}`)}</div><p class="mini-caption">Médias são contexto da célula; a regra é aplicada pixel a pixel. Sinal repetido nas duas observações de 2025.</p><div class="radar-evidence-title">Operação do provedor · fictícia</div><p class="mini-caption">Distâncias a partir do centro da célula, sem rota de instalação ou validação óptica.</p><div class="detail-stats">${detailRow('Distância à fibra cadastrada',`${n(region.network_distance_m)} m`)}${detailRow('CTO mais próxima',escapeHTML(region.nearest_cto))}${detailRow('Distância até a CTO',`${n(region.cto_distance_m)} m`)}${detailRow('Estado da CTO',labels[region.cto_status])}${detailRow('Pedidos a até 500 m',region.nearby_request_ids.length)}</div><div class="detail-callout"><strong>Por que investigar</strong>${capacityReason} ${region.nearby_request_ids.length?'Há pedidos fictícios próximos para confrontar com o sinal observado.':'Sem pedidos próximos no cenário; demanda permanece desconhecida.'}</div><div class="radar-next-action"><strong>Próxima ação</strong><p>Conferir se a mudança corresponde a obra, solo exposto ou ocupação. Confirmar endereços e interesse; validar rota, capacidade óptica e custo em campo.</p></div><button class="button" id="radar-inspect-cto">Ver CTO no mapa →</button><div class="radar-validation-status">Validação em campo: pendente · não há aprovação de expansão.</div>`;
  $('radar-inspect-cto').onclick=()=>{
    if(inspectionBusy()){toast('Encerre a inspeção simulada atual antes de trocar o território.');return;}
    $('city').value=region.city_id;$('sector').value='all';$('search').value='';$('status').value='all';selected=null;renderAll();setView('network');selectEntity('cto',region.nearest_cto,true);
  };
}
function renderRadarList(){
  const regions=radarRegions(),pages=Math.max(1,Math.ceil(regions.length/RADAR_PAGE));
  radarPage=Math.max(0,Math.min(radarPage,pages-1));
  $('radar-list').innerHTML=regions.slice(radarPage*RADAR_PAGE,(radarPage+1)*RADAR_PAGE).map((r,index)=>`<button class="radar-list-row ${r.id===radarSelectedId?'selected':''}" data-area="${escapeHTML(r.id)}"><span class="radar-row-number">${radarPage*RADAR_PAGE+index+1}</span><span><strong>${escapeHTML(r.action)}</strong><small>${escapeHTML(r.id)} · ${n(r.changed_area_ha)} ha sinalizados</small></span><span><strong>${n(r.network_distance_m)} m</strong><small>até a fibra fictícia</small></span><span><strong>${r.nearby_request_ids.length} pedidos</strong><small>em até 500 m</small></span><span>↗</span></button>`).join('')||'<div class="empty">Nenhuma área atende aos filtros. O radar não cria oportunidades para preencher o mapa.</div>';
  $('radar-list').querySelectorAll('[data-area]').forEach(button=>button.onclick=()=>selectRadarRegion(button.dataset.area));
  $('radar-page-count').textContent=`${regions.length} áreas · página ${radarPage+1}/${pages}`;
  $('radar-previous').disabled=radarPage===0;$('radar-next').disabled=radarPage===pages-1;
}
function exportRadar(){
  const city=radarCity(),regions=radarRegions();
  const data={type:'FeatureCollection',name:'Urbia radar — triagem exploratória',metadata:{...radarData.meta,city_id:city.id,sources:city.sources,filters:{network_distance_m:$('radar-radius').value,action:$('radar-action').value},field_validation:'pending'},features:regions.map(r=>({type:'Feature',id:r.id,geometry:{type:'Polygon',coordinates:[[...r.polygon.map(p=>[p[1],p[0]]),[r.polygon[0][1],r.polygon[0][0]]]]},properties:Object.fromEntries(Object.entries(r).filter(([k])=>!['polygon','display_polygon'].includes(k)))}))};
  const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/geo+json'}));const a=document.createElement('a');a.href=url;a.download=`RADAR-${city.id}-satelite-real-rede-ficticia.geojson`;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);toast(`${regions.length} áreas exportadas com cenas, critérios e proveniência.`);
}
