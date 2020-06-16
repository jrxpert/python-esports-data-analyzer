
-- domains

CREATE DOMAIN "d.primary_key" AS bigint NOT NULL;
CREATE DOMAIN "d.foreign_key" AS bigint;
CREATE DOMAIN "d.boolean" AS boolean NOT NULL DEFAULT false;
CREATE DOMAIN "d.int" AS integer;
CREATE DOMAIN "d.smallint" AS smallint;
CREATE DOMAIN "d.bigint" AS bigint;
CREATE DOMAIN "d.float" AS float;
CREATE DOMAIN "d.date" AS date;
CREATE DOMAIN "d.time" AS time without time zone;
CREATE DOMAIN "d.datetime" AS timestamp without time zone;
CREATE DOMAIN "d.current_datetime" AS timestamp without time zone NOT NULL DEFAULT now();
CREATE DOMAIN "d.binary_blob" AS bytea;
CREATE DOMAIN "d.text" AS TEXT;
CREATE DOMAIN "d.name" AS character varying(80);
CREATE DOMAIN "d.data_src" AS character varying(11) NOT NULL
    CONSTRAINT "d.data_src" CHECK ((VALUE = ANY (ARRAY['provider1', 'provider2'])));
CREATE DOMAIN "d.game_name" AS character varying(5) NOT NULL
    CONSTRAINT "d.game_name" CHECK ((VALUE = ANY (ARRAY['csgo', 'dota2', 'lol'])));


-- current data

CREATE SEQUENCE "s.current_game_watch";
CREATE TABLE "current_game_watch" (
    "id" "d.primary_key" DEFAULT nextval('"s.current_game_watch"'),
    "data_src" "d.data_src",
    "game_name" "d.game_name",
    "data_src_url" VARCHAR(255),
    "data_src_game_id" "d.int",
    "data_src_game_title" "d.name",
    "data_src_start_datetime" "d.datetime",
    "data_src_finish_datetime" "d.datetime",
    "data_src_tournament_id" "d.int",
    "data_src_tournament_title" "d.name",
    "insert_datetime" "d.current_datetime",
    "is_watching" "d.boolean",
    "is_deleted" "d.boolean" DEFAULT false,

    CONSTRAINT "pk.current_game_watch"
        PRIMARY KEY("id")
);


CREATE SEQUENCE "s.current_game_stats";
CREATE TABLE "current_game_stats" (
    "id" "d.primary_key" DEFAULT nextval('"s.current_game_stats"'),
    "watch_game_id" "d.foreign_key" NOT NULL,
    "unchanged_game_id" "d.foreign_key" DEFAULT NULL,
    "insert_datetime" "d.current_datetime",

    CONSTRAINT "pk.current_game_stats"
        PRIMARY KEY("id"),

    CONSTRAINT "fk.current_game_stats.game"
        FOREIGN KEY ("watch_game_id")
        REFERENCES "current_game_watch" ("id")
        ON UPDATE RESTRICT
        ON DELETE CASCADE
);


CREATE SEQUENCE "s.current_game_invalid";
CREATE TABLE "current_game_invalid" (
    "id" "d.primary_key" DEFAULT nextval('"s.current_game_invalid"'),
    "watch_game_id" "d.foreign_key" NULL,
    "data_src_url" VARCHAR(255),
    "insert_datetime" "d.current_datetime",
    "problem_msg" "d.text",

    CONSTRAINT "pk.current_game_invalid"
        PRIMARY KEY("id"),

    CONSTRAINT "fk.current_game_invalid.game"
        FOREIGN KEY ("watch_game_id")
        REFERENCES "current_game_watch" ("id")
        ON UPDATE RESTRICT
        ON DELETE CASCADE
);


CREATE SEQUENCE "s.current_game_unchanged";
CREATE TABLE "current_game_unchanged" (
    "id" "d.primary_key" DEFAULT nextval('"s.current_game_unchanged"'),
    "watch_game_id" "d.foreign_key" NOT NULL,
    "stats_game_id" "d.foreign_key" DEFAULT NULL,
    "data_src_url" VARCHAR(255),
    "insert_datetime" "d.current_datetime",

    CONSTRAINT "pk.current_game_unchanged"
        PRIMARY KEY("id"),

    CONSTRAINT "fk.current_game_unchanged.game"
        FOREIGN KEY ("watch_game_id")
        REFERENCES "current_game_watch" ("id")
        ON UPDATE RESTRICT
        ON DELETE CASCADE
);


