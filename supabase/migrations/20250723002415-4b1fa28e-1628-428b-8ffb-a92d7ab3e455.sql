-- Create slack_oauth_tokens table for storing Slack workspace authentication
CREATE TABLE public.slack_oauth_tokens (
    id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
    workspace_id TEXT NOT NULL UNIQUE,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    expires_at TIMESTAMP WITH TIME ZONE,
    installed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Enable Row Level Security
ALTER TABLE public.slack_oauth_tokens ENABLE ROW LEVEL SECURITY;

-- Create permissive policies for now
CREATE POLICY "Users can view all slack oauth tokens" 
ON public.slack_oauth_tokens 
FOR SELECT 
USING (true);

CREATE POLICY "Users can insert slack oauth tokens" 
ON public.slack_oauth_tokens 
FOR INSERT 
WITH CHECK (true);

CREATE POLICY "Users can update slack oauth tokens" 
ON public.slack_oauth_tokens 
FOR UPDATE 
USING (true);

-- Add trigger for automatic timestamp updates
CREATE TRIGGER update_slack_oauth_tokens_updated_at
BEFORE UPDATE ON public.slack_oauth_tokens
FOR EACH ROW
EXECUTE FUNCTION public.update_updated_at_column();

-- Create index for workspace_id lookups
CREATE INDEX idx_slack_oauth_tokens_workspace_id ON public.slack_oauth_tokens(workspace_id);