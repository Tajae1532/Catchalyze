-- Fix RLS security issues for new tables
-- Enable RLS and add policies for insight_evidence, ticket_summaries, slack_message_summaries

-- Enable RLS on insight_evidence table
ALTER TABLE insight_evidence ENABLE ROW LEVEL SECURITY;

-- Create policies for insight_evidence
CREATE POLICY "Users can view all insight evidence" 
ON insight_evidence 
FOR SELECT 
USING (true);

CREATE POLICY "Users can insert insight evidence" 
ON insight_evidence 
FOR INSERT 
WITH CHECK (true);

CREATE POLICY "Users can update insight evidence" 
ON insight_evidence 
FOR UPDATE 
USING (true);

CREATE POLICY "Users can delete insight evidence" 
ON insight_evidence 
FOR DELETE 
USING (true);

-- Enable RLS on ticket_summaries table  
ALTER TABLE ticket_summaries ENABLE ROW LEVEL SECURITY;

-- Create policies for ticket_summaries
CREATE POLICY "Users can view all ticket summaries" 
ON ticket_summaries 
FOR SELECT 
USING (true);

CREATE POLICY "Users can insert ticket summaries" 
ON ticket_summaries 
FOR INSERT 
WITH CHECK (true);

CREATE POLICY "Users can update ticket summaries" 
ON ticket_summaries 
FOR UPDATE 
USING (true);

CREATE POLICY "Users can delete ticket summaries" 
ON ticket_summaries 
FOR DELETE 
USING (true);

-- Enable RLS on slack_message_summaries table
ALTER TABLE slack_message_summaries ENABLE ROW LEVEL SECURITY;

-- Create policies for slack_message_summaries
CREATE POLICY "Users can view all slack message summaries" 
ON slack_message_summaries 
FOR SELECT 
USING (true);

CREATE POLICY "Users can insert slack message summaries" 
ON slack_message_summaries 
FOR INSERT 
WITH CHECK (true);

CREATE POLICY "Users can update slack message summaries" 
ON slack_message_summaries 
FOR UPDATE 
USING (true);

CREATE POLICY "Users can delete slack message summaries" 
ON slack_message_summaries 
FOR DELETE 
USING (true);