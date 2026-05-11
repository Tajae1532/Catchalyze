-- Enable RLS on beta_applications table
ALTER TABLE beta_applications ENABLE ROW LEVEL SECURITY;

-- Allow anyone to insert beta applications (public form)
CREATE POLICY "Anyone can submit beta applications" ON beta_applications
FOR INSERT 
WITH CHECK (true);

-- Only allow service role to read/update beta applications (for admin review)
CREATE POLICY "Service role can manage beta applications" ON beta_applications
FOR ALL
USING (auth.role() = 'service_role');

-- Allow authenticated users to view their own applications
CREATE POLICY "Users can view their own beta applications" ON beta_applications
FOR SELECT
USING (auth.jwt() ->> 'email' = email);