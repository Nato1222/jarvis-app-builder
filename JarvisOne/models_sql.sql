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
  status TEXT, -- e.g., pending_approval, approved
  details JSON, -- To store financials, phases etc. as a JSON string
  ceo_notes TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES users(user_id)
);

-- Board Messages table (replaces the old 'messages' table)
-- This stores the live chat feed for a strategy discussion.
CREATE TABLE IF NOT EXISTS board_messages (
    msg_id TEXT PRIMARY KEY,
    strategy_id TEXT,
    actor TEXT,
    type TEXT,
    message TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(strategy_id) REFERENCES strategies(strategy_id)
);

-- Missions table (updated for JarvisAgent execution)
CREATE TABLE IF NOT EXISTS missions (
    mission_id TEXT PRIMARY KEY,
    strategy_id TEXT NOT NULL,
    title TEXT NOT NULL, -- This will be the mission description for Jarvis
    assigned_agent TEXT,
    status TEXT NOT NULL DEFAULT 'pending', -- pending, in_progress, completed
    result TEXT, -- To store the report from JarvisAgent
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (strategy_id) REFERENCES strategies(strategy_id)
);

-- Mission metrics (editable key/value metrics per mission)
CREATE TABLE IF NOT EXISTS mission_metrics (
  mission_id TEXT NOT NULL,
  key TEXT NOT NULL,
  value TEXT,
  PRIMARY KEY (mission_id, key),
  FOREIGN KEY (mission_id) REFERENCES missions(mission_id)
);

-- Mission activities (timeline entries with optional JSON details)
CREATE TABLE IF NOT EXISTS mission_activities (
  activity_id TEXT PRIMARY KEY,
  mission_id TEXT NOT NULL,
  time TEXT DEFAULT CURRENT_TIMESTAMP,
  action TEXT NOT NULL,
  status TEXT NOT NULL, -- completed | in-progress | pending | blocked
  details TEXT, -- JSON string with arbitrary details
  FOREIGN KEY (mission_id) REFERENCES missions(mission_id)
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
