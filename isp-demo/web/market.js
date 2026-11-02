/* Real ANATEL market data (fixed broadband accesses by provider/municipality).
   Independent of the fictional SerraLink network scenario: no company here is
   converted into a competitor, CTO or client of the simulation. */
'use strict';
let marketData=null,marketPromise=null;
async function loadMarket(){
  if(!marketPromise)marketPromise=fetch('/api/market').then(async response=>{
    if(!response.ok)throw new Error('A base de mercado da Anatel não respondeu. Tente novamente.');
    marketData=await response.json();
    if(marketData.meta.synthetic!==false)throw new Error('A camada de mercado deve ter origem pública real.');
  }).catch(error=>{marketPromise=null;throw error;});
  await marketPromise;
}
function initMarket(){
  $('market-export').onclick=exportMarket;
}
async function openMarket(){
  $('market-status').textContent='Carregando acessos declarados à Anatel…';$('market-error').hidden=true;
  try{
    await loadMarket();
    $('market-content').hidden=false;$('market-export').disabled=false;
    if(!marketData.cities.some(c=>c.id===marketCityId()))marketSetCity(marketData.cities[0].id);
    renderMarket();
    $('market-status').textContent=`Fonte: ANATEL · competência de referência ${formatMonth(marketData.cities[0].reference_month)} · consulta em ${formatDate(marketData.meta.retrieved_at)}.`;
  }catch(error){$('market-error').hidden=false;$('market-error').textContent=error.message;$('market-status').textContent='Dados de mercado não carregados.';}
}
let marketCity='pouso-alegre';
const marketCityId=()=>marketCity;
function marketSetCity(id){marketCity=id;if(marketData)renderMarket();}
function formatMonth(value){const [y,m]=value.split('-');return new Date(Number(y),Number(m)-1,1).toLocaleDateString('pt-BR',{month:'long',year:'numeric'});}
function renderMarket(){
  const city=marketData.cities.find(c=>c.id===marketCity)||marketData.cities[0];
  $('market-city-list').innerHTML=marketData.cities.map(c=>`<button data-market-city="${escapeHTML(c.id)}" class="${c.id===city.id?'active':''}">${escapeHTML(c.name)}<span class="market-scope-tag ${c.scope}">${c.scope==='network'?'cenário fictício':'comparação'}</span></button>`).join('');
  document.querySelectorAll('[data-market-city]').forEach(button=>button.onclick=()=>marketSetCity(button.dataset.marketCity));
  const leader=city.ranking[0];
  $('market-kpis').innerHTML=
    kpi('Acessos declarados',n(city.total_accesses),`Competência ${formatMonth(city.reference_month)} · ${escapeHTML(city.uf)}`,'network')+
    kpi('Prestadoras distintas',n(city.distinct_providers),'Enviaram dados à Anatel neste município','users')+
    kpi('Maior participação',leader?`${(leader.share*100).toFixed(1)}%`:'—',leader?escapeHTML(leader.company):'—','spark')+
    kpi('Natureza do dado',city.scope==='network'?'Cenário fictício':'Comparação',city.scope==='network'?'Cidade também usada na simulação SerraLink':'Fora do cenário · referência de mercado','pin');
  $('market-ranking-caption').textContent=`${escapeHTML(city.name)} · ${formatMonth(city.reference_month)} · acessos declarados por prestadora`;
  $('market-ranking').innerHTML=`<div class="market-row-head"><span>Prestadora</span><span>%</span><span>Acessos</span></div>`+
    city.ranking.map((row,index)=>`<div class="market-row${index===0?' leader':''}"><strong>${escapeHTML(row.company)}</strong><span class="market-share">${(row.share*100).toFixed(1)}%</span><span class="market-count">${n(row.accesses)}</span><div class="market-bar-track"><div class="market-bar-fill" style="width:${(row.share*100).toFixed(2)}%"></div></div></div>`).join('');
  const months=city.monthly_total_accesses,max=Math.max(1,...months.map(m=>m.accesses));
  $('market-trend').innerHTML=`<div class="market-trend-chart" aria-label="Acessos totais declarados por mês">${months.map(m=>`<div class="market-trend-bar${city.scope==='network'?' network':''}" style="height:${m.accesses/max*100}%" data-tip="${formatMonth(m.month)}: ${n(m.accesses)} acessos"></div>`).join('')}</div><div class="market-trend-labels"><span>${formatMonth(months[0].month)}</span><span>${formatMonth(months.at(-1).month)}</span></div>`;
  $('market-provenance').innerHTML=`<p>Fonte: <a href="${escapeHTML(marketData.meta.dataset_page)}" target="_blank" rel="noopener noreferrer">${escapeHTML(marketData.meta.source)} ↗</a>. Arquivo nacional baixado em ${formatDate(marketData.meta.retrieved_at)}, filtrado para estas seis cidades; licença ${escapeHTML(marketData.meta.license)}, atualização ${escapeHTML(marketData.meta.periodicity).toLowerCase()}.</p><p>${escapeHTML(marketData.meta.unit)}.</p><ul>${marketData.meta.limitations.map(l=>`<li>${escapeHTML(l)}</li>`).join('')}</ul><p><a href="${escapeHTML(marketData.meta.methodology_url)}" target="_blank" rel="noopener noreferrer">Glossário e metadados da Anatel ↗</a></p>`;
}
function exportMarket(){
  const city=marketData.cities.find(c=>c.id===marketCity);
  const result={source:marketData.meta.source,source_url:marketData.meta.dataset_page,license:marketData.meta.license,retrieved_at:marketData.meta.retrieved_at,city:city.name,uf:city.uf,scope:city.scope,reference_month:city.reference_month,total_accesses:city.total_accesses,ranking:city.ranking,monthly_total_accesses:city.monthly_total_accesses,limitations:marketData.meta.limitations};
  const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}));
  const a=document.createElement('a');a.href=url;a.download=`ANATEL-mercado-real-${city.id}.json`;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
  toast('Dados reais de mercado exportados com fonte e licença.');
}
