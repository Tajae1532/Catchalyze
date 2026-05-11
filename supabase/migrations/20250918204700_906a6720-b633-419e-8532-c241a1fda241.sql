-- Create beta_applications table for storing beta access requests
CREATE TABLE IF NOT EXISTS beta_applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    company TEXT NOT NULL,
    role TEXT NOT NULL,
    current_tools TEXT NOT NULL,
    time_spent_weekly TEXT NOT NULL,
    pain_points TEXT NOT NULL,
    company_size TEXT NOT NULL,
    why_interested TEXT NOT NULL,
    ready_to_pay BOOLEAN NOT NULL,
    start_timeline TEXT NOT NULL,
    ip_address INET,
    user_agent TEXT,
    submitted_at TIMESTAMPTZ DEFAULT NOW(),
    status TEXT DEFAULT 'pending_review',
    reviewed_at TIMESTAMPTZ,
    invoice_sent_at TIMESTAMPTZ,
    notes TEXT
);

-- Create indexes for efficient querying
CREATE INDEX idx_beta_applications_email ON beta_applications(email);
CREATE INDEX idx_beta_applications_status ON beta_applications(status);
CREATE INDEX idx_beta_applications_submitted_at ON beta_applications(submitted_at);