DROP POLICY "Users can view all tickets" ON tickets;
CREATE POLICY "Users can view account tickets" ON tickets 
FOR SELECT USING (
  account_id IN (
    SELECT account_id FROM user_accounts WHERE user_id = auth.uid()
  )
);

DROP POLICY "Users can view all slack messages" ON slack_messages;
CREATE POLICY "Users can view account slack messages" ON slack_messages 
FOR SELECT USING (
  account_id IN (
    SELECT account_id FROM user_accounts WHERE user_id = auth.uid()
  )
);

DROP POLICY "Users can view all customers" ON customers;
CREATE POLICY "Users can view account customers" ON customers 
FOR SELECT USING (
  account_id IN (
    SELECT account_id FROM user_accounts WHERE user_id = auth.uid()
  )
);

DROP POLICY "Users can view all insights" ON insights;
CREATE POLICY "Users can view account insights" ON insights 
FOR SELECT USING (
  account_id IN (
    SELECT account_id FROM user_accounts WHERE user_id = auth.uid()
  )
);

CREATE POLICY "Users can insert account tickets" ON tickets 
FOR INSERT WITH CHECK (
  account_id IN (SELECT account_id FROM user_accounts WHERE user_id = auth.uid())
);

CREATE POLICY "Users can update account tickets" ON tickets 
FOR UPDATE USING (
  account_id IN (SELECT account_id FROM user_accounts WHERE user_id = auth.uid())
);

-- Slack message summaries (with type casting)
DROP POLICY "Users can view all slack message summaries" ON slack_message_summaries;
CREATE POLICY "Users can view account slack message summaries" ON slack_message_summaries
FOR SELECT USING (
  slack_message_id::text IN (
    SELECT id::text FROM slack_messages WHERE account_id IN (
      SELECT account_id FROM user_accounts WHERE user_id = auth.uid()
    )
  )
);

-- Ticket summaries (with type casting)
DROP POLICY "Users can view all ticket summaries" ON ticket_summaries;
CREATE POLICY "Users can view account ticket summaries" ON ticket_summaries
FOR SELECT USING (
  ticket_id::text IN (
    SELECT id::text FROM tickets WHERE account_id IN (
      SELECT account_id FROM user_accounts WHERE user_id = auth.uid()
    )
  )
);

-- Insight evidence (with type casting)
DROP POLICY "Users can view all insight evidence" ON insight_evidence;
CREATE POLICY "Users can view account insight evidence" ON insight_evidence
FOR SELECT USING (
  insight_id::text IN (
    SELECT id::text FROM insights WHERE account_id IN (
      SELECT account_id FROM user_accounts WHERE user_id = auth.uid()
    )
  )
);

-- Add missing customer policies
CREATE POLICY "Users can insert account customers" ON customers
FOR INSERT WITH CHECK (
  account_id IN (SELECT account_id FROM user_accounts WHERE user_id = auth.uid())
);

CREATE POLICY "Users can update account customers" ON customers
FOR UPDATE USING (
  account_id IN (SELECT account_id FROM user_accounts WHERE user_id = auth.uid())
);

-- Add missing slack message policies
CREATE POLICY "Users can insert account slack messages" ON slack_messages
FOR INSERT WITH CHECK (
  account_id IN (SELECT account_id FROM user_accounts WHERE user_id = auth.uid())
);

-- Add missing insight policies
CREATE POLICY "Users can insert account insights" ON insights
FOR INSERT WITH CHECK (
  account_id IN (SELECT account_id FROM user_accounts WHERE user_id = auth.uid())
);

CREATE POLICY "Users can update account insights" ON insights
FOR UPDATE USING (
  account_id IN (SELECT account_id FROM user_accounts WHERE user_id = auth.uid())
);