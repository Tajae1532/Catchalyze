-- Create zendesk_oauth_tokens table
CREATE TABLE public.zendesk_oauth_tokens (
    id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
    subdomain TEXT NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_type TEXT DEFAULT 'bearer',
    scope TEXT,
    expires_at TIMESTAMP WITH TIME ZONE,
    installed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Enable Row Level Security
ALTER TABLE public.zendesk_oauth_tokens ENABLE ROW LEVEL SECURITY;

-- Create policies for zendesk oauth tokens
CREATE POLICY "Users can insert zendesk oauth tokens" 
ON public.zendesk_oauth_tokens 
FOR INSERT 
WITH CHECK (true);

CREATE POLICY "Users can update zendesk oauth tokens" 
ON public.zendesk_oauth_tokens 
FOR UPDATE 
USING (true);

CREATE POLICY "Users can view all zendesk oauth tokens" 
ON public.zendesk_oauth_tokens 
FOR SELECT 
USING (true);

-- Create trigger for automatic timestamp updates
CREATE TRIGGER update_zendesk_oauth_tokens_updated_at
BEFORE UPDATE ON public.zendesk_oauth_tokens
FOR EACH ROW
EXECUTE FUNCTION public.update_updated_at_column();

-- Create index on subdomain for faster lookups
CREATE INDEX idx_zendesk_oauth_tokens_subdomain ON public.zendesk_oauth_tokens(subdomain);