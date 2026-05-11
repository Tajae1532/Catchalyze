-- CustomerWhisperer Grounded Insight Schema Migration
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

-- Core insights table
CREATE TABLE IF NOT EXISTS insights (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    type insight_type NOT NULL,
    title text NOT NULL,
    severity insight_severity NOT NULL DEFAULT 'medium',
    confidence numeric(3,2) NOT NULL DEFAULT 0.70,
    impact_score smallint NOT NULL DEFAULT 0,
    novelty_score smallint NOT NULL DEFAULT 0,
    recommended_action text,
    playbook_steps text[],
    why_now text,
    owner_hint owner_hint,
    time_cost_hint time_cost_hint,
    affected_customers integer NOT NULL DEFAULT 0,
    data jsonb NOT NULL DEFAULT '{}'::jsonb,
    prompt_version text NOT NULL DEFAULT 'v1',
    is_active boolean NOT NULL DEFAULT true,
    snooze_until timestamptz,
    dismissed_until timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- Add constraints to insights table (idempotent)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'insights_confidence_check') THEN
        ALTER TABLE insights ADD CONSTRAINT insights_confidence_check 
        CHECK (confidence >= 0 AND confidence <= 1);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'insights_impact_score_check') THEN
        ALTER TABLE insights ADD CONSTRAINT insights_impact_score_check 
        CHECK (impact_score BETWEEN 0 AND 100);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'insights_novelty_score_check') THEN
        ALTER TABLE insights ADD CONSTRAINT insights_novelty_score_check 
        CHECK (novelty_score BETWEEN 0 AND 100);
    END IF;
END $$;

DO $$
BEGIN
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
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Add constraints to insight_evidence table (idempotent)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'insight_evidence_exactly_one_check') THEN
        ALTER TABLE insight_evidence ADD CONSTRAINT insight_evidence_exactly_one_check 
        CHECK ((ticket_id IS NOT NULL) <> (slack_message_id IS NOT NULL));
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'insight_evidence_snippet_length_check') THEN
        ALTER TABLE insight_evidence ADD CONSTRAINT insight_evidence_snippet_length_check 
        CHECK (char_length(evidence_snippet) <= 280);
    END IF;
END $$;

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
    updated_at timestamptz NOT NULL DEFAULT now()
);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ticket_summaries_one_line_length_check') THEN
        ALTER TABLE ticket_summaries ADD CONSTRAINT ticket_summaries_one_line_length_check 
        CHECK (char_length(one_line) <= 200);
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS slack_message_summaries (
    slack_message_id uuid PRIMARY KEY REFERENCES slack_messages(id) ON DELETE CASCADE,
    one_line text NOT NULL,
    token_estimate integer NOT NULL DEFAULT 0,
    updated_at timestamptz NOT NULL DEFAULT now()
);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'slack_message_summaries_one_line_length_check') THEN
        ALTER TABLE slack_message_summaries ADD CONSTRAINT slack_message_summaries_one_line_length_check 
        CHECK (char_length(one_line) <= 200);
    END IF;
END $$;

-- Auto-update trigger function for updated_at (idempotent)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

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

-- Example Usage Queries

-- 1. INSERT sample insight with evidence
-- First, insert an insight
INSERT INTO insights (
    type, 
    title, 
    severity, 
    confidence, 
    impact_score, 
    novelty_score, 
    recommended_action,
    playbook_steps,
    why_now,
    owner_hint,
    time_cost_hint,
    affected_customers,
    data
) VALUES (
    'churn_risk',
    'High-value customers showing decreased engagement',
    'high',
    0.85,
    75,
    60,
    'Proactive outreach to affected accounts within 48 hours',
    ARRAY['Schedule customer success call', 'Review usage analytics', 'Offer additional training'],
    'Engagement metrics dropped 40% in last 2 weeks across premium accounts',
    'CS',
    'M',
    12,
    '{"engagement_drop": 0.4, "affected_tiers": ["premium", "enterprise"], "avg_revenue_per_account": 15000}'::jsonb
);

-- Link evidence to the insight (replace UUIDs with actual IDs from your data)
-- Evidence from ticket
INSERT INTO insight_evidence (insight_id, ticket_id, evidence_snippet, evidence_sentiment)
SELECT 
    (SELECT id FROM insights WHERE title = 'High-value customers showing decreased engagement' LIMIT 1),
    (SELECT id FROM tickets LIMIT 1), -- Replace with actual ticket_id
    'Customer reported confusion with new dashboard layout and decreased daily usage',
    -0.3;

-- Evidence from slack message  
INSERT INTO insight_evidence (insight_id, slack_message_id, evidence_snippet, evidence_sentiment)
SELECT 
    (SELECT id FROM insights WHERE title = 'High-value customers showing decreased engagement' LIMIT 1),
    (SELECT id FROM slack_messages LIMIT 1), -- Replace with actual slack_message_id
    'CS team noting multiple customers asking for training on recent UI changes',
    -0.2;

-- 2. SELECT insights for time window with filters
-- Get insights from last 30 days with medium+ severity
SELECT 
    id,
    title,
    type,
    severity,
    confidence,
    impact_score,
    novelty_score,
    why_now,
    created_at,
    evidence_count
FROM insights_with_counts
WHERE 
    created_at >= NOW() - INTERVAL '30 days'
    AND severity IN ('medium', 'high', 'critical')
    AND type = ANY(ARRAY['churn_risk', 'ux_friction']::insight_type[])
    AND is_active = true
ORDER BY 
    impact_score DESC, 
    created_at DESC;

-- 3. SELECT insight with evidence details (JSON aggregation)
SELECT 
    i.id,
    i.title,
    i.type,
    i.severity,
    i.confidence,
    i.impact_score,
    i.recommended_action,
    i.why_now,
    i.created_at,
    COALESCE(
        json_agg(
            json_build_object(
                'kind', CASE 
                    WHEN e.ticket_id IS NOT NULL THEN 'ticket'
                    WHEN e.slack_message_id IS NOT NULL THEN 'slack_message'
                END,
                'id', COALESCE(e.ticket_id, e.slack_message_id),
                'snippet', e.evidence_snippet,
                'sentiment', e.evidence_sentiment,
                'created_at', e.created_at
            )
        ) FILTER (WHERE e.id IS NOT NULL),
        '[]'::json
    ) as evidence_items
FROM insights i
LEFT JOIN insight_evidence e ON i.id = e.insight_id
WHERE i.id = $1 -- Replace $1 with actual insight ID
GROUP BY 
    i.id, i.title, i.type, i.severity, i.confidence, 
    i.impact_score, i.recommended_action, i.why_now, i.created_at;