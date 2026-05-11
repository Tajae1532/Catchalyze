-- CustomerWhisperer Grounded Insight Schema Migration
-- Extends existing insights table and adds new schema elements
-- Postgres 15 (Supabase) - Idempotent DDL

-- Ensure pgcrypto extension for gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Create enums (idempotent)
DO $$ 
BEGIN
    CREATE TYPE insight_type AS ENUM ('trend','churn_risk','bug','ux_friction','feature_request','process_gap');
EXCEPTION 
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ 
BEGIN
    CREATE TYPE insight_severity AS ENUM ('low','medium','high','critical');
EXCEPTION 
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ 
BEGIN
    CREATE TYPE owner_hint AS ENUM ('CS','Support','PM','Eng','Sales');
EXCEPTION 
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ 
BEGIN
    CREATE TYPE time_cost_hint AS ENUM ('S','M','L');
EXCEPTION 
    WHEN duplicate_object THEN NULL;
END $$;

-- Drop existing constraints that conflict with our new schema
DO $$
BEGIN
    -- Drop existing type constraint
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'insights_type_check') THEN
        ALTER TABLE insights DROP CONSTRAINT insights_type_check;
    END IF;
    
    -- Drop existing severity constraint
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'insights_severity_check') THEN
        ALTER TABLE insights DROP CONSTRAINT insights_severity_check;
    END IF;
END $$;

-- Update existing type values to match new enum
UPDATE insights SET type = 'trend' WHERE type IN ('trending_issue', 'sentiment_spike');

-- Convert type column to enum
DO $$
BEGIN
    -- Check if the column is still text type
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'insights' AND column_name = 'type' 
        AND data_type = 'text'
    ) THEN
        -- Convert existing type column to use the enum
        ALTER TABLE insights ALTER COLUMN type TYPE insight_type USING type::insight_type;
    END IF;
END $$;

-- Convert severity column to enum (handling the default value issue)
DO $$
BEGIN
    -- Check if the column is still text type
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'insights' AND column_name = 'severity' 
        AND data_type = 'text'
    ) THEN
        -- First drop the default
        ALTER TABLE insights ALTER COLUMN severity DROP DEFAULT;
        -- Convert existing severity column to use the enum
        ALTER TABLE insights ALTER COLUMN severity TYPE insight_severity USING severity::insight_severity;
        -- Add back the default with enum type
        ALTER TABLE insights ALTER COLUMN severity SET DEFAULT 'medium'::insight_severity;
    END IF;
END $$;

-- Extend existing insights table with new columns (idempotent)
DO $$
BEGIN
    -- Add confidence column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'insights' AND column_name = 'confidence') THEN
        ALTER TABLE insights ADD COLUMN confidence numeric(3,2) NOT NULL DEFAULT 0.70;
    END IF;
    
    -- Add impact_score column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'insights' AND column_name = 'impact_score') THEN
        ALTER TABLE insights ADD COLUMN impact_score smallint NOT NULL DEFAULT 0;
    END IF;
    
    -- Add novelty_score column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'insights' AND column_name = 'novelty_score') THEN
        ALTER TABLE insights ADD COLUMN novelty_score smallint NOT NULL DEFAULT 0;
    END IF;
    
    -- Add recommended_action column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'insights' AND column_name = 'recommended_action') THEN
        ALTER TABLE insights ADD COLUMN recommended_action text;
    END IF;
    
    -- Add playbook_steps column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'insights' AND column_name = 'playbook_steps') THEN
        ALTER TABLE insights ADD COLUMN playbook_steps text[];
    END IF;
    
    -- Add why_now column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'insights' AND column_name = 'why_now') THEN
        ALTER TABLE insights ADD COLUMN why_now text;
    END IF;
    
    -- Add owner_hint column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'insights' AND column_name = 'owner_hint') THEN
        ALTER TABLE insights ADD COLUMN owner_hint owner_hint;
    END IF;
    
    -- Add time_cost_hint column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'insights' AND column_name = 'time_cost_hint') THEN
        ALTER TABLE insights ADD COLUMN time_cost_hint time_cost_hint;
    END IF;
    
    -- Add prompt_version column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'insights' AND column_name = 'prompt_version') THEN
        ALTER TABLE insights ADD COLUMN prompt_version text NOT NULL DEFAULT 'v1';
    END IF;
    
    -- Add snooze_until column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'insights' AND column_name = 'snooze_until') THEN
        ALTER TABLE insights ADD COLUMN snooze_until timestamptz;
    END IF;
    
    -- Add dismissed_until column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'insights' AND column_name = 'dismissed_until') THEN
        ALTER TABLE insights ADD COLUMN dismissed_until timestamptz;
    END IF;
END $$;

