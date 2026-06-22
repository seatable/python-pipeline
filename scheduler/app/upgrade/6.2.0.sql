
ALTER TABLE script_log MODIFY started_at DATETIME(6);

ALTER TABLE script_log ADD COLUMN IF NOT EXISTS state VARCHAR(10);
ALTER TABLE script_log ADD INDEX IF NOT EXISTS state_h3u8i9o1_key (state);

ALTER TABLE script_log ADD COLUMN IF NOT EXISTS created_at DATETIME(6);
ALTER TABLE script_log ADD INDEX IF NOT EXISTS created_at_h3u7y9o4_key (created_at);
UPDATE script_log SET created_at=started_at;
