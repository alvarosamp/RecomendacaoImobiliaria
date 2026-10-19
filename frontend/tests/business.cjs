async function revealAuxiliary(page){const section=page.locator(".workspace-secondary");if(await section.count()&&!await section.evaluate(element=>element.open))await section.locator(":scope > summary").click()}
const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs')
;(async()=>{
 const business=JSON.parse(fs.readFileSync(process.env.URBIA_BUSINESS_FIXTURE||'/private/tmp/urbia-business-fixture.json','utf8'))
 const browser=await chromium.launch({channel:'chrome',headless:true})
 try{
  const context=await browser.newContext({viewport:{width:1440,height:1000},timezoneId:'America/Sao_Paulo'})
  await context.addInitScript(()=>localStorage.setItem('token','fixture'))
  const page=await context.newPage(),errors=[]
  page.on('pageerror',error=>errors.push(error.message))
  let saved=null
  await page.route('**/api/**',async route=>{
   const req=route.request(),path=new URL(req.url()).pathname
   let body=[]
   if(path==='/api/auth/me')body={id:1,name:'Teste',role:'empreendedor'}
   else if(path==='/api/scores')body=[{h3_id:'88a88c994bfffff',zona:'ZR'}]
   else if(path==='/api/projects'&&req.method()==='GET')body=saved?[saved,{id:2,name:'Alternativa sem dados',revision:1,can_edit:true,premises:{},analysis:null}]:[]
   else if(path==='/api/projects'||path==='/api/projects/1'){saved={...req.postDataJSON(),id:1,revision:(saved?.revision||0)+1,can_edit:true,analysis:null};body=saved}
   else if(path==='/api/projects/1/analyze'){saved={...saved,revision:saved.revision+1,analysis:{mode:'territorial',captured_at:new Date().toISOString(),business,legal:{status:'blocked',articles:[],sources:[]},concept:{scenarios:[]}}};body=saved}
   else if(path.endsWith('/history'))body={items:[],next_before_revision:null}
   else if(path.endsWith('/report'))return route.fulfill({contentType:'text/markdown',body:'# Localização comercial de teste'})
   else if(path.includes('geojson'))body={type:'FeatureCollection',features:[]}
   else if(path.includes('timeseries'))body={dates:[],records:[]}
   await route.fulfill({contentType:'application/json',body:JSON.stringify(body)})
  })
  await page.goto('http://127.0.0.1:4175/app')
  await revealAuxiliary(page)
  await page.getByRole('button',{name:'Iniciar análise'}).first().click()
  assert.equal(await page.getByLabel('Uso pretendido').inputValue(),'comercial')
  await page.getByLabel('Nome do projeto').fill('Localização de farmácia de teste')
  await page.getByLabel('Região de referência').selectOption('88a88c994bfffff')
  await page.getByRole('button',{name:'2. Premissas'}).click()
  assert.equal(await page.getByLabel('Incluir critérios de localização comercial').isChecked(),true)
  for(const [label,value] of Object.entries({'População mínima estimada na célula':'0','Referência de distância ao serviço (m)':'500','Data dos critérios comerciais':'2026-10-15','Justificativa dos critérios comerciais':'Hipótese a investigar'}))await page.getByLabel(label,{exact:true}).fill(value)
  await page.getByRole('button',{name:'Salvar projeto',exact:true}).click()
  await page.getByRole('status').filter({hasText:'Projeto salvo'}).waitFor()
  assert.equal(saved.business.minimum_population,0)
  await page.reload()
  await page.getByRole('button',{name:'Projetos de terrenos',exact:true}).click()
  await page.getByLabel('Retomar estudo').selectOption('1')
  await page.getByRole('button',{name:'2. Premissas'}).click()
  assert.equal(await page.getByLabel('População mínima estimada na célula').inputValue(),'0')
  await page.getByRole('button',{name:'3. Restrições e cenários'}).click()
  await page.getByRole('button',{name:'Salvar e calcular análise integrada'}).click()
  await page.getByRole('heading',{name:'Triagem de localização comercial'}).waitFor()
  await page.getByText('Estabelecimentos mapeados: 0',{exact:true}).waitFor()
  await page.getByText('A triagem legal indica bloqueio.',{exact:false}).waitFor()
  await page.getByText('Critérios e limites da triagem comercial',{exact:true}).click()
  await page.getByText('Processamento dos indicadores:',{exact:false}).waitFor()
  await page.setViewportSize({width:390,height:844})
  await page.waitForFunction(()=>document.querySelector('.sidebar').getBoundingClientRect().right<=0)
  await page.getByRole('heading',{name:'Triagem de localização comercial'}).scrollIntoViewIfNeeded()
  await page.screenshot({path:'/private/tmp/urbia-business-mobile.png'})
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth))
  assert.ok(await page.evaluate(()=>document.querySelector('.financial-results').getBoundingClientRect().right<=window.innerWidth))
  await page.getByRole('button',{name:'4. Relatório'}).click()
  const download=page.waitForEvent('download')
  await page.getByRole('button',{name:'Salvar e baixar relatório (.md)'}).click()
  assert.equal((await download).suggestedFilename(),'urbia-projeto-1.md')
  await page.setViewportSize({width:1440,height:1000})
  await page.getByRole('button',{name:'Comparar estudos',exact:true}).click()
  await page.getByLabel('Estudo 1',{exact:true}).selectOption('1')
  await page.getByLabel('Estudo 2',{exact:true}).selectOption('2')
  const populationRow=page.getByRole('row').filter({has:page.getByRole('cell',{name:'Critério de população mínima',exact:true})})
  assert.equal(await populationRow.getByRole('cell').nth(1).innerText(),'0')
  const serviceRow=page.getByRole('row').filter({has:page.getByRole('cell',{name:'Estabelecimentos do setor mapeados',exact:true})})
  assert.equal(await serviceRow.getByRole('cell').nth(1).innerText(),'0')
  assert.equal(await serviceRow.getByRole('cell').nth(2).innerText(),'Não disponível')
  const comparison=page.waitForEvent('download')
  await page.getByRole('button',{name:'Baixar comparação (.md)'}).click()
  const stream=await (await comparison).createReadStream(),chunks=[]
  for await(const chunk of stream)chunks.push(chunk)
  assert.ok(Buffer.concat(chunks).toString('utf8').includes('Critério de população mínima: 0'))
  assert.deepEqual(errors,[])
  console.log('Validated commercial defaults, zero criteria, persistence, legal block, results, report, comparison export and mobile layout.')
  await context.close()
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exitCode=1})