-- Add new constraints (idempotent)
DO $$
BEGIN
    -- confidence constraint
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'insights_confidence_check') THEN
        ALTER TABLE insights ADD CONSTRAINT insights_confidence_check 
        CHECK (confidence >= 0 AND confidence <= 1);
    END IF;
    
    -- impact_score constraint
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'insights_impact_score_check') THEN
        ALTER TABLE insights ADD CONSTRAINT insights_impact_score_check 
        CHECK (impact_score BETWEEN 0 AND 100);
    END IF;
    
    -- novelty_score constraint
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'insights_novelty_score_check') THEN
        ALTER TABLE insights ADD CONSTRAINT insights_novelty_score_check 
        CHECK (novelty_score BETWEEN 0 AND 100);
    END IF;
    
    -- playbook_steps constraint
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'insights_playbook_steps_check') THEN
        ALTER TABLE insights ADD CONSTRAINT insights_playbook_steps_check 
        CHECK (coalesce(array_length(playbook_steps,1),0) <= 3);
    END IF;
END $$;

-- Indexes for insights table
CREATE INDEX IF NOT EXISTS idx_insights_created_at_desc ON insights (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_insights_type_severity ON insights (type, severity);
CREATE INDEX IF NOT EXISTS idx_insights_is_active ON insights (is_active);
CREATE INDEX IF NOT EXISTS idx_insights_data_gin ON insights USING GIN (data jsonb_path_ops);

-- Evidence linking table (many-to-many polymorphic)
CREATE TABLE IF NOT EXISTS insight_evidence (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    insight_id uuid NOT NULL REFERENCES insights(id) ON DELETE CASCADE,
    ticket_id uuid REFERENCES tickets(id) ON DELETE CASCADE,
    slack_message_id uuid REFERENCES slack_messages(id) ON DELETE CASCADE,
    evidence_snippet text NOT NULL,
    evidence_sentiment numeric(3,2),
    created_at timestamptz NOT NULL DEFAULT now(),
    -- Add constraints inline for new table creation
    CONSTRAINT insight_evidence_exactly_one_check CHECK ((ticket_id IS NOT NULL) <> (slack_message_id IS NOT NULL)),
    CONSTRAINT insight_evidence_snippet_length_check CHECK (char_length(evidence_snippet) <= 280)
);

-- Partial unique indexes for insight_evidence (prevent duplicates)
CREATE UNIQUE INDEX IF NOT EXISTS idx_insight_evidence_ticket_unique 
ON insight_evidence (insight_id, ticket_id) WHERE ticket_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_insight_evidence_slack_unique 
ON insight_evidence (insight_id, slack_message_id) WHERE slack_message_id IS NOT NULL;

-- Regular indexes for insight_evidence
CREATE INDEX IF NOT EXISTS idx_insight_evidence_insight_id ON insight_evidence (insight_id);
CREATE INDEX IF NOT EXISTS idx_insight_evidence_ticket_id ON insight_evidence (ticket_id) WHERE ticket_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_insight_evidence_slack_message_id ON insight_evidence (slack_message_id) WHERE slack_message_id IS NOT NULL;

-- Summary cache tables to protect token budgets
CREATE TABLE IF NOT EXISTS ticket_summaries (
    ticket_id uuid PRIMARY KEY REFERENCES tickets(id) ON DELETE CASCADE,
    one_line text NOT NULL,
    token_estimate integer NOT NULL DEFAULT 0,
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ticket_summaries_one_line_length_check CHECK (char_length(one_line) <= 200)
);

CREATE TABLE IF NOT EXISTS slack_message_summaries (
    slack_message_id uuid PRIMARY KEY REFERENCES slack_messages(id) ON DELETE CASCADE,
    one_line text NOT NULL,
    token_estimate integer NOT NULL DEFAULT 0,
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT slack_message_summaries_one_line_length_check CHECK (char_length(one_line) <= 200)
);

-- Triggers for auto-updating updated_at (idempotent)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_insights_updated_at') THEN
        CREATE TRIGGER update_insights_updated_at
            BEFORE UPDATE ON insights
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_ticket_summaries_updated_at') THEN
        CREATE TRIGGER update_ticket_summaries_updated_at
            BEFORE UPDATE ON ticket_summaries
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_slack_message_summaries_updated_at') THEN
        CREATE TRIGGER update_slack_message_summaries_updated_at
            BEFORE UPDATE ON slack_message_summaries
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

-- Convenience view: insights with evidence counts
CREATE OR REPLACE VIEW insights_with_counts AS
SELECT 
    i.id,
    i.title,
    i.type,
    i.severity,
    i.confidence,
    i.impact_score,
    i.novelty_score,
    i.created_at,
    COALESCE(e.evidence_count, 0) as evidence_count
FROM insights i
LEFT JOIN (
    SELECT 
        insight_id, 
        COUNT(*) as evidence_count
    FROM insight_evidence 
    GROUP BY insight_id
) e ON i.id = e.insight_id;