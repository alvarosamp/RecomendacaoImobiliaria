const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs')
;(async()=>{
 const technical=JSON.parse(fs.readFileSync(process.env.URBIA_TECHNICAL_FIXTURE||'/private/tmp/urbia-technical-fixture.json','utf8'))
 const browser=await chromium.launch({channel:'chrome',headless:true})
 try{
  const context=await browser.newContext({viewport:{width:1440,height:1000},timezoneId:'America/Sao_Paulo'})
  await context.addInitScript(()=>localStorage.setItem('token','fixture'))
  const page=await context.newPage(),errors=[]
  page.on('pageerror',error=>errors.push(error.message))
  const original={name:'Estudo original',h3_id:null,intended_use:'residencial',notes:'Evidência anterior',premises:{lotArea:300,buildArea:165,frontage:10,floors:2,typology:'casa',finish:'medio'},technical:{slope_pct:0},business:null,financial:null}
  let saved={...original,id:1,name:'Hipótese atual',revision:3,can_edit:true,technical:{slope_pct:7},analysis:null},attempts=0,viewer=false,restored=false
  await page.route('**/api/**',async route=>{
   const req=route.request(),path=new URL(req.url()).pathname
   let body=[]
   if(path==='/api/auth/me')body={id:1,name:'Teste',role:'incorporadora'}
   else if(path==='/api/projects')body=[{...saved,can_edit:!viewer}]
   else if(path==='/api/projects/1'&&req.method()==='PATCH'){saved={...req.postDataJSON(),id:1,revision:saved.revision+1,can_edit:true};body=saved}
   else if(path.endsWith('/history'))body={items:[{revision:saved.revision,actor_name:'Editor de teste',occurred_at:'2026-10-15T12:00:00Z',action:restored?'restored':'updated',changed_fields:['technical'],snapshot_available:true,restored_from_revision:restored?2:null},{revision:2,actor_name:'Editor de teste',occurred_at:'2026-10-14T12:00:00Z',action:'analyzed',changed_fields:['analysis'],snapshot_available:true}],next_before_revision:null}
   else if(path==='/api/projects/1/versions/2')body={revision:2,name:original.name,inputs:original,analysis:{captured_at:'2026-10-14T12:00:00Z',technical,legal:{status:'conditioned',notes:'Exige validação'},concept:{scenarios:[]}},saved_at:'2026-10-14T12:00:00Z',current_revision:saved.revision,differences:[{field:'name',historical:original.name,current:saved.name},{field:'technical.slope_pct',historical:0,current:7}]}
   else if(path==='/api/projects/1/versions/2/restore'){
    attempts++
    if(attempts===1)return route.fulfill({status:409,contentType:'application/json',body:JSON.stringify({detail:'Projeto alterado. Reabra antes de recuperar premissas.'})})
    assert.equal(req.postDataJSON().revision,saved.revision)
    restored=true;saved={...saved,...original,revision:saved.revision+1,analysis:null};body=saved
   }
   else if(path.includes('geojson'))body={type:'FeatureCollection',features:[]}
   else if(path.includes('timeseries'))body={dates:[],records:[]}
   await route.fulfill({contentType:'application/json',body:JSON.stringify(body)})
  })
  await page.goto('http://127.0.0.1:4175/app')
  await page.getByRole('button',{name:'Projetos de terrenos',exact:true}).click()
  await page.getByLabel('Retomar estudo').selectOption('1')
  await page.getByRole('button',{name:'Consultar revisão 2',exact:true}).click()
  await page.getByRole('heading',{name:'Conteúdo da revisão 2'}).waitFor()
  const zero=page.getByRole('row').filter({hasText:'Evidências técnicas · Declividade (%)'})
  assert.equal(await zero.getByRole('cell').nth(1).innerText(),'0')
  await page.getByText('Consultar resultados históricos (sem recálculo)',{exact:true}).click()
  await page.getByRole('heading',{name:'Diagnóstico de evidências técnicas'}).waitFor()
  await page.getByLabel('Nome do projeto').fill('Edição ainda não salva')
  assert.equal(await page.getByRole('button',{name:'Recuperar premissas desta revisão'}).isDisabled(),true)
  await page.getByRole('button',{name:'Salvar projeto',exact:true}).click()
  await page.getByRole('status').filter({hasText:'Projeto salvo'}).waitFor()
  await page.getByRole('button',{name:'Consultar revisão 2',exact:true}).click()
  await page.getByRole('heading',{name:'Conteúdo da revisão 2'}).waitFor()
  await page.setViewportSize({width:390,height:844})
  await page.waitForFunction(()=>document.querySelector('.sidebar').getBoundingClientRect().right<=0)
  await page.getByRole('heading',{name:'Conteúdo da revisão 2'}).scrollIntoViewIfNeeded()
  await page.screenshot({path:'/private/tmp/urbia-versions-mobile.png'})
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth))
  page.once('dialog',dialog=>dialog.dismiss())
  await page.getByRole('button',{name:'Recuperar premissas desta revisão'}).click()
  assert.equal(attempts,0)
  page.once('dialog',dialog=>dialog.accept())
  await page.getByRole('button',{name:'Recuperar premissas desta revisão'}).click()
  await page.getByRole('alert').filter({hasText:'Projeto alterado'}).waitFor()
  assert.equal(await page.getByLabel('Nome do projeto').inputValue(),'Edição ainda não salva')
  page.once('dialog',dialog=>dialog.accept())
  await page.getByRole('button',{name:'Recuperar premissas desta revisão'}).click()
  await page.getByRole('status').filter({hasText:'Premissas recuperadas em nova revisão'}).waitFor()
  assert.equal(await page.getByLabel('Nome do projeto').inputValue(),'Estudo original')
  assert.equal(saved.analysis,null)
  await page.getByText('Premissas recuperadas da revisão 2.',{exact:true}).waitFor()
  viewer=true
  await page.reload()
  await page.setViewportSize({width:1440,height:1000})
  await page.getByRole('button',{name:'Projetos de terrenos',exact:true}).click()
  await page.getByLabel('Retomar estudo').selectOption('1')
  await page.getByRole('button',{name:'Consultar revisão 2',exact:true}).click()
  await page.getByRole('heading',{name:'Conteúdo da revisão 2'}).waitFor()
  assert.equal(await page.getByRole('button',{name:'Recuperar premissas desta revisão'}).isDisabled(),true)
  assert.deepEqual(errors,[])
  console.log('Validated historical inputs/results, differences, zero preservation, unsaved guard, cancel, conflict, recovery, read-only access and mobile layout.')
  await context.close()
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exitCode=1})
