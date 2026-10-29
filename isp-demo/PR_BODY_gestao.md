## O que muda

Adiciona o menu **Gestão** ao protótipo ISP (`isp-demo/`), com quatro ferramentas sobre o recorte de cidade/setor:

- **Receita e base:** receita recorrente faturável, receita em risco (suspensos ocupam porta mas não faturam), ticket médio e churn mensal por cidade e plano.
- **Território e penetração:** cruza células de 200 m do IBGE/CNEFE 2022 (real), instalações (fictícias) e áreas de mudança do Sentinel-2 2024→2025 (real). Classifica células em campanha comercial, ampliar capacidade ou estudar expansão; abre o planejador no centro da célula; exporta CSV.
- **Capacidade das CTOs:** tendência linear de 90 dias para estimar o esgotamento de portas; pedidos pendentes elevam o risco.
- **Ordens de serviço:** 215 ordens geradas do retrato, com SLA por prioridade, quadro por situação, distribuição automática balanceada por cidade, ordens manuais (também pelo detalhe de CTO/instalação), exportação CSV e roteiro do dia (críticas primeiro, depois vizinho mais próximo).

## Por quê

O protótipo já tinha geografia, satélite, IBGE e planejamento de rotas, mas nenhuma visão de gestão da operação. Este módulo junta essas camadas em decisões de receita, território, capacidade e equipe de campo.

## Para o revisor

- Motor de cálculo puro e sem dependências em `web/management-engine.js`, coberto por `test_management.cjs` (`node --test test_management.cjs`).
- Alterações nas ordens ficam **somente no `localStorage`** do navegador; não há backend, contas nem trilha de auditoria.
- Roteiro em linha reta, não viário. Receita e ordens derivam da operação fictícia.
- Esta branch parte de `codex/urbia-isp-vercel`, ainda não incorporada à `main`; contra a `main`, o diff inclui também os commits ISP anteriores. O commit deste módulo é o último.

## Verificação

- `node --test test_management.cjs test_inspection.cjs`: 16/16.
- `PYTHONUTF8=1 python -m unittest test_simulation test_planner test_knowledge test_vercel`: 26/27. A falha é anterior a esta mudança: `test_vercel.py` faz `os.chdir('/tmp')`, que não existe no Windows.
- Testado no navegador: as quatro abas, envio para o planejador e cálculo, distribuição automática, persistência após recarregar e largura de celular.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
