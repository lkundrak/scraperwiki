begin;

delete from codewiki_code;
delete from codewiki_scraper;
delete from codewiki_codecommitevent;
delete from codewiki_scrapermetadata;
delete from codewiki_scraperrunevent;
delete from codewiki_usercoderole;

insert into codewiki_code 
(id, title, short_name, source, description, created_at, deleted, status, guid, published, first_published_at, featured, line_count, istutorial, isstartup, language)
select
id, title, short_name, source, description, created_at, deleted, status, guid, published, first_published_at, featured, line_count, istutorial, isstartup, language
from scraper_scraper;

insert into codewiki_scraper
(code_ptr_id, last_run, license, scraper_sparkline_csv, has_geo, has_temporal, record_count, run_interval)
select
id, last_run, license, scraper_sparkline_csv, has_geo, has_temporal, record_count, run_interval
from scraper_scraper;

insert into codewiki_codecommitevent
(id, revision)
select
id, revision
from scraper_scrapercommitevent;

insert into codewiki_scrapermetadata
(id, name, scraper_id, run_id, value)
select
id, name, scraper_id, run_id, value
from scraper_scrapermetadata;

insert into codewiki_scraperrunevent
(id, scraper_id, run_id, pid, run_started, run_ended, records_produced, pages_scraped, output)
select
id, scraper_id, run_id, pid, run_started, run_ended, records_produced, pages_scraped, output
from scraper_scraperrunevent;

insert into codewiki_usercoderole
(id, user_id, code_id, role)
select
id, user_id, scraper_id, role
from scraper_userscraperrole;

commit;