CREATE SEQUENCE "s.current_game_player_stats";
CREATE TABLE "current_game_player_stats" (
    "id" "d.primary_key" DEFAULT nextval('"s.current_game_player_stats"'),
    "stats_game_id" "d.foreign_key" NOT NULL,
    "data_src_url" VARCHAR(255),
    "data_src_player_id" "d.int",
    "kill" "d.smallint",
    "assist" "d.smallint",
    "death" "d.smallint",
    "tower_kill" "d.smallint", -- DOTA2 special
    "roshan_kill" "d.smallint", -- DOTA2 special
    "creep_score" "d.float", -- LOL special

    CONSTRAINT "pk.current_game_player_stats"
        PRIMARY KEY("id"),

    CONSTRAINT "fk.current_game_player_stats.game"
        FOREIGN KEY ("stats_game_id")
        REFERENCES "current_game_stats" ("id")
        ON UPDATE RESTRICT
        ON DELETE CASCADE
);


CREATE SEQUENCE "s.current_game_player_unchanged";
CREATE TABLE "current_game_player_unchanged" (
    "id" "d.primary_key" DEFAULT nextval('"s.current_game_player_unchanged"'),
    "stats_game_id" "d.foreign_key" NOT NULL,
    "data_src_url" VARCHAR(255),
    "data_src_player_id" "d.int",
    "kill" "d.smallint",
    "assist" "d.smallint",
    "death" "d.smallint",
    "tower_kill" "d.smallint", -- DOTA2 special
    "roshan_kill" "d.smallint", -- DOTA2 special
    "creep_score" "d.float", -- LOL special

    CONSTRAINT "pk.current_game_player_unchanged"
        PRIMARY KEY("id"),

    CONSTRAINT "fk.current_game_player_unchanged.game"
        FOREIGN KEY ("stats_game_id")
        REFERENCES "current_game_unchanged" ("id")
        ON UPDATE RESTRICT
        ON DELETE CASCADE
);


CREATE SEQUENCE "s.current_game_team_stats";
CREATE TABLE "current_game_team_stats" (
    "id" "d.primary_key" DEFAULT nextval('"s.current_game_team_stats"'),
    "stats_game_id" "d.foreign_key" NOT NULL,
    "data_src_url" VARCHAR(255),
    "data_src_team_id" "d.int",
    "bomb_plant" "d.smallint" DEFAULT NULL, -- CS:GO special
    "bomb_defuse" "d.smallint" DEFAULT NULL, -- CS:GO special
    "round_win" "d.smallint" DEFAULT NULL, -- CS:GO special
    "round_lose" "d.smallint" DEFAULT NULL, -- CS:GO special
    "team_win" "d.smallint" DEFAULT NULL, -- DOTA2 special
    "team_lose" "d.smallint" DEFAULT NULL, -- DOTA2 special
    "turret" "d.smallint" DEFAULT NULL, -- LOL special
    "dragon" "d.smallint" DEFAULT NULL, -- LOL special
    "baron" "d.smallint" DEFAULT NULL, -- LOL special

    CONSTRAINT "pk.current_game_team_stats"
        PRIMARY KEY("id"),

    CONSTRAINT "fk.current_game_team_stats.game"
        FOREIGN KEY ("stats_game_id")
        REFERENCES "current_game_stats" ("id")
        ON UPDATE RESTRICT
        ON DELETE CASCADE,

    CONSTRAINT "uq.current_game_team_stats.src_game_team"
        UNIQUE ("stats_game_id", "data_src_team_id")
);


