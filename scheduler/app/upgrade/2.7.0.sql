ALTER TABLE `script_log` CHANGE `output` `output` LONGTEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
DROP TABLE IF EXISTS `task_log`;
DROP TABLE IF EXISTS `task`;
ALTER TABLE user_run_script_statistics ADD COLUMN IF NOT EXISTS org_id int(11) DEFAULT NULL AFTER username;
