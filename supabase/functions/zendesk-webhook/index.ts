import "https://deno.land/x/xhr@0.1.0/mod.ts";
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.7.1';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

// Rate limiting map (IP -> array of timestamps)
const rateLimitMap = new Map<string, number[]>();
const RATE_LIMIT_WINDOW = 60000; // 1 minute
const RATE_LIMIT_MAX_REQUESTS = 100; // Max requests per window (higher for Zendesk)

// Verify Zendesk signature
async function verifyZendeskSignature(
  body: string,
  signature: string,
  endpoint: string
): Promise<boolean> {
  // Zendesk uses HTTP basic auth or API token for webhook authentication
  // Since we don't have a specific webhook secret, we'll validate the endpoint format
  // and basic request structure for now
  try {
    const parsedBody = JSON.parse(body);
    return parsedBody && parsedBody.ticket && typeof parsedBody.ticket === 'object';
  } catch {
    return false;
  }
}

// Rate limiting function
function checkRateLimit(ip: string): boolean {
  const now = Date.now();
  const requests = rateLimitMap.get(ip) || [];
  
  // Remove old requests outside the window
  const validRequests = requests.filter(time => now - time < RATE_LIMIT_WINDOW);
  
  if (validRequests.length >= RATE_LIMIT_MAX_REQUESTS) {
    return false;
  }
  
  validRequests.push(now);
  rateLimitMap.set(ip, validRequests);
  return true;
}

interface ZendeskTicket {
  id: string;
  subject: string;
  description: string;
  status: string;
  priority: string;
  requester_id: string;
  requester?: {
    name: string;
    email: string;
  };
  tags: string[];
  created_at: string;
  updated_at: string;
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    // Rate limiting
    const clientIP = req.headers.get('x-forwarded-for') || req.headers.get('x-real-ip') || 'unknown';
    if (!checkRateLimit(clientIP)) {
      return new Response(
        JSON.stringify({ error: 'Rate limit exceeded' }),
        { 
          status: 429,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      );
    }

    // Get environment variables
    const openAIApiKey = Deno.env.get('OPENAI_API_KEY');
    if (!openAIApiKey) {
      throw new Error('OpenAI API key not configured');
    }

    // Get raw body for validation
    const rawBody = await req.text();
    
    // Basic request validation
    if (!rawBody || rawBody.trim() === '') {
      return new Response(
        JSON.stringify({ error: 'Empty request body' }),
        { 
          status: 400,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      );
    }

    // Validate request structure
    const isValidRequest = await verifyZendeskSignature(
      rawBody,
      req.headers.get('authorization') || '',
      req.url
    );
    
    if (!isValidRequest) {
      console.error('Invalid Zendesk webhook request');
      return new Response(
        JSON.stringify({ error: 'Invalid request format' }),
        { 
          status: 400,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      );
    }

    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_ANON_KEY') ?? ''
    );

    const { ticket } = JSON.parse(rawBody) as { ticket: ZendeskTicket };
    
    if (!ticket) {
      throw new Error('No ticket data provided');
    }

    console.log('Processing Zendesk ticket:', ticket.id);

    // Analyze sentiment with OpenAI
    const sentimentResponse = await fetch('https://api.openai.com/v1/chat/completions', {
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
            content: 'Analyze the sentiment of this customer support ticket. Return a JSON object with: sentiment_score (number between -1 and 1), summary (brief explanation), and key_issues (array of main problems mentioned).'
          },
          {
            role: 'user',
            content: `Subject: ${ticket.subject}\nDescription: ${ticket.description}`
          }
        ],
        temperature: 0.1,
        max_tokens: 500
      }),
    });

    const sentimentData = await sentimentResponse.json();
    let analysis = { sentiment_score: 0, summary: '', key_issues: [] };
    
    try {
      analysis = JSON.parse(sentimentData.choices[0].message.content);
    } catch (e) {
      console.error('Failed to parse sentiment analysis:', e);
    }

    // Find or create customer
    let customer;
    const { data: existingCustomer } = await supabaseClient
      .from('customers')
      .select('*')
      .eq('email', ticket.requester?.email)
      .single();

    if (existingCustomer) {
      customer = existingCustomer;
      
      // Update customer health score based on ticket priority and sentiment
      let healthAdjustment = 0;
      if (ticket.priority === 'urgent') healthAdjustment = -15;
      else if (ticket.priority === 'high') healthAdjustment = -10;
      else if (ticket.priority === 'normal') healthAdjustment = -5;
      
      // Additional adjustment based on sentiment
      healthAdjustment += Math.round(analysis.sentiment_score * 10);
      
      const newHealthScore = Math.max(0, Math.min(100, customer.health_score + healthAdjustment));
      
      await supabaseClient
        .from('customers')
        .update({ 
          health_score: newHealthScore,
          sentiment_score: analysis.sentiment_score,
          last_interaction: new Date().toISOString(),
          churn_risk: newHealthScore < 30 ? 'high' : newHealthScore < 60 ? 'medium' : 'low'
        })
        .eq('id', customer.id);

      customer.health_score = newHealthScore;
    } else {
      // Create new customer
      const { data: newCustomer, error } = await supabaseClient
        .from('customers')
        .insert({
          name: ticket.requester?.name || 'Unknown',
          email: ticket.requester?.email,
          sentiment_score: analysis.sentiment_score,
          health_score: analysis.sentiment_score > 0 ? 70 : 40,
          last_interaction: new Date().toISOString(),
          churn_risk: analysis.sentiment_score < -0.3 ? 'high' : 'low'
        })
        .select()
        .single();

      if (error) throw error;
      customer = newCustomer;
    }

    // Store ticket
    const { error: ticketError } = await supabaseClient
      .from('tickets')
      .upsert({
        zendesk_ticket_id: ticket.id,
        customer_id: customer.id,
        subject: ticket.subject,
        description: ticket.description,
        status: ticket.status,
        priority: ticket.priority,
        sentiment_score: analysis.sentiment_score,
        ai_summary: analysis.summary,
        tags: ticket.tags,
        created_at: ticket.created_at,
        updated_at: ticket.updated_at
      }, { onConflict: 'zendesk_ticket_id' });

    if (ticketError) throw ticketError;

    console.log('Ticket processed successfully:', ticket.id);

    // Trigger background insights generation
    try {
      await supabaseClient.functions.invoke('ai-insights');
    } catch (e) {
      console.error('Failed to trigger insights generation:', e);
    }

    return new Response(
      JSON.stringify({ 
        success: true, 
        customer_id: customer.id,
        health_score: customer.health_score,
        sentiment_score: analysis.sentiment_score
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    );

  } catch (error) {
    console.error('Error in zendesk-webhook:', error);
    return new Response(
      JSON.stringify({ error: error instanceof Error ? error.message : 'Unknown error' }),
      { 
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    );
  }
});