CREATE SEQUENCE "s.current_game_team_unchanged";
CREATE TABLE "current_game_team_unchanged" (
    "id" "d.primary_key" DEFAULT nextval('"s.current_game_team_unchanged"'),
    "stats_game_id" "d.foreign_key" NOT NULL,
    "data_src_url" VARCHAR(255),
    "data_src_team_id" "d.int",
    "bomb_plant" "d.smallint" DEFAULT NULL, -- CS:GO special
    "bomb_defuse" "d.smallint" DEFAULT NULL, -- CS:GO special
    "round_win" "d.smallint" DEFAULT NULL, -- CS:GO special
    "round_lose" "d.smallint" DEFAULT NULL, -- CS:GO special
    "team_win" "d.smallint" DEFAULT NULL, -- DOTA2 special
    "team_lose" "d.smallint" DEFAULT NULL, -- DOTA2 special
    "turret" "d.smallint" DEFAULT NULL, -- LOL special
    "dragon" "d.smallint" DEFAULT NULL, -- LOL special
    "baron" "d.smallint" DEFAULT NULL, -- LOL special

    CONSTRAINT "pk.current_game_team_unchanged"
        PRIMARY KEY("id"),

    CONSTRAINT "fk.current_game_team_unchanged.game"
        FOREIGN KEY ("stats_game_id")
        REFERENCES "current_game_unchanged" ("id")
        ON UPDATE RESTRICT
        ON DELETE CASCADE,

    CONSTRAINT "uq.current_game_team_unchanged.src_game_team"
        UNIQUE ("stats_game_id", "data_src_team_id")
);


CREATE TABLE "current_game_analysis" (
    "data_src" "d.data_src",
    "game_name" "d.name" DEFAULT NULL,
    "games_watch_count" "d.int" DEFAULT 0,
    "games_watch_with_stats_count" "d.int" DEFAULT 0,
    "games_watch_with_stats_percent" "d.float" DEFAULT 0,
    "games_watch_with_stats_corrected_count" "d.int" DEFAULT 0,
    "games_watch_with_stats_corrected_percent" "d.float" DEFAULT 0,
    "games_stats_correction_count" "d.int" DEFAULT 0,
    "games_stats_correction_per_game_average_count" "d.int" DEFAULT 0,
    "games_stats_game_end_save_stats_average_seconds_diff" "d.float" DEFAULT 0,
    "games_stats_save_stats_last_correction_average_seconds_diff" "d.float" DEFAULT 0,
    "datapoints_stats_count" "d.int" DEFAULT 0,
    "datapoints_stats_correction_count" "d.int" DEFAULT 0,
    "datapoints_stats_correction_percent" "d.float" DEFAULT 0,
    "datapoints_stats_correction_per_game_max" "d.int" DEFAULT 0,
    "datapoints_stats_correction_per_game_median" "d.float" DEFAULT 0,
    "analysis_update_datetime" "d.datetime" DEFAULT NULL,

    CONSTRAINT "uq.current_game_analysis.src"
        UNIQUE ("data_src", "game_name")
);

INSERT INTO "current_game_analysis" ("data_src", "game_name") VALUES ('provider1', 'csgo');
INSERT INTO "current_game_analysis" ("data_src", "game_name") VALUES ('provider1', 'dota2');
INSERT INTO "current_game_analysis" ("data_src", "game_name") VALUES ('provider1', 'lol');
INSERT INTO "current_game_analysis" ("data_src", "game_name") VALUES ('provider1', NULL);
INSERT INTO "current_game_analysis" ("data_src", "game_name") VALUES ('provider2', 'csgo');
INSERT INTO "current_game_analysis" ("data_src", "game_name") VALUES ('provider2', 'dota2');
INSERT INTO "current_game_analysis" ("data_src", "game_name") VALUES ('provider2', 'lol');
INSERT INTO "current_game_analysis" ("data_src", "game_name") VALUES ('provider2', NULL);


-- past data

CREATE SEQUENCE "s.past_game_stats";
CREATE TABLE "past_game_stats" (
    "id" "d.primary_key" DEFAULT nextval('"s.past_game_stats"'),
    "data_src" "d.data_src",
    "game_name" "d.game_name",
    "data_src_url" VARCHAR(255),
    "data_src_game_id" "d.int",
    "data_src_game_title" "d.name",
    "data_src_start_datetime" "d.datetime",
    "data_src_finish_datetime" "d.datetime",
    "data_src_tournament_id" "d.int",
    "data_src_tournament_title" "d.name",
    "insert_datetime" "d.current_datetime",
    "update_datetime" "d.datetime",

    CONSTRAINT "pk.past_game_stats"
        PRIMARY KEY("id"),

    CONSTRAINT "uq.past_game_stats.src_game"
        UNIQUE ("data_src_game_id")
);


CREATE SEQUENCE "s.past_game_invalid";
CREATE TABLE "past_game_invalid" (
    "id" "d.primary_key" DEFAULT nextval('"s.past_game_invalid"'),
    "data_src_url" VARCHAR(255),
    "stats_game_id" "d.int" DEFAULT NULL,
    "insert_datetime" "d.current_datetime",
    "problem_msg" "d.text",

    CONSTRAINT "pk.past_game_invalid"
        PRIMARY KEY("id")
);


