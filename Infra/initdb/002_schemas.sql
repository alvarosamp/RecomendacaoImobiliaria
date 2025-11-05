-- Series temprais, acessibilidade, features, scores
-- Séries de índices espectrais por H3 e data (NDVI/NDBI/etc.)

-- ensure schema exists
IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = N'geo')
BEGIN
    EXEC('CREATE SCHEMA geo');
END
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.tables t
    JOIN sys.schemas s ON t.schema_id = s.schema_id
    WHERE t.name = 'indices' AND s.name = 'geo'
)
BEGIN
CREATE TABLE geo.indices (
  h3_id   NVARCHAR(100) NOT NULL,
  [date]  DATE NOT NULL,
  ndvi    FLOAT NULL,
  ndbi    FLOAT NULL,
  bai     FLOAT NULL,
  cloud_pct FLOAT NULL,
  CONSTRAINT PK_indices PRIMARY KEY (h3_id, [date]),
  CONSTRAINT fk_indices_h3 FOREIGN KEY (h3_id) REFERENCES geo.grid_h3(h3_id) ON DELETE CASCADE
);
END
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes i
    JOIN sys.tables t ON i.object_id = t.object_id
    JOIN sys.schemas s ON t.schema_id = s.schema_id
    WHERE i.name = 'idx_indices_h3_date' AND t.name = 'indices' AND s.name = 'geo'
)
BEGIN
CREATE INDEX idx_indices_h3_date ON geo.indices (h3_id, [date]);
END
GO

-- Acessibilidade / Distâncias até POIs (métricas estáticas por H3)
IF NOT EXISTS (
    SELECT 1 FROM sys.tables t
    JOIN sys.schemas s ON t.schema_id = s.schema_id
    WHERE t.name = 'access' AND s.name = 'geo'
)
BEGIN
CREATE TABLE geo.access (
  h3_id  NVARCHAR(100) NOT NULL,
  metric NVARCHAR(200) NOT NULL,              -- ex: dist_min_supermarket_m
  value  FLOAT NOT NULL,
  CONSTRAINT PK_access PRIMARY KEY (h3_id, metric),
  CONSTRAINT fk_access_h3 FOREIGN KEY (h3_id) REFERENCES geo.grid_h3(h3_id) ON DELETE CASCADE
);
END
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes i
    JOIN sys.tables t ON i.object_id = t.object_id
    JOIN sys.schemas s ON t.schema_id = s.schema_id
    WHERE i.name = 'idx_access_metric' AND t.name = 'access' AND s.name = 'geo'
)
BEGIN
CREATE INDEX idx_access_metric ON geo.access (metric);
END
GO

-- Features agregadas por H3 (últimas janelas/estatísticas)
IF NOT EXISTS (
    SELECT 1 FROM sys.tables t
    JOIN sys.schemas s ON t.schema_id = s.schema_id
    WHERE t.name = 'features' AND s.name = 'geo'
)
BEGIN
CREATE TABLE geo.features (
  h3_id NVARCHAR(100) PRIMARY KEY,
  -- exemplos de colunas; serão expandidas conforme pipeline
  ndvi_mean_90      FLOAT NULL,
  ndvi_slope_180    FLOAT NULL,
  ndbi_mean_90      FLOAT NULL,
  ndbi_slope_180    FLOAT NULL,
  poi_supermarket_cnt INT NULL,
  poi_pharmacy_cnt    INT NULL,
  poi_school_cnt      INT NULL,
  dist_min_supermarket_m FLOAT NULL,
  dist_min_pharmacy_m    FLOAT NULL,
  dist_min_school_m      FLOAT NULL,
  CONSTRAINT fk_features_h3 FOREIGN KEY (h3_id) REFERENCES geo.grid_h3(h3_id) ON DELETE CASCADE
);
END
GO

-- Scores de recomendação por H3 (residencial/comercial)
IF NOT EXISTS (
    SELECT 1 FROM sys.tables t
    JOIN sys.schemas s ON t.schema_id = s.schema_id
    WHERE t.name = 'scores' AND s.name = 'geo'
)
BEGIN
CREATE TABLE geo.scores (
  h3_id NVARCHAR(100) PRIMARY KEY,
  score_residencial FLOAT NULL,
  score_comercial   FLOAT NULL,
  explain_json      NVARCHAR(MAX) NULL,           -- guarda decomposição do score / flags de conformidade (JSON stored as text)
  updated_at        DATETIME2 DEFAULT SYSUTCDATETIME(),
  CONSTRAINT fk_scores_h3 FOREIGN KEY (h3_id) REFERENCES geo.grid_h3(h3_id) ON DELETE CASCADE
);
END
GO
