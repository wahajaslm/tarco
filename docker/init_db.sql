-- WORKFLOW: Database initialization script for PostgreSQL with pgvector extension.
-- Used by: Docker container startup, database setup, development environment
-- Initialization steps:
-- 1. Create pgvector extension for vector operations
-- 2. Create text_index schema for RAG embeddings
-- 3. Grant permissions to application user
-- 4. Create indexes for performance optimization
-- 5. Set default privileges for future tables
--
-- Database flow: Container startup -> Run init script -> Create extensions -> Grant permissions
-- This ensures the database is properly configured for vector search and application access.

-- Initialize PostgreSQL database for Trade Compliance API

-- Create pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create text_index schema
CREATE SCHEMA IF NOT EXISTS text_index;

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA public TO tarco;
GRANT ALL PRIVILEGES ON SCHEMA text_index TO tarco;

-- Set search path
SET search_path TO public, text_index;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_goods_code_level ON goods_nomenclature(goods_code, level);
CREATE INDEX IF NOT EXISTS idx_is_leaf ON goods_nomenclature(is_leaf);
CREATE INDEX IF NOT EXISTS idx_import_goods_origin ON measures_import(goods_code, origin_group);
CREATE INDEX IF NOT EXISTS idx_import_legal_base ON measures_import(legal_base_id);
CREATE INDEX IF NOT EXISTS idx_import_validity ON measures_import(valid_from, valid_to);
CREATE INDEX IF NOT EXISTS idx_export_goods_dest ON measures_export(goods_code, destination_group);
CREATE INDEX IF NOT EXISTS idx_export_legal_base ON measures_export(legal_base_id);
CREATE INDEX IF NOT EXISTS idx_export_validity ON measures_export(valid_from, valid_to);
CREATE INDEX IF NOT EXISTS idx_conditions_goods_cert ON measure_conditions(goods_code, certificate_code);
CREATE INDEX IF NOT EXISTS idx_geo_type ON geographies(type);
CREATE INDEX IF NOT EXISTS idx_geo_group ON geographies(group_name);
CREATE INDEX IF NOT EXISTS idx_vat_validity ON vat_rates(valid_from, valid_to);
CREATE INDEX IF NOT EXISTS idx_exchange_iso_date ON exchange_rates(iso, rate_date);
CREATE INDEX IF NOT EXISTS idx_reach_goods_prefix ON reach_map(goods_code_prefix);
CREATE INDEX IF NOT EXISTS idx_reach_entry ON reach_map(entry_no);

-- Create text index schema indexes
CREATE INDEX IF NOT EXISTS idx_chunks_goods_code ON text_index.nomenclature_chunks(goods_code);
CREATE INDEX IF NOT EXISTS idx_evidence_hs_prefix ON text_index.evidence_chunks(hs_prefix);
CREATE INDEX IF NOT EXISTS idx_evidence_chapter ON text_index.evidence_chunks(chapter);
CREATE INDEX IF NOT EXISTS idx_evidence_legal_base ON text_index.evidence_chunks(legal_base_id);

-- Grant permissions on all tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO tarco;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA text_index TO tarco;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO tarco;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA text_index TO tarco;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO tarco;
ALTER DEFAULT PRIVILEGES IN SCHEMA text_index GRANT ALL ON TABLES TO tarco;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO tarco;
ALTER DEFAULT PRIVILEGES IN SCHEMA text_index GRANT ALL ON SEQUENCES TO tarco;
