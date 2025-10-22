-- Gov Contracts AI - Database Schemas
-- Version: 1.0
-- Description: Creates logical schemas for data organization

\echo 'Creating database schemas...'

-- Core application schema
CREATE SCHEMA IF NOT EXISTS app;
COMMENT ON SCHEMA app IS 'Core application tables (licitacoes, items, fornecedores)';

-- Machine Learning schema
CREATE SCHEMA IF NOT EXISTS ml;
COMMENT ON SCHEMA ml IS 'ML features, predictions, and model metadata';

-- AI/RAG schema
CREATE SCHEMA IF NOT EXISTS ai;
COMMENT ON SCHEMA ai IS 'Embeddings, RAG metadata, LLM prompts/responses';

-- Audit and logging schema
CREATE SCHEMA IF NOT EXISTS audit;
COMMENT ON SCHEMA audit IS 'Audit logs, user actions, system events';

-- Analytics and reporting schema
CREATE SCHEMA IF NOT EXISTS analytics;
COMMENT ON SCHEMA analytics IS 'Materialized views, aggregations, dashboards';

\echo 'Schemas created successfully!'

-- List all schemas
SELECT schema_name,
       pg_catalog.obj_description(oid) as description
FROM information_schema.schemata
JOIN pg_namespace ON nspname = schema_name
WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
ORDER BY schema_name;
