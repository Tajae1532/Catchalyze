-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Embeddings store table
CREATE TABLE public.embeddings_store (
    id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
    account_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000',
    source TEXT NOT NULL CHECK (source IN ('ticket', 'slack')),
    source_id UUID NOT NULL,
    ts TIMESTAMP WITH TIME ZONE NOT NULL,
    customer_id UUID,
    channel_id TEXT,
    one_line TEXT NOT NULL CHECK (LENGTH(one_line) <= 200),
    sentiment FLOAT,
    text_hash TEXT NOT NULL,
    embedding VECTOR(1536) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    UNIQUE (account_id, source, source_id)
);

-- Topics table
CREATE TABLE public.topics (
    topic_id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
    account_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000',
    name TEXT,
    keywords TEXT[],
    centroid VECTOR(1536) NOT NULL,
    cohesion FLOAT NOT NULL DEFAULT 0.0 CHECK (cohesion >= 0 AND cohesion <= 1),
    doc_count_30d INTEGER NOT NULL DEFAULT 0,
    last_updated TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    state TEXT NOT NULL DEFAULT 'active' CHECK (state IN ('active', 'merged', 'archived')),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Topic membership table
CREATE TABLE public.topic_membership (
    topic_id UUID NOT NULL REFERENCES public.topics(topic_id) ON DELETE CASCADE,
    embedding_id UUID NOT NULL REFERENCES public.embeddings_store(id) ON DELETE CASCADE,
    account_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000',
    assigned_ts TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    PRIMARY KEY (topic_id, embedding_id)
);

-- Topic daily metrics table
CREATE TABLE public.topic_daily_metrics (
    topic_id UUID NOT NULL REFERENCES public.topics(topic_id) ON DELETE CASCADE,
    account_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000',
    day DATE NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    avg_sentiment FLOAT,
    PRIMARY KEY (topic_id, day)
);

-- Create indexes for performance
CREATE INDEX idx_embeddings_store_account_ts ON public.embeddings_store (account_id, ts DESC);
CREATE INDEX idx_embeddings_store_text_hash ON public.embeddings_store (account_id, text_hash);
CREATE INDEX idx_embeddings_embedding_hnsw ON public.embeddings_store USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

CREATE INDEX idx_topics_account_id ON public.topics (account_id);
CREATE INDEX idx_topics_last_updated ON public.topics (account_id, last_updated DESC);

CREATE INDEX idx_topic_membership_topic_id ON public.topic_membership (topic_id);
CREATE INDEX idx_topic_membership_account_id ON public.topic_membership (account_id);

CREATE INDEX idx_topic_daily_metrics_account_day ON public.topic_daily_metrics (account_id, day DESC);
CREATE INDEX idx_topic_daily_metrics_topic_day ON public.topic_daily_metrics (topic_id, day DESC);

-- Enable RLS on all tables
ALTER TABLE public.embeddings_store ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.topics ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.topic_membership ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.topic_daily_metrics ENABLE ROW LEVEL SECURITY;

-- Create RLS policies (for now allowing all operations)
CREATE POLICY "Allow all operations on embeddings_store" ON public.embeddings_store FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all operations on topics" ON public.topics FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all operations on topic_membership" ON public.topic_membership FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all operations on topic_daily_metrics" ON public.topic_daily_metrics FOR ALL USING (true) WITH CHECK (true);