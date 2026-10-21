async function revealAuxiliary(page){const section=page.locator(".workspace-secondary");if(await section.count()&&!await section.evaluate(element=>element.open))await section.locator(":scope > summary").click()}
// Run against `vite preview --port 4175`; requires Playwright in NODE_PATH.
const { chromium } = require('playwright')
const assert = require('node:assert/strict')
const base = process.env.URBIA_UI_URL || 'http://127.0.0.1:4175'
const cell = '88a88c994bfffff'
const names = { investidor: 'Urbia Invest', corretor: 'Urbia Mercado', incorporadora: 'Urbia Incorpora', governo: 'Urbia Governo' }
;(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'chrome', args: ['--enable-unsafe-swiftshader'] })
  try {
    for (const role of Object.keys(names)) {
      const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } })
      await context.addInitScript(() => localStorage.setItem('token', 'ui-test-fixture'))
      const page = await context.newPage()
      const errors = []
      page.on('pageerror', error => errors.push(error.message))
      let stored = null
      await page.route('**/api/**', async route => {
        const request = route.request(), path = new URL(request.url()).pathname
        let body
        if (path.endsWith('/history')) body = { items: [], next_before_revision: null }
        else if (path === '/api/auth/me') body = { id: 1, name: 'Teste', role, is_admin: false }
        else if (path === '/api/scores') body = [{ h3_id: cell, zona: 'ZR', score_residencial: 70, score_comercial: 35, risk_level: 'baixo', confidence: .6, explainability: [] }]
        else if (path === '/api/government/diagnosis') {
          const params = new URL(request.url()).searchParams
          body = { service: params.get('service'), service_label: 'Escolas', target_distance_m: Number(params.get('target_distance_m')), captured_at: new Date().toISOString(), methodology: 'triagem_acesso_v1', formula: 'Fórmula de teste', limitations: ['Capacidade e cobertura pública não verificadas.'], sources: [], summary: { ranked: 1, high_priority: 1, pending: 1 }, report_markdown: '# Diagnóstico de teste', rows: [{ h3_id: cell, neighborhood: 'Região de teste', population: 100, population_basis: 'estimate', count: 0, distance_m: 3000, priority: 'alta', investigation_score: 100, reason: 'Ausência no recorte e distância; capacidade não verificada.' }, { h3_id: 'missing', population: null, count: null, distance_m: null, priority: 'dados_pendentes', investigation_score: null, reason: 'População indisponível' }] }
        }
        else if (path === '/api/projects' && request.method() === 'GET') body = stored ? [stored] : []
        else if (path === '/api/projects' || (path === '/api/projects/1' && request.method() === 'PATCH')) {
          stored = { ...request.postDataJSON(), id: 1, revision: (stored?.revision || 0) + 1, analysis: null, updated_at: new Date().toISOString() }; body = stored
        } else if (path === '/api/projects/1/analyze') {
          stored = { ...stored, revision: stored.revision + 1, analysis: { captured_at: new Date().toISOString(), legal: { status: 'conditioned', notes: 'Teste: confirmar restrições', sources: [], articles: [], spatial_overlays_verified: false }, concept: { scenarios: [{ id: 'casa', label: 'Casa', buildArea: 165, cost: 500000, months: 12, roiYear: 5, viabilityScore: 60 }] } } }; body = stored
        } else if (path === '/api/projects/1/report') return route.fulfill({ contentType: 'text/markdown', body: '# Relatório do estudo de teste' })
        else if (path.includes('geojson')) body = { type: 'FeatureCollection', features: [] }
        else if (path.includes('timeseries')) body = { dates: [], records: [] }
        else body = []
        await route.fulfill({ contentType: 'application/json', body: JSON.stringify(body) })
      })
      await page.goto(base + '/app')
      await page.getByText(names[role], { exact: true }).waitFor()
      await revealAuxiliary(page)
      assert.equal(await page.getByRole('button', { name: 'Iniciar análise' }).count(), 2)
      if (role === 'incorporadora') {
        await revealAuxiliary(page)
        await page.getByRole('button', { name: 'Iniciar análise' }).first().click()
        await page.getByRole('button', { name: '2. Premissas' }).click()
        await page.getByLabel('Nome do projeto').fill('Estudo UI persistente')
        await page.getByLabel('Região de referência').selectOption(cell)
        await page.getByLabel('Área informada do lote (m²)').fill('450')
        await page.getByRole('button', { name: 'Salvar projeto', exact: true }).click()
        await page.getByRole('status').filter({ hasText: 'Projeto salvo' }).waitFor()
        assert.equal(stored.premises.lotArea, 450)
        await page.reload()
        await page.getByRole('button', { name: 'Projetos de terrenos' }).click()
        await page.getByLabel('Retomar estudo').selectOption('1')
        await page.getByRole('button', { name: '2. Premissas' }).click()
        assert.equal(await page.getByLabel('Área informada do lote (m²)').inputValue(), '450')
        await page.screenshot({ path: '/private/tmp/urbia-study-desktop.png', fullPage: true })
        await page.getByRole('button', { name: '3. Restrições e cenários' }).click()
        await page.getByRole('button', { name: 'Salvar e calcular análise integrada' }).click()
        await page.getByRole('heading', { name: 'Triagem urbanística: Condicionado' }).waitFor()
        await page.getByRole('button', { name: '4. Relatório' }).click()
        const downloaded = page.waitForEvent('download')
        await page.getByRole('button', { name: 'Salvar e baixar relatório (.md)' }).click()
        assert.equal((await downloaded).suggestedFilename(), 'urbia-projeto-1.md')
        await page.setViewportSize({ width: 390, height: 844 })
        await page.waitForFunction(() => document.querySelector('.sidebar').getBoundingClientRect().right <= 0)
        await page.screenshot({ path: '/private/tmp/urbia-study-mobile.png', fullPage: true })
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), 'Mobile content overflows')
        await page.setViewportSize({ width: 1440, height: 1000 })
        await page.getByRole('button', { name: 'Início', exact: true }).click()
        await revealAuxiliary(page)
        await page.getByRole('button', { name: 'Iniciar análise' }).nth(1).click()
        await page.getByRole('navigation', { name: /^Etapas:/ }).waitFor()
        await page.getByRole('button', { name: 'Voltar ao início' }).click()
      } else if (role === 'governo') {
        await revealAuxiliary(page)
        await page.getByRole('button', { name: 'Iniciar análise' }).first().click()
        await page.getByRole('button', { name: 'Gerar diagnóstico' }).click()
        await page.getByRole('heading', { name: '1 regiões ranqueadas' }).waitFor()
        await page.getByLabel('Filtrar prioridade').selectOption('dados_pendentes')
        await page.getByRole('cell', { name: 'População indisponível' }).waitFor()
        await page.getByLabel('Filtrar prioridade').selectOption('')
        await page.getByText('Critérios, fontes e limitações').click()
        await page.screenshot({ path: '/private/tmp/urbia-government-desktop.png', fullPage: true })
        await page.getByLabel('Referência exploratória de distância (m)').fill('1000')
        await page.getByRole('status').filter({ hasText: 'Parâmetros alterados' }).waitFor()
        assert.equal(await page.getByRole('button', { name: 'Baixar diagnóstico (.md)' }).count(), 0)
        await page.getByRole('button', { name: 'Gerar diagnóstico' }).click()
        await page.getByRole('button', { name: 'Baixar diagnóstico (.md)' }).waitFor()
        const download = page.waitForEvent('download')
        await page.getByRole('button', { name: 'Baixar diagnóstico (.md)' }).click()
        assert.equal((await download).suggestedFilename(), 'urbia-diagnostico-schools.md')
        await page.setViewportSize({ width: 390, height: 844 })
        await page.waitForFunction(() => document.querySelector('.sidebar').getBoundingClientRect().right <= 0)
        await page.screenshot({ path: '/private/tmp/urbia-government-mobile.png', fullPage: true })
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), 'Government mobile overflows')
        await page.setViewportSize({ width: 1440, height: 1000 })
        await page.getByRole('button', { name: 'Início', exact: true }).click()
        await revealAuxiliary(page)
        await page.getByRole('button', { name: 'Iniciar análise' }).nth(1).click()
        await page.getByRole('navigation', { name: /^Etapas:/ }).waitFor()
      } else {
        for (let index = 0; index < 2; index++) {
          await revealAuxiliary(page)
          await page.getByRole('button', { name: 'Iniciar análise' }).nth(index).click()
          await page.getByRole('navigation', { name: /^Etapas:/ }).waitFor()
          await page.getByRole('button', { name: 'Voltar ao início' }).click()
          await page.getByText(names[role], { exact: true }).waitFor()
        }
      }
      assert.deepEqual(errors, [], `${role}: browser exceptions`)
      console.log('Validated workspace:', role)
      await context.close()
    }
  } finally { await browser.close() }
})().catch(error => { console.error(error); process.exitCode = 1 })
