ALTER TABLE `script_log` CHANGE `output` `output` LONGTEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
DELETE TABLE IF EXISTS `task_log`;