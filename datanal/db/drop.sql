
-- past data

DROP TABLE IF EXISTS "past_game_analysis" CASCADE;

DROP SEQUENCE IF EXISTS "s.past_game_player_stats" CASCADE;
DROP TABLE IF EXISTS "past_game_player_stats" CASCADE;

DROP SEQUENCE IF EXISTS "s.past_game_team_stats" CASCADE;
DROP TABLE IF EXISTS "past_game_team_stats" CASCADE;

DROP SEQUENCE IF EXISTS "s.past_game_invalid" CASCADE;
DROP TABLE IF EXISTS "past_game_invalid" CASCADE;

DROP SEQUENCE IF EXISTS "s.past_game_stats" CASCADE;
DROP TABLE IF EXISTS "past_game_stats" CASCADE;


-- current data

DROP TABLE IF EXISTS "current_game_analysis" CASCADE;

DROP SEQUENCE IF EXISTS "s.current_game_player_unchanged" CASCADE;
DROP TABLE IF EXISTS "current_game_player_unchanged" CASCADE;

DROP SEQUENCE IF EXISTS "s.current_game_player_stats" CASCADE;
DROP TABLE IF EXISTS "current_game_player_stats" CASCADE;

DROP SEQUENCE IF EXISTS "s.current_game_team_unchanged" CASCADE;
DROP TABLE IF EXISTS "current_game_team_unchanged" CASCADE;

DROP SEQUENCE IF EXISTS "s.current_game_team_stats" CASCADE;
DROP TABLE IF EXISTS "current_game_team_stats" CASCADE;

DROP SEQUENCE IF EXISTS "s.current_game_unchanged" CASCADE;
DROP TABLE IF EXISTS "current_game_unchanged" CASCADE;

DROP SEQUENCE IF EXISTS "s.current_game_invalid" CASCADE;
DROP TABLE IF EXISTS "current_game_invalid" CASCADE;

DROP SEQUENCE IF EXISTS "s.current_game_stats" CASCADE;
DROP TABLE IF EXISTS "current_game_stats" CASCADE;

DROP SEQUENCE IF EXISTS "s.current_game_watch" CASCADE;
DROP TABLE IF EXISTS "current_game_watch" CASCADE;


-- domains

DROP DOMAIN IF EXISTS "d.primary_key" CASCADE;
DROP DOMAIN IF EXISTS "d.foreign_key" CASCADE;
DROP DOMAIN IF EXISTS "d.boolean" CASCADE;
DROP DOMAIN IF EXISTS "d.int" CASCADE;
DROP DOMAIN IF EXISTS "d.smallint" CASCADE;
DROP DOMAIN IF EXISTS "d.bigint" CASCADE;
DROP DOMAIN IF EXISTS "d.float" CASCADE;
DROP DOMAIN IF EXISTS "d.date" CASCADE;
DROP DOMAIN IF EXISTS "d.time" CASCADE;
DROP DOMAIN IF EXISTS "d.datetime" CASCADE;
DROP DOMAIN IF EXISTS "d.current_datetime" CASCADE;
DROP DOMAIN IF EXISTS "d.binary_blob" CASCADE;
DROP DOMAIN IF EXISTS "d.text" CASCADE;
DROP DOMAIN IF EXISTS "d.name" CASCADE;
DROP DOMAIN IF EXISTS "d.data_src" CASCADE;
DROP DOMAIN IF EXISTS "d.game_name" CASCADE;
