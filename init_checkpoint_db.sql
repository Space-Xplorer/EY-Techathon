-- Initialize PostgreSQL database for LangGraph checkpoints
-- This script runs automatically when the container starts

CREATE TABLE IF NOT EXISTS checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    checkpoint JSONB NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (thread_id, checkpoint_id)
);

CREATE INDEX IF NOT EXISTS idx_checkpoints_thread ON checkpoints(thread_id);
CREATE INDEX IF NOT EXISTS idx_checkpoints_created ON checkpoints(created_at);

-- Grant permissions
GRANT ALL PRIVILEGES ON TABLE checkpoints TO postgres;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Checkpoint database initialized successfully';
END $$;
