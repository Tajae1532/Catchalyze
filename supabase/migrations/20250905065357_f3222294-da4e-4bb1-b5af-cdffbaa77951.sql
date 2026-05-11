-- Fix critical OAuth client secrets exposure vulnerability
-- Remove public access to zendesk_oauth_clients table containing sensitive client secrets

-- Drop the dangerous "allow all operations" policy that exposes client secrets
DROP POLICY "Allow all operations on zendesk oauth clients" ON zendesk_oauth_clients;

-- Ensure RLS is enabled (should already be, but being explicit)
ALTER TABLE zendesk_oauth_clients ENABLE ROW LEVEL SECURITY;

-- DO NOT create any policies for authenticated users
-- This table should only be accessible via service role for backend operations
-- Client secrets must never be exposed to frontend/authenticated users

-- Add comment for clarity
COMMENT ON TABLE zendesk_oauth_clients IS 'Contains OAuth client secrets - service role access only, no user policies';

-- Also secure the zendesk_oauth_tokens table which may contain sensitive tokens
DROP POLICY IF EXISTS "Allow all operations on zendesk oauth tokens" ON zendesk_oauth_tokens;
ALTER TABLE zendesk_oauth_tokens ENABLE ROW LEVEL SECURITY;
COMMENT ON TABLE zendesk_oauth_tokens IS 'Contains OAuth access tokens - service role access only, no user policies';

-- Also secure slack_oauth_tokens table for consistency
ALTER TABLE slack_oauth_tokens ENABLE ROW LEVEL SECURITY;
COMMENT ON TABLE slack_oauth_tokens IS 'Contains OAuth access tokens - service role access only, no user policies';