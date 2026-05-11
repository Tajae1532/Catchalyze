-- Create customers table
CREATE TABLE public.customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    email TEXT,
    zendesk_id TEXT UNIQUE,
    slack_workspace_id TEXT,
    health_score INTEGER DEFAULT 50 CHECK (health_score >= 0 AND health_score <= 100),
    churn_risk TEXT DEFAULT 'low' CHECK (churn_risk IN ('low', 'medium', 'high')),
    sentiment_score DECIMAL DEFAULT 0.0,
    last_interaction TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Create tickets table
CREATE TABLE public.tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES public.customers(id) ON DELETE CASCADE,
    zendesk_ticket_id TEXT UNIQUE NOT NULL,
    subject TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'open' CHECK (status IN ('open', 'pending', 'solved', 'closed')),
    priority TEXT DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    sentiment_score DECIMAL,
    ai_summary TEXT,
    tags TEXT[],
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Create slack_messages table
CREATE TABLE public.slack_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES public.customers(id) ON DELETE SET NULL,
    slack_channel_id TEXT NOT NULL,
    slack_message_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    text TEXT NOT NULL,
    sentiment_score DECIMAL,
    mentions TEXT[],
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(slack_channel_id, slack_message_id)
);

-- Create insights table
CREATE TABLE public.insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    severity TEXT DEFAULT 'medium' CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    affected_customers INTEGER DEFAULT 0,
    data JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Create indexes for better performance
CREATE INDEX idx_customers_zendesk_id ON public.customers(zendesk_id);
CREATE INDEX idx_customers_health_score ON public.customers(health_score);
CREATE INDEX idx_customers_churn_risk ON public.customers(churn_risk);

CREATE INDEX idx_tickets_customer_id ON public.tickets(customer_id);
CREATE INDEX idx_tickets_zendesk_id ON public.tickets(zendesk_ticket_id);
CREATE INDEX idx_tickets_status ON public.tickets(status);
CREATE INDEX idx_tickets_created_at ON public.tickets(created_at);

CREATE INDEX idx_slack_messages_customer_id ON public.slack_messages(customer_id);
CREATE INDEX idx_slack_messages_channel_message ON public.slack_messages(slack_channel_id, slack_message_id);
CREATE INDEX idx_slack_messages_created_at ON public.slack_messages(created_at);

CREATE INDEX idx_insights_type ON public.insights(type);
CREATE INDEX idx_insights_active ON public.insights(is_active);
CREATE INDEX idx_insights_created_at ON public.insights(created_at);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers to auto-update updated_at columns
CREATE TRIGGER update_customers_updated_at
    BEFORE UPDATE ON public.customers
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_tickets_updated_at
    BEFORE UPDATE ON public.tickets
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_insights_updated_at
    BEFORE UPDATE ON public.insights
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- Enable Row Level Security (but allow all operations for now)
ALTER TABLE public.customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.slack_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.insights ENABLE ROW LEVEL SECURITY;

-- Create permissive policies for now (can be tightened later with authentication)
CREATE POLICY "Allow all operations on customers" ON public.customers FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all operations on tickets" ON public.tickets FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all operations on slack_messages" ON public.slack_messages FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all operations on insights" ON public.insights FOR ALL USING (true) WITH CHECK (true);