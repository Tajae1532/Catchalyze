-- Create app locks table for distributed locking
CREATE TABLE IF NOT EXISTS public.app_locks (
  lock_key TEXT PRIMARY KEY,
  owner TEXT NOT NULL,
  expires_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX IF NOT EXISTS app_locks_expires_idx ON public.app_locks(expires_at);

-- Create optional run log table
CREATE TABLE IF NOT EXISTS public.insight_generation_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  finished_at TIMESTAMP WITH TIME ZONE,
  status TEXT NOT NULL, -- 'ok' | 'error' | 'skipped'
  error TEXT,
  rows_inserted INTEGER DEFAULT 0
);

-- Enable RLS on both tables
ALTER TABLE public.app_locks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.insight_generation_runs ENABLE ROW LEVEL SECURITY;

-- Allow all operations on app_locks (used for server coordination)
CREATE POLICY "Allow all operations on app locks" 
ON public.app_locks 
FOR ALL 
USING (true) 
WITH CHECK (true);

-- Allow all operations on insight generation runs (logging table)
CREATE POLICY "Allow all operations on insight runs" 
ON public.insight_generation_runs 
FOR ALL 
USING (true) 
WITH CHECK (true);