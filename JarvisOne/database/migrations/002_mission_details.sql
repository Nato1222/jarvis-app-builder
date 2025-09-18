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