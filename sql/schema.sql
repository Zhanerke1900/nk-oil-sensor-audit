PRAGMA foreign_keys = ON;
CREATE TABLE wells (
    well_id TEXT PRIMARY KEY,
    well_type TEXT NOT NULL CHECK(well_type IN ('fountain','sucker_rod_pump'))
);
CREATE TABLE parameters (
    parameter TEXT PRIMARY KEY,
    unit TEXT NOT NULL,
    applicable_well_type TEXT NOT NULL
);
CREATE TABLE well_parameters (
    well_id TEXT NOT NULL REFERENCES wells(well_id),
    parameter TEXT NOT NULL REFERENCES parameters(parameter),
    PRIMARY KEY (well_id, parameter)
);
CREATE TABLE observations (
    observation_id INTEGER PRIMARY KEY,
    well_id TEXT NOT NULL,
    parameter TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    value REAL NOT NULL,
    n_obs INTEGER NOT NULL CHECK(n_obs > 0),
    split TEXT NOT NULL CHECK(split IN ('train','test')),
    flag TEXT NOT NULL,
    regime TEXT NOT NULL,
    scale_period TEXT NOT NULL,
    scale_review INTEGER NOT NULL CHECK(scale_review IN (0,1)),
    FOREIGN KEY (well_id, parameter) REFERENCES well_parameters(well_id, parameter),
    UNIQUE (well_id, parameter, timestamp)
);
CREATE TABLE flags (
    flag_name TEXT PRIMARY KEY
);
CREATE TABLE observation_flags (
    observation_id INTEGER NOT NULL REFERENCES observations(observation_id),
    flag_name TEXT NOT NULL REFERENCES flags(flag_name),
    PRIMARY KEY (observation_id, flag_name)
);
CREATE INDEX idx_observation_time ON observations(timestamp);
CREATE INDEX idx_observation_split ON observations(split);
