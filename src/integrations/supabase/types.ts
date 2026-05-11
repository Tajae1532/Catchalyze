export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "12.2.3 (519615d)"
  }
  public: {
    Tables: {
      accounts: {
        Row: {
          created_at: string | null
          id: string
          name: string
          slug: string | null
          updated_at: string | null
        }
        Insert: {
          created_at?: string | null
          id?: string
          name: string
          slug?: string | null
          updated_at?: string | null
        }
        Update: {
          created_at?: string | null
          id?: string
          name?: string
          slug?: string | null
          updated_at?: string | null
        }
        Relationships: []
      }
      active_trends: {
        Row: {
          account_id: string
          created_at: string | null
          id: string
          is_active: boolean | null
          topic_id: string
          trend_data: Json | null
          trend_type: string
          updated_at: string | null
        }
        Insert: {
          account_id: string
          created_at?: string | null
          id?: string
          is_active?: boolean | null
          topic_id: string
          trend_data?: Json | null
          trend_type: string
          updated_at?: string | null
        }
        Update: {
          account_id?: string
          created_at?: string | null
          id?: string
          is_active?: boolean | null
          topic_id?: string
          trend_data?: Json | null
          trend_type?: string
          updated_at?: string | null
        }
        Relationships: []
      }
      app_locks: {
        Row: {
          expires_at: string
          lock_key: string
          owner: string
        }
        Insert: {
          expires_at: string
          lock_key: string
          owner: string
        }
        Update: {
          expires_at?: string
          lock_key?: string
          owner?: string
        }
        Relationships: []
      }
      beta_applications: {
        Row: {
          company: string
          company_size: string
          current_tools: string
          email: string
          id: string
          invoice_sent_at: string | null
          ip_address: unknown | null
          name: string
          notes: string | null
          pain_points: string
          ready_to_pay: boolean
          reviewed_at: string | null
          role: string
          start_timeline: string
          status: string | null
          submitted_at: string | null
          time_spent_weekly: string
          user_agent: string | null
          why_interested: string
        }
        Insert: {
          company: string
          company_size: string
          current_tools: string
          email: string
          id?: string
          invoice_sent_at?: string | null
          ip_address?: unknown | null
          name: string
          notes?: string | null
          pain_points: string
          ready_to_pay: boolean
          reviewed_at?: string | null
          role: string
          start_timeline: string
          status?: string | null
          submitted_at?: string | null
          time_spent_weekly: string
          user_agent?: string | null
          why_interested: string
        }
        Update: {
          company?: string
          company_size?: string
          current_tools?: string
          email?: string
          id?: string
          invoice_sent_at?: string | null
          ip_address?: unknown | null
          name?: string
          notes?: string | null
          pain_points?: string
          ready_to_pay?: boolean
          reviewed_at?: string | null
          role?: string
          start_timeline?: string
          status?: string | null
          submitted_at?: string | null
          time_spent_weekly?: string
          user_agent?: string | null
          why_interested?: string
        }
        Relationships: []
      }
      customers: {
        Row: {
          account_id: string
          churn_risk: string | null
          created_at: string
          email: string | null
          health_score: number | null
          id: string
          last_interaction: string | null
          name: string
          sentiment_score: number | null
          slack_workspace_id: string | null
          updated_at: string
          zendesk_id: string | null
        }
        Insert: {
          account_id: string
          churn_risk?: string | null
          created_at?: string
          email?: string | null
          health_score?: number | null
          id?: string
          last_interaction?: string | null
          name: string
          sentiment_score?: number | null
          slack_workspace_id?: string | null
          updated_at?: string
          zendesk_id?: string | null
        }
        Update: {
          account_id?: string
          churn_risk?: string | null
          created_at?: string
          email?: string | null
          health_score?: number | null
          id?: string
          last_interaction?: string | null
          name?: string
          sentiment_score?: number | null
          slack_workspace_id?: string | null
          updated_at?: string
          zendesk_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "customers_account_id_fkey"
            columns: ["account_id"]
            isOneToOne: false
            referencedRelation: "accounts"
            referencedColumns: ["id"]
          },
        ]
      }
      embeddings_store: {
        Row: {
          account_id: string
          channel_id: string | null
          created_at: string
          customer_id: string | null
          embedding: string
          id: string
          one_line: string
          sentiment: number | null
          source: string
          source_id: string
          text_hash: string
          ts: string
          user_identifier: string | null
        }
        Insert: {
          account_id?: string
          channel_id?: string | null
          created_at?: string
          customer_id?: string | null
          embedding: string
          id?: string
          one_line: string
          sentiment?: number | null
          source: string
          source_id: string
          text_hash: string
          ts: string
          user_identifier?: string | null
        }
        Update: {
          account_id?: string
          channel_id?: string | null
          created_at?: string
          customer_id?: string | null
          embedding?: string
          id?: string
          one_line?: string
          sentiment?: number | null
          source?: string
          source_id?: string
          text_hash?: string
          ts?: string
          user_identifier?: string | null
        }
        Relationships: []
      }
      insight_evidence: {
        Row: {
          created_at: string
          evidence_sentiment: number | null
          evidence_snippet: string
          id: string
          insight_id: string
          slack_message_id: string | null
          ticket_id: string | null
        }
        Insert: {
          created_at?: string
          evidence_sentiment?: number | null
          evidence_snippet: string
          id?: string
          insight_id: string
          slack_message_id?: string | null
          ticket_id?: string | null
        }
        Update: {
          created_at?: string
          evidence_sentiment?: number | null
          evidence_snippet?: string
          id?: string
          insight_id?: string
          slack_message_id?: string | null
          ticket_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "insight_evidence_insight_id_fkey"
            columns: ["insight_id"]
            isOneToOne: false
            referencedRelation: "insights"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "insight_evidence_insight_id_fkey"
            columns: ["insight_id"]
            isOneToOne: false
            referencedRelation: "insights_with_counts"
            referencedColumns: ["id"]
          },
        ]
      }
      insight_generation_runs: {
        Row: {
          error: string | null
          finished_at: string | null
          id: string
          rows_inserted: number | null
          started_at: string
          status: string
        }
        Insert: {
          error?: string | null
          finished_at?: string | null
          id?: string
          rows_inserted?: number | null
          started_at?: string
          status: string
        }
        Update: {
          error?: string | null
          finished_at?: string | null
          id?: string
          rows_inserted?: number | null
          started_at?: string
          status?: string
        }
        Relationships: []
      }
      insights: {
        Row: {
          account_id: string
          affected_customers: number | null
          confidence: number
          created_at: string
          data: Json | null
          description: string
          dismissed_until: string | null
          id: string
          impact_score: number
          is_active: boolean | null
          novelty_score: number
          owner_hint: Database["public"]["Enums"]["owner_hint"] | null
          playbook_steps: string[] | null
          prompt_version: string
          recommended_action: string | null
          severity: Database["public"]["Enums"]["insight_severity"] | null
          snooze_until: string | null
          time_cost_hint: Database["public"]["Enums"]["time_cost_hint"] | null
          title: string
          type: Database["public"]["Enums"]["insight_type"]
          updated_at: string
          why_now: string | null
        }
        Insert: {
          account_id: string
          affected_customers?: number | null
          confidence?: number
          created_at?: string
          data?: Json | null
          description: string
          dismissed_until?: string | null
          id?: string
          impact_score?: number
          is_active?: boolean | null
          novelty_score?: number
          owner_hint?: Database["public"]["Enums"]["owner_hint"] | null
          playbook_steps?: string[] | null
          prompt_version?: string
          recommended_action?: string | null
          severity?: Database["public"]["Enums"]["insight_severity"] | null
          snooze_until?: string | null
          time_cost_hint?: Database["public"]["Enums"]["time_cost_hint"] | null
          title: string
          type: Database["public"]["Enums"]["insight_type"]
          updated_at?: string
          why_now?: string | null
        }
        Update: {
          account_id?: string
          affected_customers?: number | null
          confidence?: number
          created_at?: string
          data?: Json | null
          description?: string
          dismissed_until?: string | null
          id?: string
          impact_score?: number
          is_active?: boolean | null
          novelty_score?: number
          owner_hint?: Database["public"]["Enums"]["owner_hint"] | null
          playbook_steps?: string[] | null
          prompt_version?: string
          recommended_action?: string | null
          severity?: Database["public"]["Enums"]["insight_severity"] | null
          snooze_until?: string | null
          time_cost_hint?: Database["public"]["Enums"]["time_cost_hint"] | null
          title?: string
          type?: Database["public"]["Enums"]["insight_type"]
          updated_at?: string
          why_now?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "insights_account_id_fkey"
            columns: ["account_id"]
            isOneToOne: false
            referencedRelation: "accounts"
            referencedColumns: ["id"]
          },
        ]
      }
      integrations: {
        Row: {
          config: Json
          created_at: string
          id: string
          is_active: boolean | null
          last_sync: string | null
          type: string
          updated_at: string
          user_id: string
        }
        Insert: {
          config: Json
          created_at?: string
          id?: string
          is_active?: boolean | null
          last_sync?: string | null
          type: string
          updated_at?: string
          user_id: string
        }
        Update: {
          config?: Json
          created_at?: string
          id?: string
          is_active?: boolean | null
          last_sync?: string | null
          type?: string
          updated_at?: string
          user_id?: string
        }
        Relationships: []
      }
      rate_limit_events: {
        Row: {
          account_id: string
          created_at: string | null
          error_type: string | null
          id: string
          rate_limiter_state: Json | null
          success: boolean
          timestamp: string
        }
        Insert: {
          account_id: string
          created_at?: string | null
          error_type?: string | null
          id?: string
          rate_limiter_state?: Json | null
          success: boolean
          timestamp: string
        }
        Update: {
          account_id?: string
          created_at?: string | null
          error_type?: string | null
          id?: string
          rate_limiter_state?: Json | null
          success?: boolean
          timestamp?: string
        }
        Relationships: []
      }
      slack_account_mapping: {
        Row: {
          account_id: string | null
          created_at: string | null
          id: string
          team_name: string | null
          workspace_id: string
        }
        Insert: {
          account_id?: string | null
          created_at?: string | null
          id?: string
          team_name?: string | null
          workspace_id: string
        }
        Update: {
          account_id?: string | null
          created_at?: string | null
          id?: string
          team_name?: string | null
          workspace_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "slack_account_mapping_account_id_fkey"
            columns: ["account_id"]
            isOneToOne: false
            referencedRelation: "accounts"
            referencedColumns: ["id"]
          },
        ]
      }
      slack_message_summaries: {
        Row: {
          one_line: string
          slack_message_id: string
          token_estimate: number
          updated_at: string
        }
        Insert: {
          one_line: string
          slack_message_id: string
          token_estimate?: number
          updated_at?: string
        }
        Update: {
          one_line?: string
          slack_message_id?: string
          token_estimate?: number
          updated_at?: string
        }
        Relationships: []
      }
      slack_messages: {
        Row: {
          account_id: string
          created_at: string
          customer_id: string | null
          id: string
          mentions: string[] | null
          sentiment_score: number | null
          slack_channel_id: string
          slack_message_id: string
          text: string
          thread_ts: string | null
          user_id: string
        }
        Insert: {
          account_id: string
          created_at?: string
          customer_id?: string | null
          id?: string
          mentions?: string[] | null
          sentiment_score?: number | null
          slack_channel_id: string
          slack_message_id: string
          text: string
          thread_ts?: string | null
          user_id: string
        }
        Update: {
          account_id?: string
          created_at?: string
          customer_id?: string | null
          id?: string
          mentions?: string[] | null
          sentiment_score?: number | null
          slack_channel_id?: string
          slack_message_id?: string
          text?: string
          thread_ts?: string | null
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "slack_messages_account_id_fkey"
            columns: ["account_id"]
            isOneToOne: false
            referencedRelation: "accounts"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "slack_messages_customer_id_fkey"
            columns: ["customer_id"]
            isOneToOne: false
            referencedRelation: "customers"
            referencedColumns: ["id"]
          },
        ]
      }
      slack_oauth_tokens: {
        Row: {
          access_token: string
          created_at: string
          expires_at: string | null
          id: string
          installed_at: string
          refresh_token: string | null
          updated_at: string
          workspace_id: string
        }
        Insert: {
          access_token: string
          created_at?: string
          expires_at?: string | null
          id?: string
          installed_at?: string
          refresh_token?: string | null
          updated_at?: string
          workspace_id: string
        }
        Update: {
          access_token?: string
          created_at?: string
          expires_at?: string | null
          id?: string
          installed_at?: string
          refresh_token?: string | null
          updated_at?: string
          workspace_id?: string
        }
        Relationships: []
      }
      ticket_summaries: {
        Row: {
          one_line: string
          ticket_id: string
          token_estimate: number
          updated_at: string
        }
        Insert: {
          one_line: string
          ticket_id: string
          token_estimate?: number
          updated_at?: string
        }
        Update: {
          one_line?: string
          ticket_id?: string
          token_estimate?: number
          updated_at?: string
        }
        Relationships: []
      }
      tickets: {
        Row: {
          account_id: string
          ai_summary: string | null
          created_at: string
          customer_id: string | null
          description: string | null
          id: string
          priority: string | null
          sentiment_score: number | null
          status: string | null
          subject: string
          tags: string[] | null
          updated_at: string
          zendesk_ticket_id: string
        }
        Insert: {
          account_id: string
          ai_summary?: string | null
          created_at?: string
          customer_id?: string | null
          description?: string | null
          id?: string
          priority?: string | null
          sentiment_score?: number | null
          status?: string | null
          subject: string
          tags?: string[] | null
          updated_at?: string
          zendesk_ticket_id: string
        }
        Update: {
          account_id?: string
          ai_summary?: string | null
          created_at?: string
          customer_id?: string | null
          description?: string | null
          id?: string
          priority?: string | null
          sentiment_score?: number | null
          status?: string | null
          subject?: string
          tags?: string[] | null
          updated_at?: string
          zendesk_ticket_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "tickets_account_id_fkey"
            columns: ["account_id"]
            isOneToOne: false
            referencedRelation: "accounts"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "tickets_customer_id_fkey"
            columns: ["customer_id"]
            isOneToOne: false
            referencedRelation: "customers"
            referencedColumns: ["id"]
          },
        ]
      }
      topic_daily_metrics: {
        Row: {
          account_id: string
          avg_sentiment: number | null
          count: number
          day: string
          topic_id: string
        }
        Insert: {
          account_id?: string
          avg_sentiment?: number | null
          count?: number
          day: string
          topic_id: string
        }
        Update: {
          account_id?: string
          avg_sentiment?: number | null
          count?: number
          day?: string
          topic_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "topic_daily_metrics_topic_id_fkey"
            columns: ["topic_id"]
            isOneToOne: false
            referencedRelation: "topics"
            referencedColumns: ["topic_id"]
          },
        ]
      }
      topic_membership: {
        Row: {
          account_id: string
          assigned_ts: string
          embedding_id: string
          topic_id: string
        }
        Insert: {
          account_id?: string
          assigned_ts?: string
          embedding_id: string
          topic_id: string
        }
        Update: {
          account_id?: string
          assigned_ts?: string
          embedding_id?: string
          topic_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "topic_membership_embedding_id_fkey"
            columns: ["embedding_id"]
            isOneToOne: false
            referencedRelation: "embeddings_store"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "topic_membership_topic_id_fkey"
            columns: ["topic_id"]
            isOneToOne: false
            referencedRelation: "topics"
            referencedColumns: ["topic_id"]
          },
        ]
      }
      topics: {
        Row: {
          account_id: string
          centroid: string
          cohesion: number
          created_at: string
          doc_count_30d: number
          keywords: string[] | null
          last_updated: string
          name: string | null
          state: string
          topic_id: string
        }
        Insert: {
          account_id?: string
          centroid: string
          cohesion?: number
          created_at?: string
          doc_count_30d?: number
          keywords?: string[] | null
          last_updated?: string
          name?: string | null
          state?: string
          topic_id?: string
        }
        Update: {
          account_id?: string
          centroid?: string
          cohesion?: number
          created_at?: string
          doc_count_30d?: number
          keywords?: string[] | null
          last_updated?: string
          name?: string | null
          state?: string
          topic_id?: string
        }
        Relationships: []
      }
      user_accounts: {
        Row: {
          account_id: string
          created_at: string | null
          role: string | null
          user_id: string
        }
        Insert: {
          account_id: string
          created_at?: string | null
          role?: string | null
          user_id: string
        }
        Update: {
          account_id?: string
          created_at?: string | null
          role?: string | null
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "user_accounts_account_id_fkey"
            columns: ["account_id"]
            isOneToOne: false
            referencedRelation: "accounts"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "user_accounts_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
        ]
      }
      users: {
        Row: {
          avatar_url: string | null
          created_at: string | null
          email: string
          google_id: string
          id: string
          name: string | null
          updated_at: string | null
        }
        Insert: {
          avatar_url?: string | null
          created_at?: string | null
          email: string
          google_id: string
          id?: string
          name?: string | null
          updated_at?: string | null
        }
        Update: {
          avatar_url?: string | null
          created_at?: string | null
          email?: string
          google_id?: string
          id?: string
          name?: string | null
          updated_at?: string | null
        }
        Relationships: []
      }
      zendesk_account_mapping: {
        Row: {
          account_id: string | null
          created_at: string | null
          id: string
          subdomain: string
        }
        Insert: {
          account_id?: string | null
          created_at?: string | null
          id?: string
          subdomain: string
        }
        Update: {
          account_id?: string | null
          created_at?: string | null
          id?: string
          subdomain?: string
        }
        Relationships: [
          {
            foreignKeyName: "zendesk_account_mapping_account_id_fkey"
            columns: ["account_id"]
            isOneToOne: false
            referencedRelation: "accounts"
            referencedColumns: ["id"]
          },
        ]
      }
      zendesk_integrations: {
        Row: {
          created_at: string | null
          subdomain: string
          trigger_id: string | null
          updated_at: string | null
          webhook_id: string | null
        }
        Insert: {
          created_at?: string | null
          subdomain: string
          trigger_id?: string | null
          updated_at?: string | null
          webhook_id?: string | null
        }
        Update: {
          created_at?: string | null
          subdomain?: string
          trigger_id?: string | null
          updated_at?: string | null
          webhook_id?: string | null
        }
        Relationships: []
      }
      zendesk_oauth_clients: {
        Row: {
          client_id: string
          client_secret_enc: string | null
          created_at: string | null
          encryption_version: string | null
          redirect_uri: string | null
          scopes: string | null
          subdomain: string
          updated_at: string | null
        }
        Insert: {
          client_id: string
          client_secret_enc?: string | null
          created_at?: string | null
          encryption_version?: string | null
          redirect_uri?: string | null
          scopes?: string | null
          subdomain: string
          updated_at?: string | null
        }
        Update: {
          client_id?: string
          client_secret_enc?: string | null
          created_at?: string | null
          encryption_version?: string | null
          redirect_uri?: string | null
          scopes?: string | null
          subdomain?: string
          updated_at?: string | null
        }
        Relationships: []
      }
      zendesk_oauth_tokens: {
        Row: {
          access_token: string
          created_at: string
          expires_at: string | null
          id: string
          installed_at: string
          refresh_token: string | null
          scope: string | null
          subdomain: string
          token_type: string | null
          updated_at: string
        }
        Insert: {
          access_token: string
          created_at?: string
          expires_at?: string | null
          id?: string
          installed_at?: string
          refresh_token?: string | null
          scope?: string | null
          subdomain: string
          token_type?: string | null
          updated_at?: string
        }
        Update: {
          access_token?: string
          created_at?: string
          expires_at?: string | null
          id?: string
          installed_at?: string
          refresh_token?: string | null
          scope?: string | null
          subdomain?: string
          token_type?: string | null
          updated_at?: string
        }
        Relationships: []
      }
    }
    Views: {
      insights_with_counts: {
        Row: {
          confidence: number | null
          created_at: string | null
          evidence_count: number | null
          id: string | null
          impact_score: number | null
          novelty_score: number | null
          severity: Database["public"]["Enums"]["insight_severity"] | null
          title: string | null
          type: Database["public"]["Enums"]["insight_type"] | null
        }
        Relationships: []
      }
    }
    Functions: {
      binary_quantize: {
        Args: { "": string } | { "": unknown }
        Returns: unknown
      }
      halfvec_avg: {
        Args: { "": number[] }
        Returns: unknown
      }
      halfvec_out: {
        Args: { "": unknown }
        Returns: unknown
      }
      halfvec_send: {
        Args: { "": unknown }
        Returns: string
      }
      halfvec_typmod_in: {
        Args: { "": unknown[] }
        Returns: number
      }
      hnsw_bit_support: {
        Args: { "": unknown }
        Returns: unknown
      }
      hnsw_halfvec_support: {
        Args: { "": unknown }
        Returns: unknown
      }
      hnsw_sparsevec_support: {
        Args: { "": unknown }
        Returns: unknown
      }
      hnswhandler: {
        Args: { "": unknown }
        Returns: unknown
      }
      ivfflat_bit_support: {
        Args: { "": unknown }
        Returns: unknown
      }
      ivfflat_halfvec_support: {
        Args: { "": unknown }
        Returns: unknown
      }
      ivfflathandler: {
        Args: { "": unknown }
        Returns: unknown
      }
      l2_norm: {
        Args: { "": unknown } | { "": unknown }
        Returns: number
      }
      l2_normalize: {
        Args: { "": string } | { "": unknown } | { "": unknown }
        Returns: unknown
      }
      sparsevec_out: {
        Args: { "": unknown }
        Returns: unknown
      }
      sparsevec_send: {
        Args: { "": unknown }
        Returns: string
      }
      sparsevec_typmod_in: {
        Args: { "": unknown[] }
        Returns: number
      }
      upsert_topic_daily_metrics: {
        Args: {
          p_account_id: string
          p_count_delta?: number
          p_day: string
          p_sentiment?: number
          p_topic_id: string
        }
        Returns: undefined
      }
      vector_avg: {
        Args: { "": number[] }
        Returns: string
      }
      vector_dims: {
        Args: { "": string } | { "": unknown }
        Returns: number
      }
      vector_norm: {
        Args: { "": string }
        Returns: number
      }
      vector_out: {
        Args: { "": string }
        Returns: unknown
      }
      vector_send: {
        Args: { "": string }
        Returns: string
      }
      vector_typmod_in: {
        Args: { "": unknown[] }
        Returns: number
      }
    }
    Enums: {
      insight_severity: "low" | "medium" | "high" | "critical"
      insight_type:
        | "trend"
        | "churn_risk"
        | "bug"
        | "ux_friction"
        | "feature_request"
        | "process_gap"
      owner_hint: "CS" | "Support" | "PM" | "Eng" | "Sales"
      time_cost_hint: "S" | "M" | "L"
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {
      insight_severity: ["low", "medium", "high", "critical"],
      insight_type: [
        "trend",
        "churn_risk",
        "bug",
        "ux_friction",
        "feature_request",
        "process_gap",
      ],
      owner_hint: ["CS", "Support", "PM", "Eng", "Sales"],
      time_cost_hint: ["S", "M", "L"],
    },
  },
} as const
