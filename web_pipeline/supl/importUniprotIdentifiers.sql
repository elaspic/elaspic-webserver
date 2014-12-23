-- Import all uniprot identifiers
COPY uniprot_kb.uniprot_identifier(uniprot_id, identifier_type, identifier_id)
FROM '/tmp/idmapping.dat' 
WITH (DELIMITER E'\t');

-- Delete all rows with empty identifier
DELETE FROM uniprot_kb.uniprot_identifier
WHERE identifier_id = '-';




-- Check status
SELECT dead_tuple_count FROM pgstattuple('uniprot_kb.uniprot_identifier');

-- Check if active
SELECT * FROM pg_stat_activity; 

-- Kill process 
SELECT pg_cancel_backend(pid of the postgres process); 