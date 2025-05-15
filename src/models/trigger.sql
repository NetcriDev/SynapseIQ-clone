-- select * 
-- from incident_reports
-- where state = 'OH';


-- SELECT original_document_location, COUNT(*) AS total
-- FROM incident_reports
-- GROUP BY original_document_location;



-- UPDATE incident_reports
-- SET is_external = CASE
--     WHEN state = 'OH' THEN 'yes'
--     ELSE 'no'
-- END;

-- SELECT 
--   CASE 
--     WHEN original_document_location ILIKE '%/ohio/%' THEN 'OHIO'
--     ELSE 'OTROS'
--   END AS url_group,
--   COUNT(*) AS total
-- FROM incident_reports
-- GROUP BY url_group
-- ORDER BY total DESC;


-- CREATE OR REPLACE FUNCTION log_audit_changes() RETURNS trigger AS $$
-- DECLARE
--     user_id TEXT := current_user;
-- BEGIN
--     -- Log para debug
--     RAISE NOTICE 'Trigger ejecutado para la acción % en la tabla %', TG_OP, TG_TABLE_NAME;

--     IF (TG_OP = 'UPDATE') THEN
--         INSERT INTO audit_log (
--             table_name, record_id, action,
--             old_data, old_data_text,
--             new_data, new_data_text,
--             changed_by, source
--         )
--         VALUES (
--             TG_TABLE_NAME,
--             OLD.id::TEXT,
--             'UPDATE',
--             to_jsonb(OLD), OLD::TEXT,
--             to_jsonb(NEW), NEW::TEXT,
--             user_id,
--             'trigger'
--         );
--         RETURN NEW;

--     ELSIF (TG_OP = 'DELETE') THEN
--         INSERT INTO audit_log (
--             table_name, record_id, action,
--             old_data, old_data_text,
--             changed_by, source
--         )
--         VALUES (
--             TG_TABLE_NAME,
--             OLD.id::TEXT,
--             'DELETE',
--             to_jsonb(OLD), OLD::TEXT,
--             user_id,
--             'trigger'
--         );
--         RETURN OLD;
--     END IF;

--     RETURN NULL;
-- END;
-- $$ LANGUAGE plpgsql;

-- CREATE TRIGGER trg_audit_incident_reports
-- AFTER UPDATE OR DELETE ON incident_reports
-- FOR EACH ROW
-- EXECUTE FUNCTION log_audit_changes();


-- CREATE TRIGGER trg_audit_vehicles
-- AFTER UPDATE OR DELETE ON vehicles
-- FOR EACH ROW
-- EXECUTE FUNCTION log_audit_changes();

-- CREATE TRIGGER trg_audit_passengers
-- AFTER UPDATE OR DELETE ON passengers
-- FOR EACH ROW
-- EXECUTE FUNCTION log_audit_changes();

-- UPDATE incident_reports
-- SET notes = 'Auditoría test'
-- WHERE id = 1;

-- SELECT * FROM audit_log
-- ORDER BY changed_at DESC
-- LIMIT 5;






