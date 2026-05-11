-- Multi-tenant authentication foundation schema

-- Users table for Google OAuth
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  google_id TEXT UNIQUE NOT NULL,
  name TEXT,
  avatar_url TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Accounts table for tenant isolation
CREATE TABLE accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  slug TEXT UNIQUE, -- for future custom domains
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User-account relationships (supports multiple users per account)
CREATE TABLE user_accounts (
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  account_id UUID REFERENCES accounts(id) ON DELETE CASCADE,
  role TEXT DEFAULT 'member' CHECK (role IN ('owner', 'admin', 'member')),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  PRIMARY KEY (user_id, account_id)
);

-- OAuth integration mappings for webhook routing
CREATE TABLE zendesk_account_mapping (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id UUID REFERENCES accounts(id) ON DELETE CASCADE,
  subdomain TEXT UNIQUE NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE slack_account_mapping (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id UUID REFERENCES accounts(id) ON DELETE CASCADE,
  workspace_id TEXT UNIQUE NOT NULL,
  team_name TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS on all new tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE zendesk_account_mapping ENABLE ROW LEVEL SECURITY;
ALTER TABLE slack_account_mapping ENABLE ROW LEVEL SECURITY;

-- RLS policies for users table
CREATE POLICY "Users can view their own data" ON users FOR SELECT USING (auth.uid()::text = id::text);
CREATE POLICY "Users can update their own data" ON users FOR UPDATE USING (auth.uid()::text = id::text);

-- RLS policies for accounts table  
CREATE POLICY "Users can view accounts they belong to" ON accounts FOR SELECT 
USING (id IN (SELECT account_id FROM user_accounts WHERE user_id = auth.uid()));

-- RLS policies for user_accounts table
CREATE POLICY "Users can view their account relationships" ON user_accounts FOR SELECT 
USING (user_id = auth.uid());

-- RLS policies for mapping tables (allow service role access)
CREATE POLICY "Allow service role access to zendesk mappings" ON zendesk_account_mapping FOR ALL USING (true);
CREATE POLICY "Allow service role access to slack mappings" ON slack_account_mapping FOR ALL USING (true);

-- Create development account for existing data
INSERT INTO accounts (id, name, slug) VALUES 
('00000000-0000-0000-0000-000000000000', 'Development Account', 'dev');