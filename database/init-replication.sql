-- ==============================================================================
-- Generative AI-Based University Knowledge Assistant
-- PostgreSQL Primary & Read-Replica Synchronization Setup (C-DAL, SDD §5.1)
--
-- Configures replication slots and physical streaming replication between
-- primary PostgreSQL instance and 2 read replicas.
-- ==============================================================================

-- 1. Create replication user if not exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'uka_replicator') THEN
        CREATE ROLE uka_replicator WITH REPLICATION LOGIN PASSWORD 'uka_replica_stream_password';
        RAISE NOTICE 'Replication role uka_replicator created.';
    END IF;
END
$$;

-- 2. Create physical replication slots for Replica 1 and Replica 2
SELECT pg_create_physical_replication_slot('replica_1_slot')
WHERE NOT EXISTS (
    SELECT 1 FROM pg_replication_slots WHERE slot_name = 'replica_1_slot'
);

SELECT pg_create_physical_replication_slot('replica_2_slot')
WHERE NOT EXISTS (
    SELECT 1 FROM pg_replication_slots WHERE slot_name = 'replica_2_slot'
);

-- 3. Verification query to monitor replica lag and health
-- SELECT client_addr, state, sent_lsn, write_lsn, flush_lsn, replay_lsn, sync_state
-- FROM pg_stat_replication;
