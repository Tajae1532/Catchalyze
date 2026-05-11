import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { CheckCircle2, AlertCircle, Loader2, ExternalLink, Copy, Check } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

interface ZendeskOnboardingWizardProps {
  onComplete: () => void;
  onCancel: () => void;
}

const PUBLIC_BASE_URL = import.meta.env.VITE_PUBLIC_BASE_URL || 'http://localhost:8000';

const REQUIRED_CONFIG = {
  name: 'Catchalyze',
  description: 'Creating OAuth',
  company: 'Catchalyze',
  identifier: 'catchalyze',
  clientKind: 'Confidential',
  redirectUrl: 'https://api.catchalyze.com/zendesk/oauth/callback',
  scopes: 'read write'
};

export const ZendeskOnboardingWizard: React.FC<ZendeskOnboardingWizardProps> = ({ 
  onComplete, 
  onCancel 
}) => {
  const [currentStep, setCurrentStep] = useState(1);
  const [subdomain, setSubdomain] = useState('');
  const [clientId, setClientId] = useState('');
  const [clientSecret, setClientSecret] = useState('');
  const [isValidating, setIsValidating] = useState(false);
  const [isValidated, setIsValidated] = useState(false);
  const [validationError, setValidationError] = useState('');
  const [copied, setCopied] = useState<string | null>(null);
  const { toast } = useToast();

  const copyToClipboard = async (text: string, label: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(label);
      setTimeout(() => setCopied(null), 2000);
      toast({
        title: 'Copied!',
        description: `${label} copied to clipboard`,
      });
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }
  };

  const normalizeSubdomain = (input: string) => {
    let normalized = input.trim().toLowerCase();
    if (normalized.includes('.zendesk.com')) {
      normalized = normalized.split('.zendesk.com')[0];
    }
    if (normalized.includes('://')) {
      const urlParts = normalized.split('://')[1];
      if (urlParts) {
        normalized = urlParts.split('.zendesk.com')[0];
      }
    }
    return normalized;
  };

        const validateAndSave = async () => {
          if (!subdomain || !clientId || !clientSecret) {
            setValidationError('All fields are required');
            return;
          }

          setIsValidating(true);
          setValidationError('');

          try {
            const response = await fetch(`${PUBLIC_BASE_URL}/api/zendesk/credentials`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              credentials: 'include', // Send auth cookies
              body: JSON.stringify({
                subdomain: normalizeSubdomain(subdomain),
                client_id: clientId,
                client_secret: clientSecret,
                scopes: REQUIRED_CONFIG.scopes
              })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
              throw new Error(data.detail || data.error || `HTTP ${response.status}`);
            }

            setIsValidated(true);
            toast({
              title: 'Success!',
              description: 'Zendesk app configuration validated and saved.',
            });
            
            setTimeout(() => setCurrentStep(4), 1000);
            
          } catch (error: any) {
            setValidationError(error.message || 'Validation failed');
            toast({
              title: 'Validation Failed',
              description: error.message || 'Please check your configuration and try again.',
              variant: 'destructive',
            });
          } finally {
            setIsValidating(false);
          }
        };

  const connectZendesk = () => {
    const normalizedSubdomain = normalizeSubdomain(subdomain);
    window.location.href = `${PUBLIC_BASE_URL}/zendesk/oauth/start?subdomain=${encodeURIComponent(normalizedSubdomain)}`;
  };

  const renderStep = () => {
    switch (currentStep) {
      case 1:
        return (
          <div className="space-y-4">
            <div className="text-center">
              <h3 className="text-lg font-semibold mb-2">Step 1: Create Zendesk OAuth App</h3>
              <p className="text-muted-foreground mb-4">
                First, you'll need to create an OAuth app in your Zendesk Admin settings. Go to Admin → Apps and integrations → APIs → OAuth Clients and create a new OAuth client.
              </p>
            </div>

            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                <strong>Important:</strong> You need admin permissions in your Zendesk instance to create an OAuth app.
              </AlertDescription>
            </Alert>

            <div className="bg-muted p-4 rounded-lg space-y-3">
              <h4 className="font-medium">Required Configuration:</h4>
              <div className="grid grid-cols-1 gap-3 text-sm">
                <div className="flex justify-between items-center">
                  <span className="font-medium">Name:</span>
                  <div className="flex items-center gap-2">
                    <code className="bg-background px-2 py-1 rounded">{REQUIRED_CONFIG.name}</code>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => copyToClipboard(REQUIRED_CONFIG.name, 'Name')}
                    >
                      {copied === 'Name' ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                    </Button>
                  </div>
                </div>
                <div className="flex justify-between items-center">
                  <span className="font-medium">Description:</span>
                  <div className="flex items-center gap-2">
                    <code className="bg-background px-2 py-1 rounded">{REQUIRED_CONFIG.description}</code>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => copyToClipboard(REQUIRED_CONFIG.description, 'Description')}
                    >
                      {copied === 'Description' ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                    </Button>
                  </div>
                </div>
                <div className="flex justify-between items-center">
                  <span className="font-medium">Company:</span>
                  <div className="flex items-center gap-2">
                    <code className="bg-background px-2 py-1 rounded">{REQUIRED_CONFIG.company}</code>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => copyToClipboard(REQUIRED_CONFIG.company, 'Company')}
                    >
                      {copied === 'Company' ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                    </Button>
                  </div>
                </div>
                <div className="flex justify-between items-center">
                  <span className="font-medium">Client Kind:</span>
                  <div className="flex items-center gap-2">
                    <code className="bg-background px-2 py-1 rounded">{REQUIRED_CONFIG.clientKind}</code>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => copyToClipboard(REQUIRED_CONFIG.clientKind, 'Client Kind')}
                    >
                      {copied === 'Client Kind' ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                    </Button>
                  </div>
                </div>
                <div className="flex justify-between items-center">
                  <span className="font-medium">Redirect URL:</span>
                  <div className="flex items-center gap-2">
                    <code className="bg-background px-2 py-1 rounded text-xs">{REQUIRED_CONFIG.redirectUrl}</code>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => copyToClipboard(REQUIRED_CONFIG.redirectUrl, 'Redirect URL')}
                    >
                      {copied === 'Redirect URL' ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                    </Button>
                  </div>
                </div>
              </div>
            </div>

            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                <strong>Note:</strong> For the Unique Identifier field, Zendesk will automatically use the lowercase version of the name ("catchalyze"). You can keep this default value.
              </AlertDescription>
            </Alert>

            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                <strong>Important:</strong> After creating the OAuth app, click "Save" to see the Client Secret. The Client Secret will only be shown once, so make sure to copy it before closing the dialog.
              </AlertDescription>
            </Alert>

            <div className="flex gap-2 pt-4">
              <Button variant="outline" onClick={onCancel}>
                Cancel
              </Button>
              <Button onClick={() => setCurrentStep(2)} className="flex-1">
                I've Created the OAuth App
                <ExternalLink className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </div>
        );

      case 2:
        return (
          <div className="space-y-4">
            <div className="text-center">
              <h3 className="text-lg font-semibold mb-2">Step 2: Enter Your Zendesk Details</h3>
              <p className="text-muted-foreground mb-4">
                Enter your Zendesk subdomain and the OAuth app credentials you just created.
              </p>
            </div>

            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="subdomain">Zendesk Subdomain</Label>
                <Input
                  id="subdomain"
                  placeholder="acme (for acme.zendesk.com)"
                  value={subdomain}
                  onChange={(e) => setSubdomain(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Just the subdomain part, not the full URL
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="clientId">Client ID</Label>
                <Input
                  id="clientId"
                  placeholder="Your OAuth app Client ID"
                  value={clientId}
                  onChange={(e) => setClientId(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  The Client ID is the Unique Identifier. In Zendesk, go to Admin → Apps and integrations → APIs → OAuth Clients to see the OAuth app you created and find the identifier.
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="clientSecret">Client Secret</Label>
                <Input
                  id="clientSecret"
                  type="password"
                  placeholder="Your OAuth app Client Secret"
                  value={clientSecret}
                  onChange={(e) => setClientSecret(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  This was only shown once when you created the app
                </p>
              </div>
            </div>

            <div className="flex gap-2 pt-4">
              <Button variant="outline" onClick={() => setCurrentStep(1)}>
                Back
              </Button>
              <Button onClick={() => setCurrentStep(3)} className="flex-1" disabled={!subdomain || !clientId || !clientSecret}>
                Continue
              </Button>
            </div>
          </div>
        );

      case 3:
        return (
          <div className="space-y-4">
            <div className="text-center">
              <h3 className="text-lg font-semibold mb-2">Step 3: Validate Configuration</h3>
              <p className="text-muted-foreground mb-4">
                We'll validate your configuration and save your credentials securely.
              </p>
            </div>

            <div className="bg-muted p-4 rounded-lg space-y-3">
              <h4 className="font-medium">Your Configuration:</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span>Zendesk URL:</span>
                  <span>{normalizeSubdomain(subdomain)}.zendesk.com</span>
                </div>
                <div className="flex justify-between">
                  <span>Client ID:</span>
                  <span className="font-mono">{clientId.substring(0, 8)}...</span>
                </div>
                <div className="flex justify-between">
                  <span>Redirect URL:</span>
                  <span className="text-xs">{REQUIRED_CONFIG.redirectUrl}</span>
                </div>
              </div>
            </div>

            {validationError && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{validationError}</AlertDescription>
              </Alert>
            )}

            {isValidated && (
              <Alert>
                <CheckCircle2 className="h-4 w-4" />
                <AlertDescription>
                  Configuration validated successfully! You can now connect to Zendesk.
                </AlertDescription>
              </Alert>
            )}

            <div className="flex gap-2 pt-4">
              <Button variant="outline" onClick={() => setCurrentStep(2)} disabled={isValidating}>
                Back
              </Button>
              <Button 
                onClick={validateAndSave} 
                className="flex-1" 
                disabled={isValidating || isValidated}
              >
                {isValidating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {isValidating ? 'Validating...' : isValidated ? 'Validated ✓' : 'Validate & Save'}
              </Button>
            </div>
          </div>
        );

      case 4:
        return (
          <div className="space-y-4">
            <div className="text-center">
              <CheckCircle2 className="h-12 w-12 text-green-500 mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">Step 4: Connect to Zendesk</h3>
              <p className="text-muted-foreground mb-4">
                Your configuration is saved! Now connect your Zendesk account to start receiving insights.
              </p>
            </div>

            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                You'll be redirected to Zendesk to authorize the connection. After authorization, 
                you'll be brought back to Catchalyze.
              </AlertDescription>
            </Alert>

            <div className="flex gap-2 pt-4">
              <Button variant="outline" onClick={onComplete}>
                Skip for Now
              </Button>
              <Button onClick={connectZendesk} className="flex-1">
                Connect Zendesk
                <ExternalLink className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <div className="flex justify-between items-center">
          <div>
            <CardTitle>Connect Zendesk</CardTitle>
            <CardDescription>
              Set up your Zendesk integration in 4 easy steps
            </CardDescription>
          </div>
          <div className="text-sm text-muted-foreground">
            Step {currentStep} of 4
          </div>
        </div>
        
        {/* Progress bar */}
        <div className="w-full bg-secondary rounded-full h-2 mt-4">
          <div 
            className="bg-primary rounded-full h-2 transition-all duration-300" 
            style={{ width: `${(currentStep / 4) * 100}%` }}
          />
        </div>
      </CardHeader>
      
      <CardContent>
        {renderStep()}
      </CardContent>
    </Card>
  );
};