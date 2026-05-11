-- Fix critical security vulnerability in embeddings_store table
-- Replace overly permissive RLS policy with account-scoped restrictions

-- Drop the dangerous "allow all operations" policy
DROP POLICY "Allow all operations on embeddings_store" ON embeddings_store;

-- Create secure account-scoped RLS policies
CREATE POLICY "Users can view account embeddings" ON embeddings_store
FOR SELECT USING (
  account_id IN (
    SELECT account_id FROM user_accounts WHERE user_id = auth.uid()
  )
);

CREATE POLICY "Users can insert account embeddings" ON embeddings_store
FOR INSERT WITH CHECK (
  account_id IN (
    SELECT account_id FROM user_accounts WHERE user_id = auth.uid()
  )
);

CREATE POLICY "Users can update account embeddings" ON embeddings_store
FOR UPDATE USING (
  account_id IN (
    SELECT account_id FROM user_accounts WHERE user_id = auth.uid()
  )
);

-- Note: No DELETE policy - embeddings should be permanent for audit/compliance
-- Service role can still perform maintenance operations as needed