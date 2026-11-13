// Every audience guide must open its own journey, even from a different account workspace.
const {chromium}=require('playwright'),assert=require('node:assert/strict'),crypto=require('node:crypto'),fs=require('node:fs')
const BASE=process.env.URBIA_PRESENTATION_URL||'http://127.0.0.1:18088'
;(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true})
 try{
  const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'})
  const email=`role-help-${Date.now()}@test.local`,password=crypto.randomBytes(20).toString('hex')
  assert.equal((await context.request.post(BASE+'/api/auth/register',{data:{name:'Teste de guias por atividade',email,password,profile:'incorporadora'}})).status(),200)
  const token=(await(await context.request.post(BASE+'/api/auth/login',{data:{email,password}})).json()).access_token
  await context.addInitScript(token=>localStorage.setItem('token',token),token)
  const page=await context.newPage(),errors=[];let profileWrites=0
  page.on('pageerror',error=>errors.push(error.message));page.on('request',request=>{if(new URL(request.url()).pathname==='/api/auth/me/profile'&&request.method()==='PATCH')profileWrites++})
  await page.goto(BASE+'/app');fs.mkdirSync('/private/tmp/urbia-role-help',{recursive:true})
  const guide=page.getByRole('dialog',{name:'Como usar a Urbia',exact:true})
  const roles=[['Investidor','invest','investidor','Capital necessário','Casa A'],['Corretor','mercado','corretor','Comparável','520 mil'],['Incorporadora','incorpora','incorporadora','Área vendável','200 m²'],['Construtora','obras','construtora','Evidência','água'],['Empreendedor','negocios','empreendedor','Concorrentes observados','3.300'],['Governo','governo','governo','Capacidade escolar','2.500 m']]
  for(const [label,kind,role,term,exampleText] of roles){
   await page.getByRole('button',{name:'Como usar',exact:true}).click()
   await guide.waitFor()
   const chooser=guide.getByRole('group',{name:'Como usar por atividade',exact:true})
   assert.equal(await chooser.getByRole('button').count(),6)
   await chooser.getByRole('button',{name:label,exact:true}).click()
   await guide.getByRole('heading',{name:'Como usar: '+label,exact:true}).waitFor()
   assert.equal(await chooser.getByRole('button',{name:label,exact:true}).getAttribute('aria-pressed'),'true')
   assert.equal(await guide.locator('.help-activity-content').getAttribute('data-profile'),role)
   assert.equal(await guide.locator('.help-steps > li').count(),4)
   await guide.locator('.help-field-glossary > summary').click();await guide.locator('.help-field-glossary dt').filter({hasText:term}).waitFor()
   await guide.locator('.help-worked-example > summary').click();assert.ok((await guide.locator('.help-worked-example').innerText()).includes(exampleText))
   await guide.evaluate(element=>element.scrollTop=0)
   await page.screenshot({path:`/private/tmp/urbia-role-help/${kind}.png`})
   const createdPromise=page.waitForResponse(response=>new URL(response.url()).pathname==='/api/case-demos/'+kind&&response.request().method()==='POST')
   await guide.getByRole('button',{name:'Ver exemplo preenchido',exact:true}).click()
   const response=await createdPromise;assert.equal(response.status(),201);const saved=await response.json();assert.equal(saved.kind,kind);assert.equal(saved.demonstration,true)
   await page.getByLabel('Síntese da decisão',{exact:true}).waitFor();assert.equal(await page.locator('.decision-case').getAttribute('data-kind'),kind)
   assert.equal(await page.getByLabel('Modo de trabalho').inputValue(),'incorporadora')
   await page.getByRole('button',{name:'Como usar esta análise',exact:true}).click()
   await guide.getByRole('heading',{name:'Como usar: '+label,exact:true}).waitFor()
   await guide.getByRole('button',{name:/^Começar em Urbia /}).click()
   await page.getByLabel('Nome da análise',{exact:true}).waitFor()
   assert.equal(await page.locator('.decision-case').getAttribute('data-kind'),kind)
   assert.equal(await page.locator('.decision-case').getAttribute('data-case-id'),'new')
   assert.equal(await page.getByLabel('Nome da análise',{exact:true}).inputValue(),'')
   console.log('PASS: '+label+' — specific instructions, glossary, worked example and correct demo/new-case shortcuts')
  }
  await page.getByRole('button',{name:'Como usar esta análise',exact:true}).click()
  await page.setViewportSize({width:390,height:844});await guide.evaluate(element=>element.scrollTop=0)
  assert.ok(await guide.evaluate(element=>element.scrollWidth<=element.clientWidth+1),'No horizontal overflow in guide')
  await page.screenshot({path:'/private/tmp/urbia-role-help/mobile.png'})
  await page.keyboard.press('Escape');await guide.waitFor({state:'detached'})
  assert.equal(profileWrites,0,'Reading guides and choosing their journeys does not change the account workspace')
  assert.deepEqual(errors,[])
  console.log('PASS: contextual guide, mobile, Escape, no workspace mutation and no JavaScript errors')
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exitCode=1})
