ALTER TABLE geo.features ADD COLUMN IF NOT EXISTS zona TEXT;
ALTER TABLE geo.features ADD COLUMN IF NOT EXISTS neighborhood TEXT;
ALTER TABLE geo.features ADD COLUMN IF NOT EXISTS neighborhood_source TEXT;
CREATE SCHEMA IF NOT EXISTS market;
CREATE TABLE market.listings (
 id BIGSERIAL PRIMARY KEY, source_name TEXT NOT NULL, external_id TEXT NOT NULL,
 collected_at TIMESTAMPTZ NOT NULL DEFAULT now(), listed_at DATE, title TEXT, url TEXT,
 price NUMERIC, area_m2 NUMERIC, price_per_m2 NUMERIC, property_type TEXT,
 neighborhood TEXT, city TEXT, state TEXT, geom geometry(Point,4326),
 raw JSONB NOT NULL DEFAULT '{}'::jsonb, UNIQUE(source_name,external_id)
);
CREATE INDEX listings_geom_gix ON market.listings USING GIST(geom);
CREATE TABLE geo.neighborhoods (
 id BIGSERIAL PRIMARY KEY, name TEXT NOT NULL, municipality TEXT, municipality_code TEXT,
 source_name TEXT NOT NULL, source_file TEXT, reference_date DATE,
 imported_at TIMESTAMPTZ NOT NULL DEFAULT now(), geom geometry(MultiPolygon,4326) NOT NULL,
 UNIQUE(name,municipality_code,source_name)
);
CREATE INDEX neighborhoods_geom_gix ON geo.neighborhoods USING GIST(geom);
CREATE TABLE public.users (
 id SERIAL PRIMARY KEY, name VARCHAR NOT NULL, email VARCHAR UNIQUE,
 password_hash VARCHAR NOT NULL, role VARCHAR DEFAULT 'client'
);
CREATE INDEX ix_users_id ON public.users(id);
CREATE INDEX ix_users_email ON public.users(email);
CREATE TABLE public.leads (
 id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES public.users(id),
 created_at TIMESTAMP, name VARCHAR NOT NULL, email VARCHAR, phone VARCHAR,
 budget DOUBLE PRECISION, zone VARCHAR, property_type VARCHAR DEFAULT 'casa',
 financing_status VARCHAR DEFAULT 'nao_iniciado', timeline VARCHAR DEFAULT 'pesquisando',
 visits_done INTEGER DEFAULT 0, motivation VARCHAR, source VARCHAR,
 returning_client BOOLEAN DEFAULT false, score DOUBLE PRECISION NOT NULL,
 label VARCHAR NOT NULL, explain TEXT NOT NULL, status VARCHAR DEFAULT 'novo', notes TEXT
);
CREATE INDEX ix_leads_id ON public.leads(id);
CREATE INDEX ix_leads_user_id ON public.leads(user_id);
