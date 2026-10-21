# Sistema imobiliário na Vercel

## Demonstração pública publicada

Endereço: https://urbia-imobiliario-demo.vercel.app/app

Projeto `urbia-imobiliario-demo`, equipe `teste-tor-s-projects`. Acesso público,
sem login do aplicativo ou proteção de login da Vercel. O projeto ISP é separado.
Os seis perfis podem ser escolhidos no seletor “Modo de trabalho”.

A apresentação usa dados fictícios. Estudos, equipes e contatos são guardados
somente no navegador do visitante; não existe compartilhamento real entre pessoas.
A função Python calcula as seis jornadas, conceitos e premissas de projetos usando
os mesmos módulos analíticos do repositório. Não conecta banco nem carrega segredos.
Preços e scores territoriais são exemplos, sem inferência de mercado real.
A imagem do estúdio é um esquema ilustrativo, identificado como tal; não usa IA.
Coletas, verificações legais espaciais e integrações de produção não são executadas.

Para atualizar a demonstração, a partir da raiz do repositório:

```powershell
python scripts/package_vercel_demo.py --examples
npm --prefix frontend run build:demo
python scripts/package_vercel_demo.py
Set-Location tmp/vercel-imobiliario
vercel deploy --prod --yes --project urbia-imobiliario-demo --scope teste-tor-s-projects
```

O empacotador inclui somente assets compilados e módulos Python explicitamente
selecionados. `.env*`, credenciais, banco, modelos e dados privados ficam fora.
Não envie a raiz inteira do repositório. A autenticação da versão normal permanece
ativa: `npm run build` não habilita a demonstração pública.

Validação no endereço público:

```powershell
$env:URBIA_UI_URL = 'https://urbia-imobiliario-demo.vercel.app'
node frontend/tests/public-demo.cjs
```

O teste requer Playwright e Chrome. Para verificar o pacote localmente, execute
`python scripts/serve_vercel_demo.py` e abra `http://127.0.0.1:4188/app`.

## Aplicação com dados e serviços reais

O frontend React/Vite pode ser publicado com Root Directory `frontend`,
Framework `Vite`, build `npm run build` e saída `dist`.
Use um projeto separado de `urbia-isp`, que contém outro produto.

Antes de publicar a aplicação funcional:

1. Hospede a API Python com PostGIS e volumes persistentes. A configuração
   `docker-compose.partner-demo.yml` fornece uma referência para servidor Docker.
2. Configure HTTPS para a API e confirme `/health/ready`.
3. Na Vercel, configure `VITE_API_BASE_URL=https://DOMINIO-DA-API/api`.
   Essa variável é pública e deve conter apenas a URL, nunca credenciais.
4. Configure `CORS_ORIGINS` na API com o domínio HTTPS do frontend.
5. Faça o deploy e verifique cadastro, login, mapa e relatórios.

Sem `VITE_API_BASE_URL`, o frontend mantém `/api`, usado pelo proxy Docker local.
Alterar a variável exige um novo build. Publicar apenas os arquivos estáticos
sem uma API disponível não disponibiliza o sistema completo.

O Docker Desktop local depende atualmente de uma unidade D indisponível.
