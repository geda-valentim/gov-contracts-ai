-- Gov Contracts AI - Database Users and Roles
-- Version: 1.0
-- Description: Creates application users with appropriate permissions

\echo 'Creating database users and roles...'

-- Application user (read/write access)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_user') THEN
        CREATE ROLE app_user WITH LOGIN PASSWORD 'app_password_change_me';
    END IF;
END
$$;

-- Read-only user (for analytics/reporting)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'readonly_user') THEN
        CREATE ROLE readonly_user WITH LOGIN PASSWORD 'readonly_password_change_me';
    END IF;
END
$$;

-- ML pipeline user (for model training/inference)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'ml_user') THEN
        CREATE ROLE ml_user WITH LOGIN PASSWORD 'ml_password_change_me';
    END IF;
END
$$;

\echo 'Granting permissions...'

-- Grant permissions to app_user (full access to app, ml, ai schemas)
GRANT ALL PRIVILEGES ON SCHEMA app, ml, ai, audit TO app_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA app, ml, ai, audit TO app_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA app, ml, ai, audit TO app_user;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA app, ml, ai, audit TO app_user;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA app, ml, ai, audit
    GRANT ALL PRIVILEGES ON TABLES TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA app, ml, ai, audit
    GRANT ALL PRIVILEGES ON SEQUENCES TO app_user;

-- Grant read-only access to readonly_user
GRANT USAGE ON SCHEMA app, ml, ai, analytics TO readonly_user;
GRANT SELECT ON ALL TABLES IN SCHEMA app, ml, ai, analytics TO readonly_user;

-- Set default privileges for future objects (read-only)
ALTER DEFAULT PRIVILEGES IN SCHEMA app, ml, ai, analytics
    GRANT SELECT ON TABLES TO readonly_user;

-- Grant ML user access to ml and ai schemas
GRANT ALL PRIVILEGES ON SCHEMA ml, ai TO ml_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA ml, ai TO ml_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA ml, ai TO ml_user;
GRANT SELECT ON ALL TABLES IN SCHEMA app TO ml_user;

-- Set default privileges for ml_user
ALTER DEFAULT PRIVILEGES IN SCHEMA ml, ai
    GRANT ALL PRIVILEGES ON TABLES TO ml_user;

\echo 'Users and permissions configured successfully!'

-- List all users and their attributes
SELECT rolname, rolsuper, rolinherit, rolcreaterole, rolcreatedb, rolcanlogin
FROM pg_catalog.pg_roles
WHERE rolname NOT LIKE 'pg_%'
ORDER BY rolname;
