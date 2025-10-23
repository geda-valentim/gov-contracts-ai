-- Gov Contracts AI - Utility Functions
-- Version: 1.0
-- Description: Creates useful database functions

\echo 'Creating utility functions...'

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION app.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION app.update_updated_at_column() IS 'Automatically updates updated_at timestamp on row update';

-- Function to calculate similarity between text using trigrams
CREATE OR REPLACE FUNCTION app.text_similarity(text1 TEXT, text2 TEXT)
RETURNS FLOAT AS $$
BEGIN
    RETURN similarity(text1, text2);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION app.text_similarity(TEXT, TEXT) IS 'Calculate trigram similarity between two texts (0-1)';

-- Function to normalize CNPJ
CREATE OR REPLACE FUNCTION app.normalize_cnpj(cnpj TEXT)
RETURNS TEXT AS $$
BEGIN
    -- Remove all non-numeric characters
    RETURN regexp_replace(cnpj, '[^0-9]', '', 'g');
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION app.normalize_cnpj(TEXT) IS 'Normalize CNPJ by removing special characters';

-- Function to validate CNPJ format
CREATE OR REPLACE FUNCTION app.is_valid_cnpj(cnpj TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    normalized_cnpj TEXT;
BEGIN
    normalized_cnpj := app.normalize_cnpj(cnpj);
    RETURN length(normalized_cnpj) = 14 AND normalized_cnpj ~ '^[0-9]{14}$';
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION app.is_valid_cnpj(TEXT) IS 'Validate CNPJ format (14 digits)';

-- Function to calculate cosine similarity between vectors
CREATE OR REPLACE FUNCTION ai.cosine_similarity(vec1 vector, vec2 vector)
RETURNS FLOAT AS $$
BEGIN
    RETURN 1 - (vec1 <=> vec2);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION ai.cosine_similarity(vector, vector) IS 'Calculate cosine similarity between two vectors';

\echo 'Utility functions created successfully!'

-- List all custom functions
SELECT n.nspname AS schema,
       p.proname AS function_name,
       pg_catalog.obj_description(p.oid) AS description
FROM pg_catalog.pg_proc p
JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname IN ('app', 'ml', 'ai', 'analytics')
ORDER BY schema, function_name;
