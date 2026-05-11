import "https://deno.land/x/xhr@0.1.0/mod.ts";
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.7.1';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_ANON_KEY') ?? ''
    );

    console.log('Fetching dashboard data...');

    // Get customers with health scores
    const { data: customers } = await supabaseClient
      .from('customers')
      .select('*')
      .order('created_at', { ascending: false });

    // Get active insights
    const { data: insights } = await supabaseClient
      .from('insights')
      .select('*')
      .eq('is_active', true)
      .order('created_at', { ascending: false })
      .limit(10);

    // Get recent tickets
    const { data: tickets } = await supabaseClient
      .from('tickets')
      .select(`
        *,
        customers(name, email)
      `)
      .order('created_at', { ascending: false })
      .limit(20);

    // Calculate overall metrics
    const totalCustomers = customers?.length || 0;
    const avgHealthScore = customers?.length 
      ? customers.reduce((sum, c) => sum + c.health_score, 0) / customers.length 
      : 0;
    
    const highRiskCustomers = customers?.filter(c => c.churn_risk === 'high').length || 0;
    const criticalInsights = insights?.filter(i => i.severity === 'critical').length || 0;

    // Recent activity
    const recentTickets = tickets?.slice(0, 5) || [];
    const todayTickets = tickets?.filter(t => {
      const ticketDate = new Date(t.created_at);
      const today = new Date();
      return ticketDate.toDateString() === today.toDateString();
    }).length || 0;

    // Sentiment analysis
    const avgSentiment = customers?.length
      ? customers.reduce((sum, c) => sum + (c.sentiment_score || 0), 0) / customers.length
      : 0;

    console.log('Dashboard data compiled successfully');

    return new Response(
      JSON.stringify({
        success: true,
        data: {
          overview: {
            total_customers: totalCustomers,
            avg_health_score: Math.round(avgHealthScore),
            high_risk_customers: highRiskCustomers,
            critical_insights: criticalInsights,
            today_tickets: todayTickets,
            avg_sentiment: Number(avgSentiment.toFixed(2))
          },
          customers: customers?.map(c => ({
            id: c.id,
            name: c.name,
            email: c.email,
            health_score: c.health_score,
            sentiment_score: c.sentiment_score,
            churn_risk: c.churn_risk,
            last_interaction: c.last_interaction
          })) || [],
          insights: insights || [],
          recent_tickets: recentTickets.map(t => ({
            id: t.id,
            subject: t.subject,
            customer_name: t.customers?.name || 'Unknown',
            priority: t.priority,
            status: t.status,
            sentiment_score: t.sentiment_score,
            created_at: t.created_at
          }))
        }
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    );

  } catch (error) {
    console.error('Error in get-dashboard-data:', error);
    return new Response(
      JSON.stringify({ error: error instanceof Error ? error.message : 'Unknown error' }),
      { 
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    );
  }
});