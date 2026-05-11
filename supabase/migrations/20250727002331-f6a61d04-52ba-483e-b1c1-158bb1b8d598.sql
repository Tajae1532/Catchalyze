-- Create zendesk_oauth_clients table for dual-client support
create table if not exists zendesk_oauth_clients (
  subdomain text primary key,
  client_id text not null,
  client_secret text not null,
  scopes text default 'read write',
  redirect_uri text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Create zendesk_integrations table to track webhook/trigger IDs
create table if not exists zendesk_integrations (
  subdomain text primary key,
  webhook_id text,
  trigger_id text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Add updated_at triggers for the new tables
CREATE TRIGGER update_zendesk_oauth_clients_updated_at
  BEFORE UPDATE ON zendesk_oauth_clients
  FOR EACH ROW
  EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_zendesk_integrations_updated_at
  BEFORE UPDATE ON zendesk_integrations
  FOR EACH ROW
  EXECUTE FUNCTION public.update_updated_at_column();