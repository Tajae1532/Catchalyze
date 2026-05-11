-- Create upsert function for topic daily metrics
CREATE OR REPLACE FUNCTION upsert_topic_daily_metrics(
    p_topic_id UUID,
    p_account_id UUID,
    p_day DATE,
    p_count_delta INTEGER DEFAULT 1,
    p_sentiment DOUBLE PRECISION DEFAULT NULL
) RETURNS VOID AS $$
BEGIN
    INSERT INTO topic_daily_metrics (topic_id, account_id, day, count, avg_sentiment)
    VALUES (p_topic_id, p_account_id, p_day, p_count_delta, p_sentiment)
    ON CONFLICT (topic_id, account_id, day)
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
$$ LANGUAGE plpgsql;