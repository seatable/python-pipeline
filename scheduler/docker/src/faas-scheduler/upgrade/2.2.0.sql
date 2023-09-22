ALTER TABLE script_log ADD COLUMN IF NOT EXISTS operate_from varchar(50);
ALTER TABLE script_log ADD INDEX IF NOT EXISTS `dtable_uuid_script_name_l0j7h5f2_union_key` (`dtable_uuid`,`script_name`);
