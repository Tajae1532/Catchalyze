declare const Deno: { env: { get(k: string): string | undefined } };

// @ts-ignore  // Deno URL import; types resolved at runtime
import "https://deno.land/x/xhr@0.1.0/mod.ts";
// @ts-ignore  // Deno URL import; types resolved at runtime
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
// @ts-ignore  // Deno URL import; types resolved at runtime
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
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    );

    // Get user from JWT
    const authHeader = req.headers.get('Authorization');
    if (!authHeader) {
      throw new Error('Authorization header required');
    }

    const token = authHeader.replace('Bearer ', '');
    const { data: { user } } = await supabaseClient.auth.getUser(token);
    
    if (!user) {
      throw new Error('Invalid or expired token');
    }

    if (req.method === 'POST') {
      const { subdomain, client_id, client_secret, scopes = 'read write' } = await req.json();

      // Validate required fields
      if (!subdomain || !client_id || !client_secret) {
        return new Response(
          JSON.stringify({ error: 'subdomain, client_id, and client_secret are required' }),
          { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        );
      }

      // Normalize subdomain - extract from various formats
      let normalizedSubdomain = subdomain.trim().toLowerCase();
      if (normalizedSubdomain.includes('.zendesk.com')) {
        normalizedSubdomain = normalizedSubdomain.split('.zendesk.com')[0];
      }
      if (normalizedSubdomain.includes('://')) {
        const urlParts = normalizedSubdomain.split('://')[1];
        if (urlParts) {
          normalizedSubdomain = urlParts.split('.zendesk.com')[0];
        }
      }

      // Validate subdomain format (only alphanumeric and hyphens)
      if (!/^[a-z0-9-]+$/.test(normalizedSubdomain)) {
        return new Response(
          JSON.stringify({ error: 'Invalid subdomain format. Use only lowercase letters, numbers, and hyphens.' }),
          { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        );
      }

      // Get user's account
      const { data: userAccount } = await supabaseClient
        .from('user_accounts')
        .select('account_id')
        .eq('user_id', user.id)
        .single();

      if (!userAccount) {
        throw new Error('User account not found');
      }

      // Check if subdomain is already mapped to another account
      const { data: existingMapping } = await supabaseClient
        .from('zendesk_account_mapping')
        .select('account_id')
        .eq('subdomain', normalizedSubdomain)
        .single();

      if (existingMapping && existingMapping.account_id !== userAccount.account_id) {
        return new Response(
          JSON.stringify({ 
            error: 'This Zendesk subdomain is already connected to another Catchalyze account.' 
          }),
          { status: 409, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        );
      }

      // Preflight check - verify Zendesk instance exists
      try {
        const healthCheck = await fetch(`https://${normalizedSubdomain}.zendesk.com/oauth/authorizations/new`, {
          method: 'HEAD',
          headers: { 'User-Agent': 'Catchalyze-Setup-Check/1.0' }
        });
        
        if (healthCheck.status === 404) {
          return new Response(
            JSON.stringify({ error: 'Zendesk subdomain not found. Please verify your subdomain is correct.' }),
            { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
          );
        }
      } catch (e) {
        return new Response(
          JSON.stringify({ error: 'Unable to verify Zendesk subdomain. Please check your internet connection.' }),
          { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        );
      }

      // Test OAuth app configuration with a dummy token exchange
      try {
        const testResponse = await fetch(`https://${normalizedSubdomain}.zendesk.com/oauth/tokens`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'User-Agent': 'Catchalyze-Setup-Check/1.0'
          },
          body: JSON.stringify({
            grant_type: 'authorization_code',
            code: 'test-code-for-validation',
            client_id: client_id,
            client_secret: client_secret,
            redirect_uri: 'https://api.catchalyze.com/zendesk/oauth/callback',
            scope: scopes
          })
        });

        const testResult = await testResponse.json();
        
        // Expected errors for test validation
        if (testResult.error === 'invalid_grant') {
          // This is expected - means OAuth app exists and credentials are valid
          console.log('OAuth app validation successful (expected invalid_grant error)');
        } else if (testResult.error === 'invalid_client') {
          return new Response(
            JSON.stringify({ error: 'Invalid client credentials. Please verify your Client ID and Secret.' }),
            { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
          );
        } else if (testResult.error === 'redirect_uri_mismatch') {
          return new Response(
            JSON.stringify({ 
              error: 'Redirect URI mismatch. Please set redirect URI to: https://api.catchalyze.com/zendesk/oauth/callback' 
            }),
            { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
          );
        }
      } catch (e) {
        return new Response(
          JSON.stringify({ error: 'Unable to validate OAuth app configuration. Please try again.' }),
          { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        );
      }

      // Encrypt client secret with AES-GCM
      const masterKey = Deno.env.get('ZENDESK_ENCRYPTION_KEY') || 'default-key-change-in-production';
      const encoder = new TextEncoder();
      
      // AAD binding with subdomain for integrity
      const aad = encoder.encode(normalizedSubdomain);
      
      const keyMaterial = encoder.encode(masterKey.padEnd(32, '0').substring(0, 32));
      const key = await crypto.subtle.importKey(
        'raw',
        keyMaterial,
        { name: 'AES-GCM' },
        false,
        ['encrypt', 'decrypt']
      );

      const iv = crypto.getRandomValues(new Uint8Array(12));
      const encrypted = await crypto.subtle.encrypt(
        { name: 'AES-GCM', iv, additionalData: aad },
        key,
        encoder.encode(client_secret)
      );

      // Versioned storage format: AES-GCM-256:v1:base64(iv+ciphertext)
      const combined = new Uint8Array(iv.length + encrypted.byteLength);
      combined.set(iv);
      combined.set(new Uint8Array(encrypted), iv.length);
      const encryptedSecret = `AES-GCM-256:v1:${btoa(String.fromCharCode(...combined))}`;

      // Store/update OAuth credentials with encryption version tracking
      const { error: credError } = await supabaseClient
        .from('zendesk_oauth_clients')
        .upsert({
          subdomain: normalizedSubdomain,
          client_id: client_id,
          client_secret_enc: encryptedSecret,  // Use _enc column name
          encryption_version: 'v1',
          scopes: scopes,
          redirect_uri: 'https://api.catchalyze.com/zendesk/oauth/callback'
        }, { onConflict: 'subdomain' });

      if (credError) throw credError;

      // Update account mapping
      const { error: mappingError } = await supabaseClient
        .from('zendesk_account_mapping')
        .upsert({
          subdomain: normalizedSubdomain,
          account_id: userAccount.account_id
        }, { onConflict: 'subdomain' });

      if (mappingError) throw mappingError;

      console.log(`Zendesk credentials stored successfully for subdomain: ${normalizedSubdomain}`);

      return new Response(
        JSON.stringify({ 
          success: true, 
          subdomain: normalizedSubdomain,
          message: 'Zendesk app credentials validated and stored successfully.'
        }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );

    } else if (req.method === 'GET') {
      // Get user's current Zendesk configuration
      const { data: userAccount } = await supabaseClient
        .from('user_accounts')
        .select('account_id')
        .eq('user_id', user.id)
        .single();

      if (!userAccount) {
        throw new Error('User account not found');
      }

      const { data: mapping } = await supabaseClient
        .from('zendesk_account_mapping')
        .select('subdomain')
        .eq('account_id', userAccount.account_id)
        .single();

      if (!mapping) {
        return new Response(
          JSON.stringify({ configured: false }),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        );
      }

      const { data: credentials } = await supabaseClient
        .from('zendesk_oauth_clients')
        .select('client_id, scopes, redirect_uri, encryption_version')
        .eq('subdomain', mapping.subdomain)
        .single();

      return new Response(
        JSON.stringify({ 
          configured: true,
          subdomain: mapping.subdomain,
          client_id: credentials?.client_id || '',
          scopes: credentials?.scopes || 'read write',
          redirect_uri: credentials?.redirect_uri || 'https://api.catchalyze.com/zendesk/oauth/callback',
          encryption_version: credentials?.encryption_version || 'legacy',
          needs_security_upgrade: credentials?.encryption_version !== 'v1'
        }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );

    } else {
      return new Response('Method not allowed', { status: 405, headers: corsHeaders });
    }

  } catch (error) {
    console.error('Error in zendesk-credentials:', error);
    return new Response(
      JSON.stringify({ error: error instanceof Error ? error.message : 'Unknown error' }),
      { 
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    );
  }
});