CREATE SEQUENCE "s.past_game_player_stats";
CREATE TABLE "past_game_player_stats" (
    "id" "d.primary_key" DEFAULT nextval('"s.past_game_player_stats"'),
    "stats_game_id" "d.foreign_key" NOT NULL,
    "data_src_url" VARCHAR(255),
    "data_src_player_id" "d.int",
    "kill" "d.smallint",
    "assist" "d.smallint",
    "death" "d.smallint",
    "tower_kill" "d.smallint" DEFAULT NULL, -- DOTA2 special
    "roshan_kill" "d.smallint" DEFAULT NULL, -- DOTA2 special
    "creep_score" "d.float" DEFAULT NULL, -- LOL special

    CONSTRAINT "pk.past_game_player_stats"
        PRIMARY KEY("id"),

    CONSTRAINT "fk.past_game_player_stats.game"
        FOREIGN KEY ("stats_game_id")
        REFERENCES "past_game_stats" ("id")
        ON UPDATE RESTRICT
        ON DELETE CASCADE,

    CONSTRAINT "uq.past_game_player_stats.src_game_team"
        UNIQUE ("stats_game_id", "data_src_player_id")
);


CREATE SEQUENCE "s.past_game_team_stats";
CREATE TABLE "past_game_team_stats" (
    "id" "d.primary_key" DEFAULT nextval('"s.past_game_team_stats"'),
    "stats_game_id" "d.foreign_key" NOT NULL,
    "data_src_url" VARCHAR(255),
    "data_src_team_id" "d.int",
    "bomb_plant" "d.smallint" DEFAULT NULL, -- CS:GO special
    "bomb_defuse" "d.smallint" DEFAULT NULL, -- CS:GO special
    "round_win" "d.smallint" DEFAULT NULL, -- CS:GO special
    "round_lose" "d.smallint" DEFAULT NULL, -- CS:GO special
    "team_win" "d.smallint" DEFAULT NULL, -- DOTA2 special
    "team_lose" "d.smallint" DEFAULT NULL, -- DOTA2 special
    "turret" "d.smallint" DEFAULT NULL, -- LOL special
    "dragon" "d.smallint" DEFAULT NULL, -- LOL special
    "baron" "d.smallint" DEFAULT NULL, -- LOL special

    CONSTRAINT "pk.past_game_team_stats"
        PRIMARY KEY("id"),

    CONSTRAINT "fk.past_game_team_stats.game"
        FOREIGN KEY ("stats_game_id")
        REFERENCES "past_game_stats" ("id")
        ON UPDATE RESTRICT
        ON DELETE CASCADE,

    CONSTRAINT "uq.past_game_team_stats.src_game_team"
        UNIQUE ("stats_game_id", "data_src_team_id")
);


CREATE TABLE "past_game_analysis" (
    "data_src" "d.data_src",
    "game_name" "d.game_name",
    "matches_total_count" "d.smallint" DEFAULT 0,
    "matches_invalid_count" "d.smallint" DEFAULT 0,
    "games_total_count" "d.smallint" DEFAULT 0,
    "games_invalid_count" "d.smallint" DEFAULT 0,
    "datapoints_wanted_count" "d.smallint" DEFAULT 0,
    "datapoints_missing_count" "d.smallint" DEFAULT 0,
    "datapoints_unavailable_count" "d.smallint" DEFAULT 0, -- None value
    "analysis_update_datetime" "d.datetime" DEFAULT NULL,

    CONSTRAINT "uq.past_game_analysis.src_game"
        UNIQUE ("data_src", "game_name")
);

INSERT INTO "past_game_analysis" ("data_src", "game_name") VALUES ('provider1', 'csgo');
INSERT INTO "past_game_analysis" ("data_src", "game_name") VALUES ('provider1', 'dota2');
INSERT INTO "past_game_analysis" ("data_src", "game_name") VALUES ('provider1', 'lol');
INSERT INTO "past_game_analysis" ("data_src", "game_name") VALUES ('provider2', 'csgo');
INSERT INTO "past_game_analysis" ("data_src", "game_name") VALUES ('provider2', 'dota2');
INSERT INTO "past_game_analysis" ("data_src", "game_name") VALUES ('provider2', 'lol');
