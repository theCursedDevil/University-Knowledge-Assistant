-- Create least-privilege application accounts using container-provided secrets.
\set ON_ERROR_STOP on
\getenv app_password APP_DB_PASSWORD
\getenv readonly_password READONLY_DB_PASSWORD
\getenv repl_password REPL_PASSWORD
\getenv keycloak_password KEYCLOAK_DB_PASSWORD

SELECT format('CREATE ROLE uka_keycloak WITH LOGIN PASSWORD %L', :'keycloak_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'uka_keycloak')
\gexec
ALTER ROLE uka_keycloak WITH LOGIN PASSWORD :'keycloak_password';

SELECT format('CREATE DATABASE keycloak OWNER uka_keycloak')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'keycloak')
\gexec

SELECT format('CREATE ROLE uka_app WITH LOGIN PASSWORD %L', :'app_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'uka_app')
\gexec
ALTER ROLE uka_app WITH LOGIN PASSWORD :'app_password';

SELECT format('GRANT CONNECT ON DATABASE %I TO uka_app', current_database()) \gexec
GRANT USAGE, CREATE ON SCHEMA public TO uka_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO uka_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO uka_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO uka_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO uka_app;
-- uka_app runs Alembic upgrades at backend startup, so it needs CREATE on public.

SELECT format('CREATE ROLE uka_readonly WITH LOGIN PASSWORD %L', :'readonly_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'uka_readonly')
\gexec
ALTER ROLE uka_readonly WITH LOGIN PASSWORD :'readonly_password';
SELECT format('GRANT CONNECT ON DATABASE %I TO uka_readonly', current_database()) \gexec
GRANT USAGE ON SCHEMA public TO uka_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO uka_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO uka_readonly;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER ON ALL TABLES IN SCHEMA public FROM uka_readonly;
REVOKE CREATE ON SCHEMA public FROM uka_readonly;

SELECT format('CREATE ROLE uka_replicator WITH REPLICATION LOGIN PASSWORD %L', :'repl_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'uka_replicator')
\gexec
ALTER ROLE uka_replicator WITH REPLICATION LOGIN PASSWORD :'repl_password';
