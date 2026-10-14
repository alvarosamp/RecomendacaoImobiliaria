-- Dashboard e ETL.
-- POIs por H3 (contagem por subcategoria).
CREATE MATERIALIZED VIEW IF NOT EXISTS geo.v_pois_by_h3 AS
SELECT g.h3_id,
       p.subcategory,
       COUNT(*) AS poi_count
FROM geo.grid_h3 g
JOIN geo.osm_pois p
  ON ST_Contains(g.geom, p.geom)
GROUP BY g.h3_id, p.subcategory;
CREATE INDEX IF NOT EXISTS idx_v_pois_by_h3 ON geo.v_pois_by_h3 (h3_id);

-- Ultimo NDVI por H3 para mapas snapshot.
CREATE MATERIALIZED VIEW IF NOT EXISTS geo.v_ndvi_latest AS
SELECT i.h3_id,
       i.ndvi,
       i.date
FROM geo.indices i
JOIN (
  SELECT h3_id, MAX(date) AS max_date
  FROM geo.indices
  WHERE ndvi IS NOT NULL
  GROUP BY h3_id
) m ON i.h3_id = m.h3_id AND i.date = m.max_date;
CREATE INDEX IF NOT EXISTS idx_v_ndvi_latest_h3 ON geo.v_ndvi_latest (h3_id);

-- Elegibilidade por uso espacial para filtros rapidos.
CREATE MATERIALIZED VIEW IF NOT EXISTS geo.v_h3_zona AS
SELECT g.h3_id,
       z.zona,
       z.usos_permitidos,
       z.usos_condicionados,
       z.usos_vetados
FROM geo.grid_h3 g
JOIN geo.zoning z ON ST_Intersects(g.geom, z.geom);
CREATE INDEX IF NOT EXISTS idx_v_h3_zona_h3 ON geo.v_h3_zona (h3_id);

-- Atualizacao das materialized views.
CREATE OR REPLACE FUNCTION geo.refresh_materialized() RETURNS VOID LANGUAGE plpgsql AS $$
BEGIN
  REFRESH MATERIALIZED VIEW geo.v_pois_by_h3;
  REFRESH MATERIALIZED VIEW geo.v_ndvi_latest;
  REFRESH MATERIALIZED VIEW geo.v_h3_zona;
END $$;
