DROP TABLE IF EXISTS user;

CREATE TABLE user (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  spotify_id TEXT UNIQUE NOT NULL,
  display_name TEXT NOT NULL,
  auth_code TEXT,
  access_token TEXT,
  songs TEXT
);