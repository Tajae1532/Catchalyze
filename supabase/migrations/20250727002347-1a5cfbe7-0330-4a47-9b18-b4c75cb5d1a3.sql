-- Enable RLS on the new tables and add policies
ALTER TABLE zendesk_oauth_clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE zendesk_integrations ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for zendesk_oauth_clients
CREATE POLICY "Allow all operations on zendesk oauth clients" 
ON zendesk_oauth_clients 
FOR ALL 
USING (true)
WITH CHECK (true);

-- Create RLS policies for zendesk_integrations  
CREATE POLICY "Allow all operations on zendesk integrations" 
ON zendesk_integrations 
FOR ALL 
USING (true)
WITH CHECK (true);