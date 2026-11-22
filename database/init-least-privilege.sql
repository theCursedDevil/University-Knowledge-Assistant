-- ==============================================================================
-- Generative AI-Based University Knowledge Assistant
-- Least-Privilege Role Separation Script (FR-AUTH, C-DAL, NFR-SEC-005)
--
-- Roles Created:
-- 1. uka_app: Least-privilege application role (Read/Write Data, No DDL/Superuser)
-- 2. uka_readonly: Read-only replica role (Strictly SELECT, No Mutations)
-- 3. uka_replicator: Streaming replication worker role
-- ==============================================================================

-- 1. Create Least-Privilege Application User
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'uka_app') THEN
        CREATE ROLE uka_app WITH LOGIN PASSWORD 'uka_app_secure_password';
        RAISE NOTICE 'Role uka_app created.';
    ELSE
        RAISE NOTICE 'Role uka_app already exists.';
    END IF;
END
$$;

-- Grant database connection and schema usage
GRANT CONNECT ON DATABASE university_assistant TO uka_app;
GRANT USAGE ON SCHEMA public TO uka_app;

-- Grant strictly Data Manipulation Privileges (SELECT, INSERT, UPDATE, DELETE)
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO uka_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO uka_app;

-- Ensure future tables and sequences created by migrations inherit least-privilege grants
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO uka_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO uka_app;

-- Revoke all administrative and DDL capabilities from application user
REVOKE CREATE ON SCHEMA public FROM uka_app;
REVOKE ALL PRIVILEGES ON DATABASE university_assistant FROM uka_app;
GRANT CONNECT ON DATABASE university_assistant TO uka_app;


-- 2. Create Read-Only Database Account for Replicas (Requirement 11)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'uka_readonly') THEN
        CREATE ROLE uka_readonly WITH LOGIN PASSWORD 'uka_readonly_secure_password';
        RAISE NOTICE 'Role uka_readonly created.';
    ELSE
        RAISE NOTICE 'Role uka_readonly already exists.';
    END IF;
END
$$;

-- Grant database connection and schema usage
GRANT CONNECT ON DATABASE university_assistant TO uka_readonly;
GRANT USAGE ON SCHEMA public TO uka_readonly;

-- Grant strictly SELECT privilege on all tables
GRANT SELECT ON ALL TABLES IN SCHEMA public TO uka_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO uka_readonly;

-- Revoke mutation and DDL privileges
REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER ON ALL TABLES IN SCHEMA public FROM uka_readonly;
REVOKE CREATE ON SCHEMA public FROM uka_readonly;


-- 3. Create Dedicated Streaming Replication User
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'uka_replicator') THEN
        CREATE ROLE uka_replicator WITH REPLICATION LOGIN PASSWORD 'uka_replica_stream_password';
        RAISE NOTICE 'Role uka_replicator created.';
    ELSE
        RAISE NOTICE 'Role uka_replicator already exists.';
    END IF;
END
$$;
