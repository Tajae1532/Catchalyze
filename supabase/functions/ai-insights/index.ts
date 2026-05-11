import "https://deno.land/x/xhr@0.1.0/mod.ts";
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.7.1';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

interface TicketData {
  id: string;
  subject: string;
  description: string;
  customer_name: string;
  priority: string;
  sentiment_score?: number;
}

interface SlackMessage {
  id: string;
  text: string;
  customer_name: string;
  mentions: string[];
  sentiment_score?: number;
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const openAIApiKey = Deno.env.get('OPENAI_API_KEY');
    if (!openAIApiKey) {
      throw new Error('OpenAI API key not configured');
    }

    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_ANON_KEY') ?? ''
    );

    console.log('Processing AI insights...');

    // Fetch recent tickets and slack messages
    const { data: tickets } = await supabaseClient
      .from('tickets')
      .select(`
        id,
        subject,
        description,
        priority,
        sentiment_score,
        customers(name)
      `)
      .order('created_at', { ascending: false })
      .limit(50);

    const { data: slackMessages } = await supabaseClient
      .from('slack_messages')
      .select(`
        id,
        text,
        mentions,
        sentiment_score,
        customers(name)
      `)
      .order('created_at', { ascending: false })
      .limit(50);

    // Process the data for GPT-4
    const contextData = {
      tickets: tickets?.map(t => ({
        id: t.id,
        subject: t.subject,
        description: t.description,
        customer_name: t.customers?.name || 'Unknown',
        priority: t.priority,
        sentiment_score: t.sentiment_score
      })) || [],
      slack_messages: slackMessages?.map(m => ({
        id: m.id,
        text: m.text,
        customer_name: m.customers?.name || 'Unknown',
        mentions: m.mentions || [],
        sentiment_score: m.sentiment_score
      })) || []
    };

    console.log('Sending data to OpenAI for analysis...');

    // Call OpenAI GPT-4 for insights
    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${openAIApiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: 'gpt-4.1-2025-04-14',
        messages: [
          {
            role: 'system',
            content: `You are CustomerWhisperer, an AI that analyzes customer data to surface actionable insights for product managers. 

Analyze the provided ticket and Slack data to identify:
1. Trending issues (patterns in problems)
2. Churn risk indicators (negative sentiment, escalating issues)
3. Sentiment spikes (sudden mood changes)
4. Health decline patterns

Return a JSON object with insights array. Each insight should have:
- type: "trending_issue" | "churn_risk" | "sentiment_spike" | "health_decline"
- title: Brief descriptive title
- description: Detailed explanation
- severity: "low" | "medium" | "high" | "critical"
- affected_customers: Number of customers affected
- data: Additional context as JSON object

Focus on actionable insights that help product managers make decisions.`
          },
          {
            role: 'user',
            content: `Analyze this customer data and provide insights:

TICKETS DATA:
${JSON.stringify(contextData.tickets, null, 2)}

SLACK MESSAGES DATA:
${JSON.stringify(contextData.slack_messages, null, 2)}

Provide insights in JSON format.`
          }
        ],
        temperature: 0.3,
        max_tokens: 2000
      }),
    });

    const aiResponse = await response.json();
    console.log('OpenAI response received');

    if (!aiResponse.choices?.[0]?.message?.content) {
      throw new Error('Invalid OpenAI response');
    }

    let insights;
    try {
      insights = JSON.parse(aiResponse.choices[0].message.content);
    } catch (e) {
      console.error('Failed to parse AI response:', e);
      throw new Error('Failed to parse AI insights');
    }

    // Store insights in database
    if (insights.insights && Array.isArray(insights.insights)) {
      console.log('Storing insights in database...');
      
      // Deactivate old insights
      await supabaseClient
        .from('insights')
        .update({ is_active: false })
        .eq('is_active', true);

      // Insert new insights
      const { error: insertError } = await supabaseClient
        .from('insights')
        .insert(insights.insights);

      if (insertError) {
        console.error('Error storing insights:', insertError);
        throw insertError;
      }
    }

    console.log('AI insights processing completed successfully');

    return new Response(
      JSON.stringify({ 
        success: true, 
        insights: insights.insights || [],
        processed_tickets: contextData.tickets.length,
        processed_messages: contextData.slack_messages.length
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    );

  } catch (error) {
    console.error('Error in ai-insights function:', error);
    return new Response(
      JSON.stringify({ error: error instanceof Error ? error.message : 'Unknown error' }),
      { 
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    );
  }
});