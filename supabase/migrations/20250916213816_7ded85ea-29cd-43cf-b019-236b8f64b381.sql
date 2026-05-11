-- Add encryption_version column to track formats
ALTER TABLE zendesk_oauth_clients 
ADD COLUMN encryption_version TEXT DEFAULT 'legacy';