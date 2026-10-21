async function revealAuxiliary(page){const section=page.locator(".workspace-secondary");if(await section.count()&&!await section.evaluate(element=>element.open))await section.locator(":scope > summary").click()}
const { chromium } = require('playwright')
const assert = require('node:assert/strict')
const fs = require('node:fs')
;(async () => {
 const financial=JSON.parse(fs.readFileSync(process.env.URBIA_FINANCIAL_FIXTURE || '/private/tmp/urbia-finance-fixture.json','utf8'))
 const browser=await chromium.launch({channel:'chrome',headless:true,args:['--enable-unsafe-swiftshader']})
 try {
  const context=await browser.newContext({viewport:{width:1440,height:1000},timezoneId:'America/Sao_Paulo'})
  await context.addInitScript(()=>localStorage.setItem('token','fixture'))
  const page=await context.newPage(), errors=[]
  page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept())
  let saved=null
  await page.route('**/api/**',async route=>{
   const request=route.request(), path=new URL(request.url()).pathname
   let body=[]
   if(path.endsWith('/history')) body={items:[],next_before_revision:null}
   else if(path==='/api/auth/me') body={id:1,name:'Teste',role:'incorporadora'}
   else if(path==='/api/scores') body=[{h3_id:'88a88c994bfffff',zona:'ZR',score_residencial:70,score_comercial:35}]
   else if(path==='/api/projects' && request.method()==='GET') body=saved?[saved]:[]
   else if(path==='/api/projects' || path==='/api/projects/1') {saved={...request.postDataJSON(),id:1,revision:(saved?.revision||0)+1,can_edit:true,analysis:null};body=saved}
   else if(path==='/api/projects/1/analyze') {saved={...saved,revision:saved.revision+1,analysis:{captured_at:new Date().toISOString(),financial,legal:{status:'conditioned',articles:[],sources:[]},concept:{scenarios:[]}}};body=saved}
   else if(path==='/api/projects/1/report') return route.fulfill({contentType:'text/markdown',body:'# Estudo financeiro de teste'})
   else if(path.includes('geojson')) body={type:'FeatureCollection',features:[]}
   else if(path.includes('timeseries')) body={dates:[],records:[]}
   await route.fulfill({contentType:'application/json',body:JSON.stringify(body)})
  })
  await page.goto('http://127.0.0.1:4175/app')
  await revealAuxiliary(page)
  await page.getByRole('button',{name:'Iniciar análise'}).first().click()
  await page.getByRole('button',{name:'2. Premissas'}).click()
  await page.getByLabel('Nome do projeto').fill('Estudo com premissas financeiras')
  await page.getByLabel('Região de referência').selectOption('88a88c994bfffff')
  await page.getByLabel('Incluir análise financeira').check()
  const fields={'Aquisição do terreno (R$)':'100000','Construção por m² (R$)':'1000','Outros custos fixos (R$)':'0','Contingência sobre construção (%)':'0','Área vendável (m²)':'100','Preço de venda por m² (R$)':'3000','Despesas e tributos sobre vendas (%)':'0','Prazo até a venda integral (meses)':'12','Taxa anual de desconto (%)':'0','Sensibilidade do custo de construção (%)':'10','Sensibilidade do preço de venda (%)':'10','Data de referência':'2026-10-14','Origem das premissas':'Premissas controladas para teste'}
  for(const [label,value] of Object.entries(fields)) await page.getByLabel(label,{exact:true}).fill(value)
  await page.getByRole('button',{name:'Salvar projeto',exact:true}).click()
  await page.getByRole('status').filter({hasText:'Projeto salvo'}).waitFor()
  assert.equal(saved.financial.other_costs,0)
  assert.equal(saved.financial.annual_discount_pct,0)
  await page.reload()
  await page.getByRole('button',{name:'Projetos de terrenos'}).click()
  await page.getByLabel('Retomar estudo').selectOption('1')
  await page.getByRole('button',{name:'2. Premissas'}).click()
  assert.equal(await page.getByLabel('Aquisição do terreno (R$)',{exact:true}).inputValue(),'100000')
  await page.getByRole('button',{name:'3. Restrições e cenários'}).click()
  await page.getByRole('button',{name:'Salvar e calcular análise integrada'}).click()
  await page.getByRole('heading',{name:'Base informado'}).waitFor()
  await page.getByText('Fluxo mensal do cenário base',{exact:true}).click()
  await page.getByRole('heading',{name:'Estudo financeiro informado'}).scrollIntoViewIfNeeded()
  await page.screenshot({path:'/private/tmp/urbia-financial-desktop.png'})
  assert.equal(await page.locator('.financial-results tbody tr').count(),13)
  await page.setViewportSize({width:390,height:844})
  await page.waitForFunction(()=>document.querySelector('.sidebar').getBoundingClientRect().right<=0)
  await page.getByRole('heading',{name:'Estudo financeiro informado'}).scrollIntoViewIfNeeded()
  await page.screenshot({path:'/private/tmp/urbia-financial-mobile.png'})
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth))
  assert.ok(await page.evaluate(()=>document.querySelector('.financial-results').getBoundingClientRect().right <= window.innerWidth), 'Financial panel overflows its scrolling parent')
  assert.deepEqual(errors,[])
  console.log('Validated financial assumptions, zero values, persistence, results, cash flow and responsive layout.')
  await context.close()
 } finally {await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1})
