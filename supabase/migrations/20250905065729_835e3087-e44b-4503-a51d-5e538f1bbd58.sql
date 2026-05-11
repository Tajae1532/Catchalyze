-- Fix critical customer account mapping data exposure vulnerability
-- Secure slack_account_mapping and zendesk_account_mapping tables

-- Drop dangerous policies that expose account mapping data publicly
DROP POLICY "Allow service role access to slack mappings" ON slack_account_mapping;
DROP POLICY "Allow service role access to zendesk mappings" ON zendesk_account_mapping;

-- Secure slack_account_mapping with account-scoped policies
CREATE POLICY "Users can view their account slack mappings" ON slack_account_mapping
FOR SELECT USING (
  account_id IN (
    SELECT account_id FROM user_accounts WHERE user_id = auth.uid()
  )
);

-- Backend operations for slack mappings (via service role only)
CREATE POLICY "Service role can manage slack mappings" ON slack_account_mapping
FOR ALL USING (
  auth.role() = 'service_role'
);

-- Secure zendesk_account_mapping with account-scoped policies  
CREATE POLICY "Users can view their account zendesk mappings" ON zendesk_account_mapping
FOR SELECT USING (
  account_id IN (
    SELECT account_id FROM user_accounts WHERE user_id = auth.uid()
  )
);

-- Backend operations for zendesk mappings (via service role only)
CREATE POLICY "Service role can manage zendesk mappings" ON zendesk_account_mapping
FOR ALL USING (
  auth.role() = 'service_role'
);

-- Add comments documenting the security model
COMMENT ON TABLE slack_account_mapping IS 'Account-scoped Slack workspace mappings - users can only see their own account mappings';
COMMENT ON TABLE zendesk_account_mapping IS 'Account-scoped Zendesk subdomain mappings - users can only see their own account mappings';