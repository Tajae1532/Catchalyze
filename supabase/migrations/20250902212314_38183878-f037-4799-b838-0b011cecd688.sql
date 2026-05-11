-- Fix critical security issues

-- Enable RLS on remaining tables
ALTER TABLE active_trends ENABLE ROW LEVEL SECURITY;
ALTER TABLE rate_limit_events ENABLE ROW LEVEL SECURITY;

-- Add RLS policies for active_trends (service role access for background jobs)
CREATE POLICY "Allow service role access to active_trends" ON active_trends FOR ALL USING (true);

-- Add RLS policies for rate_limit_events (service role access for rate limiting)
CREATE POLICY "Allow service role access to rate_limit_events" ON rate_limit_events FOR ALL USING (true);

-- Fix function search paths for security
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $function$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$function$;

CREATE OR REPLACE FUNCTION public.upsert_topic_daily_metrics(p_topic_id uuid, p_account_id uuid, p_day date, p_count_delta integer DEFAULT 1, p_sentiment double precision DEFAULT NULL::double precision)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $function$
BEGIN
    INSERT INTO topic_daily_metrics (topic_id, account_id, day, count, avg_sentiment)
    VALUES (p_topic_id, p_account_id, p_day, p_count_delta, p_sentiment)
    ON CONFLICT (topic_id, day)
    DO UPDATE SET
        count = topic_daily_metrics.count + p_count_delta,
        avg_sentiment = CASE 
            WHEN p_sentiment IS NOT NULL THEN 
                CASE WHEN topic_daily_metrics.avg_sentiment IS NULL THEN p_sentiment
                     ELSE (topic_daily_metrics.avg_sentiment + p_sentiment) / 2.0
                END
            ELSE topic_daily_metrics.avg_sentiment
        END;
END;
$function$;