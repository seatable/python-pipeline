CREATE TABLE `task` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `repo_id` varchar(36) NOT NULL,
  `dtable_uuid` varchar(36) NOT NULL,
  `script_name` varchar(255) NOT NULL,
  `context_data` longtext,
  `trigger` longtext NOT NULL,
  `last_trigger_time` datetime(6),
  `is_active` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `task_dtable_uuid_script_name_yr8snbw3_uniq` (`dtable_uuid`,`script_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `task_log` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `task_id` int(11) NOT NULL,
  `started_at` datetime(6) NOT NULL,
  `finished_at` datetime(6),
  `success` tinyint(1),
  `return_code` int(11),
  `output` longtext,
  PRIMARY KEY (`id`),
  KEY `task_id_yw8kjf7y` (`task_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `script_log` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `repo_id` varchar(36) NOT NULL,
  `dtable_uuid` varchar(36) NOT NULL,
  `script_name` varchar(255) NOT NULL,
  `context_data` longtext,
  `started_at` datetime(6) NOT NULL,
  `finished_at` datetime(6),
  `success` tinyint(1),
  `return_code` int(11),
  `output` longtext,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
