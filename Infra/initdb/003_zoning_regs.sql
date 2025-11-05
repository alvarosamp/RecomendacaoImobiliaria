--Zoneamento (espacial) base para o RAG
-- Zoneamento: polígonos com atributos urbanísticos
CREATE TABLE IF NOT EXISTS geo.zoning (
  id SERIAL PRIMARY KEY,
  zona TEXT NOT NULL,                        -- ex: ZC-3
  usos_permitidos TEXT[],                    -- ex: {'residencial','comercio_varejista_alimentos'}
  usos_condicionados TEXT[],
  usos_vetados TEXT[],
  gabarito INT,                              -- altura (nº de pavimentos, se aplicável)
  coef_aprov NUMERIC,                        -- coeficiente de aproveitamento
  recuos JSONB,                              -- {frontal: x, lateral: y, fundo: z}
  observacoes TEXT,
  geom geometry(MultiPolygon,4326) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_zoning_gist ON geo.zoning USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_zoning_zona ON geo.zoning (zona);

-- Camadas de restrição/overlay (ex.: APP, UC, ZEIS, eixos especiais)
CREATE TABLE IF NOT EXISTS geo.overlays (
  id SERIAL PRIMARY KEY,
  tipo TEXT NOT NULL,                        -- ex: 'APP', 'UC', 'Eixo_Adensamento'
  regras JSONB,                              -- regras específicas desta camada
  geom geometry(MultiPolygon,4326) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_overlays_gist ON geo.overlays USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_overlays_tipo ON geo.overlays (tipo);

-- Base textual para RAG (usa pgvector para embeddings, se disponível)
CREATE EXTENSION IF NOT EXISTS vector;       -- Postgres 15+: extensão pgvector
-- Ajuste a dimensão (ex.: 768 para MiniLM, 1024/1536 p/ outros modelos)
CREATE TABLE IF NOT EXISTS public.regs (
  id SERIAL PRIMARY KEY,
  doc TEXT NOT NULL,                         -- ex: "Plano Diretor 2023"
  artigo TEXT,                               -- ex: "Art. 42, §1º"
  sumario TEXT,                              -- breve resumo
  texto TEXT NOT NULL,                       -- trecho pleno
  url TEXT,                                  -- link do PDF/fonte
  embedding VECTOR(768)                      -- vetor do trecho (opcional, p/ busca semântica)
);
CREATE INDEX IF NOT EXISTS idx_regs_doc ON public.regs (doc);
-- se for usar busca vetorial: crie índice ivfflat (após popular a tabela)
-- CREATE INDEX IF NOT EXISTS idx_regs_embed ON public.regs USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);
