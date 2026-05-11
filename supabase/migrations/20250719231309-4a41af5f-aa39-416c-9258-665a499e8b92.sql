-- Create customers table
CREATE TABLE public.customers (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT,
  zendesk_id TEXT UNIQUE,
  slack_workspace_id TEXT,
  health_score INTEGER DEFAULT 50 CHECK (health_score >= 0 AND health_score <= 100),
  sentiment_score DECIMAL(3,2) DEFAULT 0.0 CHECK (sentiment_score >= -1.0 AND sentiment_score <= 1.0),
  churn_risk TEXT DEFAULT 'low' CHECK (churn_risk IN ('low', 'medium', 'high')),
  last_interaction TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Create tickets table
CREATE TABLE public.tickets (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  customer_id UUID REFERENCES public.customers(id) ON DELETE CASCADE,
  zendesk_ticket_id TEXT UNIQUE NOT NULL,
  subject TEXT NOT NULL,
  description TEXT,
  status TEXT DEFAULT 'open' CHECK (status IN ('open', 'pending', 'resolved', 'closed')),
  priority TEXT DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
  sentiment_score DECIMAL(3,2),
  ai_summary TEXT,
  tags TEXT[],
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Create slack_messages table
CREATE TABLE public.slack_messages (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  customer_id UUID REFERENCES public.customers(id) ON DELETE CASCADE,
  slack_channel_id TEXT NOT NULL,
  slack_message_id TEXT UNIQUE NOT NULL,
  user_id TEXT NOT NULL,
  text TEXT NOT NULL,
  sentiment_score DECIMAL(3,2),
  mentions TEXT[],
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Create insights table
CREATE TABLE public.insights (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  type TEXT NOT NULL CHECK (type IN ('trending_issue', 'churn_risk', 'sentiment_spike', 'health_decline')),
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  severity TEXT DEFAULT 'medium' CHECK (severity IN ('low', 'medium', 'high', 'critical')),
  affected_customers INTEGER DEFAULT 0,
  data JSONB,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Create integrations table
CREATE TABLE public.integrations (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('zendesk', 'slack')),
  config JSONB NOT NULL,
  is_active BOOLEAN DEFAULT true,
  last_sync TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  UNIQUE(user_id, type)
);

-- Enable Row Level Security
ALTER TABLE public.customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.slack_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.insights ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.integrations ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for customers
CREATE POLICY "Users can view all customers" ON public.customers FOR SELECT USING (true);
CREATE POLICY "Users can insert customers" ON public.customers FOR INSERT WITH CHECK (true);
CREATE POLICY "Users can update customers" ON public.customers FOR UPDATE USING (true);

-- Create RLS policies for tickets
CREATE POLICY "Users can view all tickets" ON public.tickets FOR SELECT USING (true);
CREATE POLICY "Users can insert tickets" ON public.tickets FOR INSERT WITH CHECK (true);
CREATE POLICY "Users can update tickets" ON public.tickets FOR UPDATE USING (true);

-- Create RLS policies for slack_messages
CREATE POLICY "Users can view all slack messages" ON public.slack_messages FOR SELECT USING (true);
CREATE POLICY "Users can insert slack messages" ON public.slack_messages FOR INSERT WITH CHECK (true);

-- Create RLS policies for insights
CREATE POLICY "Users can view all insights" ON public.insights FOR SELECT USING (true);
CREATE POLICY "Users can insert insights" ON public.insights FOR INSERT WITH CHECK (true);
CREATE POLICY "Users can update insights" ON public.insights FOR UPDATE USING (true);

-- Create RLS policies for integrations
CREATE POLICY "Users can view their own integrations" ON public.integrations FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert their own integrations" ON public.integrations FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update their own integrations" ON public.integrations FOR UPDATE USING (auth.uid() = user_id);

-- Create function to update timestamps
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for automatic timestamp updates
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

CREATE TRIGGER update_integrations_updated_at
  BEFORE UPDATE ON public.integrations
  FOR EACH ROW
  EXECUTE FUNCTION public.update_updated_at_column();

-- Create indexes for better performance
CREATE INDEX idx_customers_zendesk_id ON public.customers(zendesk_id);
CREATE INDEX idx_tickets_customer_id ON public.tickets(customer_id);
CREATE INDEX idx_tickets_zendesk_id ON public.tickets(zendesk_ticket_id);
CREATE INDEX idx_slack_messages_customer_id ON public.slack_messages(customer_id);
CREATE INDEX idx_insights_type ON public.insights(type);
CREATE INDEX idx_insights_active ON public.insights(is_active);
CREATE INDEX idx_integrations_user_type ON public.integrations(user_id, type);