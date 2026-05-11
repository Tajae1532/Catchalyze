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
const RATE_LIMIT_MAX_REQUESTS = 50; // Max requests per window

// Verify Slack signature
async function verifySlackSignature(
  body: string,
  timestamp: string,
  signature: string,
  signingSecret: string
): Promise<boolean> {
  const timestampNum = parseInt(timestamp);
  const currentTime = Math.floor(Date.now() / 1000);
  
  // Check if timestamp is within 5 minutes
  if (Math.abs(currentTime - timestampNum) > 300) {
    return false;
  }

  const baseString = `v0:${timestamp}:${body}`;
  const encoder = new TextEncoder();
  const keyData = encoder.encode(signingSecret);
  const messageData = encoder.encode(baseString);
  
  const cryptoKey = await crypto.subtle.importKey(
    'raw',
    keyData,
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );
  
  const signatureBuffer = await crypto.subtle.sign('HMAC', cryptoKey, messageData);
  const computedSignature = `v0=${Array.from(new Uint8Array(signatureBuffer))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('')}`;
  
  return computedSignature === signature;
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

interface SlackEvent {
  type: string;
  channel: string;
  user: string;
  text: string;
  ts: string;
  event_ts: string;
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
    const slackSigningSecret = Deno.env.get('SLACK_SIGNING_SECRET');
    
    if (!openAIApiKey) {
      throw new Error('OpenAI API key not configured');
    }

    if (!slackSigningSecret) {
      throw new Error('Slack signing secret not configured');
    }

    // Get raw body for signature verification
    const rawBody = await req.text();
    
    // Slack signature verification (skip for URL verification)
    const slackSignature = req.headers.get('x-slack-signature');
    const slackTimestamp = req.headers.get('x-slack-request-timestamp');
    
    if (slackSignature && slackTimestamp) {
      const isValidSignature = await verifySlackSignature(
        rawBody,
        slackTimestamp,
        slackSignature,
        slackSigningSecret
      );
      
      if (!isValidSignature) {
        console.error('Invalid Slack signature');
        return new Response(
          JSON.stringify({ error: 'Invalid signature' }),
          { 
            status: 401,
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          }
        );
      }
    }

    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_ANON_KEY') ?? ''
    );

    const body = JSON.parse(rawBody);
    
    // Handle Slack URL verification
    if (body.type === 'url_verification') {
      return new Response(body.challenge, {
        headers: { 'Content-Type': 'text/plain' }
      });
    }

    const event = body.event as SlackEvent;
    
    if (!event || event.type !== 'message' || !event.text) {
      return new Response(JSON.stringify({ success: true }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }

    // Skip bot messages
    if (event.text.includes('has joined') || event.user === 'USLACKBOT') {
      return new Response(JSON.stringify({ success: true }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }

    console.log('Processing Slack message:', event.ts);

    // Extract mentions and customer references
    const mentionRegex = /@(\w+)/g;
    const mentions = [...(event.text.match(mentionRegex) || [])];
    
    // Analyze sentiment and extract customer info with OpenAI
    const analysisResponse = await fetch('https://api.openai.com/v1/chat/completions', {
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
            content: 'Analyze this Slack message for customer sentiment and extract any customer names or company mentions. Return JSON with: sentiment_score (number -1 to 1), customer_mentions (array of customer/company names found), and categories (array of topics like "billing", "feature_request", "bug", "support").'
          },
          {
            role: 'user',
            content: event.text
          }
        ],
        temperature: 0.1,
        max_tokens: 300
      }),
    });

    const analysisData = await analysisResponse.json();
    let analysis = { sentiment_score: 0, customer_mentions: [], categories: [] };
    
    try {
      analysis = JSON.parse(analysisData.choices[0].message.content);
    } catch (e) {
      console.error('Failed to parse analysis:', e);
    }

    // Try to find customer by mentions
    let customer = null;
    if (analysis.customer_mentions && analysis.customer_mentions.length > 0) {
      for (const mention of analysis.customer_mentions) {
        const { data: foundCustomer } = await supabaseClient
          .from('customers')
          .select('*')
          .ilike('name', `%${mention}%`)
          .limit(1)
          .single();
        
        if (foundCustomer) {
          customer = foundCustomer;
          break;
        }
      }
    }

    // If no customer found, create a generic one for the channel
    if (!customer) {
      const channelName = event.channel || 'unknown';
      const { data: existingCustomer } = await supabaseClient
        .from('customers')
        .select('*')
        .eq('slack_workspace_id', channelName)
        .single();

      if (existingCustomer) {
        customer = existingCustomer;
      } else {
        const { data: newCustomer, error } = await supabaseClient
          .from('customers')
          .insert({
            name: `Slack Channel ${channelName}`,
            slack_workspace_id: channelName,
            sentiment_score: analysis.sentiment_score,
            health_score: 60,
            last_interaction: new Date().toISOString()
          })
          .select()
          .single();

        if (!error) customer = newCustomer;
      }
    }

    // Store slack message
    if (customer) {
      const { error: messageError } = await supabaseClient
        .from('slack_messages')
        .insert({
          customer_id: customer.id,
          slack_channel_id: event.channel,
          slack_message_id: event.ts,
          user_id: event.user,
          text: event.text,
          sentiment_score: analysis.sentiment_score,
          mentions: mentions
        });

      if (messageError) {
        console.error('Error storing slack message:', messageError);
      }

      // Update customer sentiment and health
      const sentimentImpact = analysis.sentiment_score * 5;
      const newHealthScore = Math.max(0, Math.min(100, customer.health_score + sentimentImpact));
      
      await supabaseClient
        .from('customers')
        .update({
          sentiment_score: (customer.sentiment_score + analysis.sentiment_score) / 2,
          health_score: newHealthScore,
          last_interaction: new Date().toISOString(),
          churn_risk: newHealthScore < 30 ? 'high' : newHealthScore < 60 ? 'medium' : 'low'
        })
        .eq('id', customer.id);
    }

    console.log('Slack message processed successfully');

    // Trigger insights generation if negative sentiment
    if (analysis.sentiment_score < -0.3) {
      try {
        await supabaseClient.functions.invoke('ai-insights');
      } catch (e) {
        console.error('Failed to trigger insights:', e);
      }
    }

    return new Response(
      JSON.stringify({ 
        success: true,
        customer_id: customer?.id,
        sentiment_score: analysis.sentiment_score,
        categories: analysis.categories
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    );

  } catch (error) {
    console.error('Error in slack-webhook:', error);
    return new Response(
      JSON.stringify({ error: error instanceof Error ? error.message : 'Unknown error' }),
      { 
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    );
  }
});