async function revealAuxiliary(page){const section=page.locator(".workspace-secondary");if(await section.count()&&!await section.evaluate(element=>element.open))await section.locator(":scope > summary").click()}
const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs')
;(async()=>{
 const fixture=JSON.parse(fs.readFileSync(process.env.URBIA_TECHNICAL_FIXTURE||'/private/tmp/urbia-technical-fixture.json','utf8'))
 const browser=await chromium.launch({channel:'chrome',headless:true})
 try {
  const context=await browser.newContext({viewport:{width:1440,height:1000},timezoneId:'America/Sao_Paulo'})
  await context.addInitScript(()=>localStorage.setItem('token','fixture'))
  const page=await context.newPage(),errors=[];page.on('pageerror',error=>errors.push(error.message))
  let role='construtora',saved=null,profileWrites=0
  const second={id:2,name:'Estudo sem análise',revision:1,can_edit:true,premises:{lotArea:500,buildArea:200},analysis:null}
  await page.route('**/api/**',async route=>{
   const req=route.request(),path=new URL(req.url()).pathname
   let body=[]
   if(path==='/api/auth/me/profile'){role=req.postDataJSON().profile;profileWrites++;body={id:1,name:'Teste',role,is_admin:false}}
   else if(path==='/api/auth/me')body={id:1,name:'Teste',role,is_admin:false}
   else if(path==='/api/projects'&&req.method()==='GET')body=saved?[saved,second]:[]
   else if(path==='/api/projects'||(path==='/api/projects/1'&&req.method()==='PATCH')){saved={...req.postDataJSON(),id:1,revision:(saved?.revision||0)+1,can_edit:true,analysis:null};body=saved}
   else if(path==='/api/projects/1/analyze-premises'){saved={...saved,revision:saved.revision+1,analysis:{mode:'premises_only',captured_at:new Date().toISOString(),technical:fixture,financial:{status:'not_requested'},legal:{status:'analisar',articles:[],sources:[],spatial_overlays_verified:false},concept:{scenarios:[]}}};body=saved}
   else if(path.endsWith('/history'))body={items:[{revision:saved?.revision||1,actor_name:'Colaborador de teste',occurred_at:new Date().toISOString(),action:saved?.analysis?'premises_analyzed':'created',changed_fields:['technical']}],next_before_revision:null}
   else if(path.includes('geojson'))body={type:'FeatureCollection',features:[]}
   else if(path.includes('timeseries'))body={dates:[],records:[]}
   await route.fulfill({contentType:'application/json',body:JSON.stringify(body)})
  })
  await page.goto('http://127.0.0.1:4175/app')
  const modes={investidor:'Urbia Invest',corretor:'Urbia Mercado',incorporadora:'Urbia Incorpora',governo:'Urbia Governo',empreendedor:'Urbia Negócios',construtora:'Urbia Obras'}
  for(const [profile,name] of Object.entries(modes)){
   await page.getByLabel('Modo de trabalho').selectOption(profile)
   await page.getByText(name,{exact:true}).waitFor()
   await revealAuxiliary(page)
   assert.equal(await page.getByRole('button',{name:'Iniciar análise'}).count(),2)
  }
  await revealAuxiliary(page)
  await page.getByRole('button',{name:'Iniciar análise'}).first().click()
  await page.getByLabel('Nome do projeto').fill('Dossiê técnico de teste')
  await page.getByRole('button',{name:'2. Premissas'}).click()
  assert.equal(await page.getByLabel('Incluir diagnóstico técnico').isChecked(),true)
  await page.getByLabel('Declividade medida (%)').fill('0')
  await page.getByLabel('Água',{exact:true}).selectOption('reported_unavailable')
  await page.getByLabel('Referência cadastral ou matrícula').fill('Referência de teste')
  await page.getByLabel('Origem das informações técnicas').fill('Declaração controlada para teste')
  await page.getByLabel('Data das evidências técnicas').fill('2026-10-14')
  page.once('dialog',dialog=>dialog.dismiss())
  await page.getByRole('button',{name:'Equipes e acesso'}).click()
  assert.equal(await page.getByLabel('Nome do projeto').inputValue(),'Dossiê técnico de teste')
  const writes=profileWrites
  page.once('dialog',dialog=>dialog.dismiss())
  await page.getByLabel('Modo de trabalho').selectOption('empreendedor')
  assert.equal(profileWrites,writes)
  assert.equal(await page.getByLabel('Modo de trabalho').inputValue(),'construtora')
  page.once('dialog',dialog=>dialog.dismiss())
  await page.getByRole('button',{name:'Sair',exact:true}).click()
  assert.equal(await page.evaluate(()=>localStorage.getItem('token')),'fixture')
  await page.getByRole('button',{name:'Salvar projeto',exact:true}).click()
  await page.getByRole('status').filter({hasText:'Projeto salvo'}).waitFor()
  assert.equal(saved.technical.slope_pct,0)
  await page.getByRole('button',{name:'3. Restrições e cenários'}).click()
  await page.getByRole('button',{name:'Calcular somente premissas declaradas'}).click()
  await page.getByRole('heading',{name:'Diagnóstico de evidências técnicas'}).waitFor()
  await page.getByText('Análise somente de premissas:',{exact:false}).waitFor()
  await page.getByRole('heading',{name:'Diagnóstico de evidências técnicas'}).scrollIntoViewIfNeeded()
  await page.screenshot({path:'/private/tmp/urbia-technical-desktop.png'})
  await page.getByRole('heading',{name:'Histórico de atividades'}).scrollIntoViewIfNeeded()
  await page.getByText('Colaborador de teste',{exact:false}).waitFor()
  await page.getByRole('button',{name:'Comparar estudos',exact:true}).click()
  await page.getByLabel('Estudo 1',{exact:true}).selectOption('1')
  await page.getByLabel('Estudo 2',{exact:true}).selectOption('2')
  assert.equal(await page.getByRole('button',{name:'Baixar comparação (.md)'}).isDisabled(),false)
  const download=page.waitForEvent('download')
  await page.getByRole('button',{name:'Baixar comparação (.md)'}).click()
  assert.equal((await download).suggestedFilename(),'urbia-comparacao-estudos.md')
  await page.setViewportSize({width:390,height:844})
  await page.waitForFunction(()=>document.querySelector('.sidebar').getBoundingClientRect().right<=0)
  await page.screenshot({path:'/private/tmp/urbia-project-compare-mobile.png'})
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth))
  assert.deepEqual(errors,[])
  console.log('Validated six workspaces, technical evidence, declared-only analysis, history, comparison and unsaved navigation/profile/logout guards.')
  await context.close()
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exitCode=1})
