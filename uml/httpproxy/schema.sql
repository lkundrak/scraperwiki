CREATE TABLE `httpcache` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `tag` varchar(255) DEFAULT NULL,
  `url` text,
  `page` longblob,
  `scraperid` varchar(255) DEFAULT NULL,
  `runid` varchar(255) DEFAULT NULL,
  `hits` int(11) DEFAULT NULL,
  `stamp` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `httpcache_tag` (`tag`)
) ENGINE=InnoDB;
