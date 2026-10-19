const { chromium } = require('playwright')
const assert = require('node:assert/strict')
;(async () => {
 const browser = await chromium.launch({channel:'chrome', headless:true})
 try {
  const context = await browser.newContext({viewport:{width:1440,height:1000},timezoneId:'America/Sao_Paulo'})
  await context.addInitScript(() => localStorage.setItem('token','fixture'))
  const page = await context.newPage(), errors=[]
  page.on('pageerror', e=>errors.push(e.message)); page.on('dialog', d=>d.accept())
  let teams=[], members=[{user_id:1,name:'Responsável',email:'owner@test.local',role:'owner'}], reader=false
  await page.route('**/api/**', async route=>{
   const req=route.request(), path=new URL(req.url()).pathname
   let body=[]
   if(path.endsWith('/history')) body={items:[],next_before_revision:null}
   else if(path==='/api/auth/me') body={id:1,name:'Teste',role:'incorporadora'}
   else if(path==='/api/organizations' && req.method()==='POST') {body={id:1,name:req.postDataJSON().name,role:'owner'};teams=[body]}
   else if(path==='/api/organizations') body=teams
   else if(path==='/api/organizations/1/members' && req.method()==='POST') {body={user_id:2,name:'Colega',email:req.postDataJSON().email,role:req.postDataJSON().role};members.push(body)}
   else if(path==='/api/organizations/1/members') body=members
   else if(path==='/api/organizations/1/members/2' && req.method()==='PATCH') {members[1].role=req.postDataJSON().role;body=members[1]}
   else if(path==='/api/organizations/1/members/2' && req.method()==='DELETE') {members=members.filter(m=>m.user_id!==2);return route.fulfill({status:204})}
   else if(path==='/api/projects' && reader) body=[{id:9,name:'Estudo de leitura',revision:1,organization_id:1,can_edit:false,h3_id:null,intended_use:'residencial',premises:{lotArea:300,frontage:10,buildArea:165,floors:2,typology:'casa',finish:'medio'},notes:'',analysis:null}]
   else if(path==='/api/projects/9/report') return route.fulfill({contentType:'text/markdown',body:'# Leitura'})
   else if(path.includes('geojson')) body={type:'FeatureCollection',features:[]}
   await route.fulfill({contentType:'application/json',body:JSON.stringify(body)})
  })
  await page.goto('http://127.0.0.1:4175/app')
  await page.getByRole('button',{name:'Equipes e acesso'}).click()
  await page.getByLabel('Nome da nova equipe').fill('Equipe urbanismo')
  await page.getByRole('button',{name:'Criar equipe'}).click()
  await page.getByRole('heading',{name:'Equipe urbanismo'}).waitFor()
  await page.getByLabel('Email de uma conta cadastrada').fill('colleague@test.local')
  await page.getByRole('button',{name:'Adicionar membro'}).click()
  await page.getByLabel('Acesso de Colega').selectOption('editor')
  await page.getByRole('status').filter({hasText:'Acesso atualizado'}).waitFor()
  assert.equal(members[1].role,'editor')
  await page.screenshot({path:'/private/tmp/urbia-teams-desktop.png',fullPage:true})
  await page.getByRole('button',{name:'Remover',exact:true}).click()
  await page.getByRole('status').filter({hasText:'Membro removido'}).waitFor()
  assert.equal(members.length,1)
  reader=true; teams[0].role='viewer'
  await page.getByRole('button',{name:'Projetos de terrenos'}).click()
  await page.getByLabel('Retomar estudo').selectOption('9')
  assert.equal(await page.getByRole('button',{name:'Salvar projeto',exact:true}).isDisabled(),true)
  assert.equal(await page.getByLabel('Nome do projeto').isDisabled(),true)
  await page.getByRole('button',{name:'3. Restrições e cenários'}).click()
  assert.equal(await page.getByRole('button',{name:'Salvar e calcular análise integrada'}).isDisabled(),true)
  await page.getByRole('button',{name:'4. Relatório'}).click()
  const download=page.waitForEvent('download')
  await page.getByRole('button',{name:'Baixar relatório (.md)',exact:true}).click()
  assert.equal((await download).suggestedFilename(),'urbia-projeto-9.md')
  await page.setViewportSize({width:390,height:844})
  await page.waitForFunction(()=>document.querySelector('.sidebar').getBoundingClientRect().right<=0)
  await page.screenshot({path:'/private/tmp/urbia-team-reader-mobile.png',fullPage:true})
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth))
  assert.deepEqual(errors,[])
  console.log('Validated team creation, membership, roles, removal and read-only study/export.')
  await context.close()
 } finally {await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1})
