-- Create Airflow database
-- This must run before other scripts (hence 00- prefix)

-- Create airflow database
CREATE DATABASE airflow
    WITH
    OWNER = admin
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.utf8'
    LC_CTYPE = 'en_US.utf8'
    TEMPLATE = template0;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE airflow TO admin;

-- Connect to airflow database and create extensions
\c airflow

-- Create commonly used extensions for Airflow
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Log completion
\echo 'Airflow database created successfully'
