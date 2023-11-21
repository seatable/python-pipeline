CREATE TABLE IF NOT EXISTS `task` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `dtable_uuid` varchar(36) NOT NULL,
  `owner` varchar(255),
  `org_id` int(11),
  `script_name` varchar(255) NOT NULL,
  `context_data` longtext,
  `trigger` longtext NOT NULL,
  `last_trigger_time` datetime(6),
  `is_active` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `task_dtable_uuid_script_name_yr8snbw3_uniq` (`dtable_uuid`,`script_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `script_log` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `dtable_uuid` varchar(36) NOT NULL,
  `owner` varchar(255) DEFAULT NULL,
  `org_id` int(11) DEFAULT NULL,
  `script_name` varchar(255) NOT NULL,
  `context_data` longtext DEFAULT NULL,
  `started_at` datetime(6) NOT NULL,
  `finished_at` datetime(6) DEFAULT NULL,
  `success` tinyint(1) DEFAULT NULL,
  `return_code` int(11) DEFAULT NULL,
  `output` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `operate_from` varchar(50) DEFAULT NULL COMMENT 'manualy, automation-rule...etc',
  PRIMARY KEY (`id`),
  KEY `started_at_c6ns09vt` (`started_at`),
  KEY `dtable_uuid_script_name_l0j7h5f2_union_key` (`dtable_uuid`,`script_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `dtable_run_script_statistics` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `dtable_uuid` varchar(36) NOT NULL,
  `run_date` date NOT NULL,
  `total_run_count` int(11) DEFAULT 0,
  `total_run_time` float DEFAULT 0,
  `update_at` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `dtable_uuid_run_date_k2n9j3p1_uniq_key` (`dtable_uuid`,`run_date`),
  KEY `dtable_uuid_n3b5u4d1_key` (`dtable_uuid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `user_run_script_statistics` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(255) NOT NULL,
  `run_date` date NOT NULL,
  `total_run_count` int(11) DEFAULT 0,
  `total_run_time` float DEFAULT 0,
  `update_at` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username_run_date_n3x0p2i8_uniq_key` (`username`,`run_date`),
  KEY `username_m0o1g4d0_key` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `org_run_script_statistics` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `org_id` int(11) NOT NULL,
  `run_date` date NOT NULL,
  `total_run_count` int(11) DEFAULT 0,
  `total_run_time` float DEFAULT 0,
  `update_at` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `org_id_run_date_a0g6y5r4_uniq_key` (`org_id`,`run_date`),
  KEY `org_id_v4b5h2d9_key` (`org_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `version_history` (
  `version` varchar(10) NOT NULL,
  `update_at` datetime(6) DEFAULT NULL
) ENGINE=InnoDB CHARSET=utf8;