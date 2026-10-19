// Real local Docker smoke check. No network/API mocks and no existing account changes.
const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto')
const BASE=process.env.URBIA_PRESENTATION_URL||'http://127.0.0.1:18088'
const OUTPUT=process.env.URBIA_SCREENSHOTS||'/private/tmp/urbia-presentation'
;(async()=>{
 fs.mkdirSync(OUTPUT,{recursive:true})
 const browser=await chromium.launch({channel:'chrome',headless:true})
 try{
  const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'})
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message))
  await page.goto(BASE);await page.getByRole('heading',{level:1}).waitFor();await page.screenshot({path:path.join(OUTPUT,'landing-desktop.png'),fullPage:true})
  assert.equal(await page.locator('.environment-card').count(),6)
  for(const width of [390,768]){
   await page.setViewportSize({width,height:844});await page.waitForFunction(()=>document.documentElement.scrollWidth<=innerWidth,null,{timeout:5000})
   await page.screenshot({path:path.join(OUTPUT,`landing-${width}.png`),fullPage:true})
  }
  await page.setViewportSize({width:1440,height:1000})
  const email=`presentation-${Date.now()}@test.local`,password=crypto.randomBytes(20).toString('hex')
  const registered=await context.request.post(BASE+'/api/auth/register',{data:{name:'Verificação visual',email,password,profile:'incorporadora'}})
  assert.equal(registered.status(),200,await registered.text())
  await page.goto(BASE+'/login');await page.screenshot({path:path.join(OUTPUT,'login.png'),fullPage:true})
  await page.locator('input[type=email]').fill(email);await page.locator('input[type=password]').fill(password);await page.getByRole('button',{name:'Acessar plataforma',exact:true}).click()
  const journeys=[['incorporadora','incorpora','Comparar propostas'],['construtora','obras','Preparar investigação'],['investidor','invest','Comparar investimentos'],['corretor','mercado','Apresentar imóvel'],['empreendedor','negocios','Comparar pontos'],['governo','governo','Priorizar visitas']]
  for(const [profile,kind,action] of journeys){
   await page.getByLabel('Modo de trabalho').selectOption(profile)
   await page.getByRole('button',{name:action,exact:true}).waitFor()
   await page.screenshot({path:path.join(OUTPUT,`${kind}-home.png`),fullPage:true})
   await page.setViewportSize({width:390,height:844});await page.waitForFunction(()=>document.documentElement.scrollWidth<=innerWidth,null,{timeout:5000})
   await page.screenshot({path:path.join(OUTPUT,`${kind}-home-mobile.png`),fullPage:true});await page.setViewportSize({width:1440,height:1000})
   await page.getByRole('button',{name:action,exact:true}).click()
   await page.getByRole('button',{name:'Conhecer exemplo demonstrativo',exact:true}).click();await page.getByLabel('Síntese da decisão',{exact:true}).waitFor()
   await page.screenshot({path:path.join(OUTPUT,`${kind}-result.png`),fullPage:true})
   const popupPromise=page.waitForEvent('popup');await page.getByRole('button',{name:'Abrir relatório para PDF',exact:true}).click();const report=await popupPromise
   await report.getByRole('heading',{name:'O que encontramos',exact:true}).waitFor();await report.close()
   await page.setViewportSize({width:390,height:844});await page.waitForFunction(()=>document.documentElement.scrollWidth<=innerWidth,null,{timeout:5000})
   await page.screenshot({path:path.join(OUTPUT,`${kind}-result-mobile.png`),fullPage:true});await page.setViewportSize({width:1440,height:1000})
   console.log('PASS: '+kind+' — home, mobile, example, report')
  }
  assert.deepEqual(errors,[])
  console.log('PASS: six environments, login, reports, mobile layouts and no JavaScript errors')
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1})
