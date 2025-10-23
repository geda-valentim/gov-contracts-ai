-- Gov Contracts AI - PostgreSQL Extensions Setup
-- Version: 1.0
-- Description: Creates necessary extensions for the application

\echo 'Creating PostgreSQL extensions...'

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable trigram similarity search (for fuzzy text matching)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Enable vector operations (for embeddings storage)
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable advanced statistics
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Enable full-text search with Portuguese support
CREATE TEXT SEARCH CONFIGURATION pt (COPY = pg_catalog.portuguese);

\echo 'Extensions created successfully!'

-- List all installed extensions
SELECT extname, extversion, extrelocatable, extnamespace::regnamespace AS schema
FROM pg_extension
ORDER BY extname;
