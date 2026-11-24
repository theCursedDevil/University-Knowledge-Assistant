-- Create the streaming-replication account and slots using container secrets.
\set ON_ERROR_STOP on
\getenv repl_password REPL_PASSWORD

SELECT format('CREATE ROLE uka_replicator WITH REPLICATION LOGIN PASSWORD %L', :'repl_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'uka_replicator')
\gexec
ALTER ROLE uka_replicator WITH REPLICATION LOGIN PASSWORD :'repl_password';

SELECT pg_create_physical_replication_slot('replica_1_slot')
WHERE NOT EXISTS (SELECT 1 FROM pg_replication_slots WHERE slot_name = 'replica_1_slot');

SELECT pg_create_physical_replication_slot('replica_2_slot')
WHERE NOT EXISTS (SELECT 1 FROM pg_replication_slots WHERE slot_name = 'replica_2_slot');
