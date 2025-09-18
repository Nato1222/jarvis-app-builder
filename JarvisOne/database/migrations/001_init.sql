-- Users table (no changes)
CREATE TABLE IF NOT EXISTS users (
  user_id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Strategies table (updated for the new live board room structure)
CREATE TABLE IF NOT EXISTS strategies (
  strategy_id TEXT PRIMARY KEY,
  user_id INTEGER,
  topic TEXT,
  tldr TEXT,
  summary TEXT,
  status TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES users(user_id)
);

-- Board Messages table (replaces the old 'messages' table)
-- This stores the live chat feed for a strategy discussion.
CREATE TABLE IF NOT EXISTS board_messages (
    msg_id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id TEXT,
    actor TEXT,
    type TEXT,
    message TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(strategy_id) REFERENCES strategies(strategy_id)
);

-- Drop the old missions table to apply changes
DROP TABLE IF EXISTS missions;

-- Missions table (updated for JarvisAgent execution)
CREATE TABLE missions (
    mission_id TEXT PRIMARY KEY,
    strategy_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    owner TEXT,
    dependencies TEXT, -- Stored as a JSON array string
    steps TEXT, -- Stored as a JSON array string
    acceptance_criteria TEXT, -- Stored as a JSON array string
    status TEXT NOT NULL DEFAULT 'pending', -- pending, in_progress, completed
    result TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (strategy_id) REFERENCES strategies(strategy_id)
);

-- Corrections table (updated to link to board_messages for CEO interventions)
CREATE TABLE IF NOT EXISTS corrections (
    correction_id TEXT PRIMARY KEY,
    msg_id TEXT,
    corrected_text TEXT,
    reason TEXT,
    tags TEXT,
    approved BOOLEAN DEFAULT 0,
    FOREIGN KEY(msg_id) REFERENCES board_messages(msg_id)
);

-- Drafts table (for other agent outputs, can be kept for now)
CREATE TABLE IF NOT EXISTS drafts (
  draft_id INTEGER PRIMARY KEY AUTOINCREMENT,
  mission_id INTEGER,
  command TEXT,
  content TEXT,
  status TEXT DEFAULT 'pending',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Actions Log table (for tool calls, can be kept for now)
CREATE TABLE IF NOT EXISTS actions_log (
  action_id INTEGER PRIMARY KEY AUTOINCREMENT,
  mission_id INTEGER,
  step_name TEXT,
  tool_used TEXT,
  request_payload TEXT,
  response_payload TEXT,
  success INTEGER,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Drop the old 'messages' table to avoid conflicts.
-- The 'IF EXISTS' clause prevents an error if the table is already gone.
DROP TABLE IF EXISTS messages;
