import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { useToast } from '@/hooks/use-toast';
import { ArrowLeft, CheckCircle } from 'lucide-react';

interface BetaApplicationProps {
  onComplete: () => void;
  onCancel: () => void;
}

const PUBLIC_BASE_URL = import.meta.env.VITE_PUBLIC_BASE_URL || 'http://localhost:8000';

export const BetaApplicationForm: React.FC<BetaApplicationProps> = ({ 
  onComplete, 
  onCancel 
}) => {
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    company: '',
    role: '',
    current_tools: '',
    time_spent_weekly: '',
    pain_points: '',
    company_size: '',
    why_interested: '',
    ready_to_pay: false,
    start_timeline: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});
  const [isSubmitted, setIsSubmitted] = useState(false);
  const { toast } = useToast();

  // Save form data to localStorage on changes
  useEffect(() => {
    localStorage.setItem('betaApplicationData', JSON.stringify(formData));
  }, [formData]);

  // Load saved data on mount
  useEffect(() => {
    const saved = localStorage.getItem('betaApplicationData');
    if (saved) {
      try {
        setFormData(JSON.parse(saved));
      } catch (e) {
        // Ignore invalid saved data
      }
    }
  }, []);

  const updateFormData = (field: string, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    // Clear validation error when user starts typing
    if (validationErrors[field]) {
      setValidationErrors(prev => ({ ...prev, [field]: '' }));
    }
  };

  // Inside BetaApplicationForm component, before the main return:
  const ConfirmationMessage = () => (
    <div className="text-center space-y-4 py-8">
      <div className="mx-auto w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
        <CheckCircle className="w-8 h-8 text-green-600" />
      </div>
      
      <div className="space-y-2">
        <h3 className="text-xl font-semibold text-gray-900">Application Submitted!</h3>
        <p className="text-gray-600">
          Thank you for your interest in Catchalyze beta access.
        </p>
      </div>
      
      <div className="bg-blue-50 p-4 rounded-lg space-y-2">
        <h4 className="font-medium text-blue-900">What happens next?</h4>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>• We'll review your application within an hour</li>
          <li>• If approved, you'll receive a PayPal invoice for $199</li>
          <li>• Beta access begins immediately after payment</li>
        </ul>
      </div>
      
      <div className="space-y-3">
        <p className="text-sm text-gray-600">
          Questions? Email <a href="mailto:support@catchalyze.com" className="text-blue-600 hover:underline">support@catchalyze.com</a>
        </p>
        
        <div className="flex gap-3 justify-center">
          <Button onClick={onComplete} className="px-6">
            Back to Homepage
          </Button>
        </div>
      </div>
    </div>
  );

  const validateStep = (step: number): boolean => {
    const errors: Record<string, string> = {};
    
    switch (step) {
      case 1:
        if (!formData.name.trim()) errors.name = 'Name is required';
        if (!formData.email.trim()) errors.email = 'Email is required';
        if (!formData.company.trim()) errors.company = 'Company is required';
        if (!formData.role.trim()) errors.role = 'Role is required';
        break;
      case 2:
        if (!formData.current_tools.trim()) errors.current_tools = 'Current tools are required';
        if (!formData.time_spent_weekly) errors.time_spent_weekly = 'Time spent weekly is required';
        if (!formData.pain_points.trim()) errors.pain_points = 'Pain points are required';
        break;
      case 3:
        if (!formData.company_size) errors.company_size = 'Company size is required';
        if (!formData.why_interested.trim()) errors.why_interested = 'Interest reason is required';
        break;
      case 4:
        if (!formData.ready_to_pay) errors.ready_to_pay = 'Must confirm readiness to pay';
        if (!formData.start_timeline) errors.start_timeline = 'Start timeline is required';
        break;
    }
    
    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const submitApplication = async () => {
    if (!validateStep(4)) return;
    
    setIsSubmitting(true);
    setSubmitError('');

    try {
      const response = await fetch(`${PUBLIC_BASE_URL}/api/beta/application`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || data.error || `HTTP ${response.status}`);
      }

      // Clear saved data on successful submission
      localStorage.removeItem('betaApplicationData');
      
      toast({
        title: 'Application Submitted!',
        description: 'We\'ll review your application and contact you within an hour.',
      });
      
      setIsSubmitted(true);
      
    } catch (error: any) {
      setSubmitError(error.message || 'Submission failed');
      toast({
        title: 'Submission Failed',
        description: error.message || 'Please try again.',
        variant: 'destructive',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const nextStep = () => {
    if (validateStep(currentStep)) {
      const newStep = Math.min(currentStep + 1, 4);
      setCurrentStep(newStep);
    }
  };

  const canGoBack = currentStep > 1;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 p-6 flex items-center justify-center">
      <Card className="w-full max-w-2xl mx-auto">
        <CardHeader>
          <div className="flex justify-between items-center">
            <div>
              <CardTitle className="text-2xl bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                Beta Access Application
              </CardTitle>
              <CardDescription>Step {currentStep} of 4</CardDescription>
            </div>
            <Button variant="ghost" onClick={onCancel} className="text-muted-foreground">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Home
            </Button>
          </div>
          
          {/* Progress bar */}
          <div className="w-full bg-secondary rounded-full h-2 mt-4">
            <div 
              className="bg-gradient-to-r from-blue-600 to-indigo-600 rounded-full h-2 transition-all duration-300" 
              style={{ width: `${(currentStep / 4) * 100}%` }}
            />
          </div>
        </CardHeader>
        
        <CardContent className="space-y-6">
          {/* Step 1: Contact Info */}
          {isSubmitted ? (
            <ConfirmationMessage />
          ) : (
            <>
            {currentStep === 1 && (
              <div className="space-y-4">
                <div className="text-center mb-6">
                  <h3 className="text-lg font-semibold mb-2">Let's get to know you</h3>
                  <p className="text-muted-foreground">Tell us about yourself and your company</p>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="name">Full Name</Label>
                    <Input
                      id="name"
                      value={formData.name}
                      onChange={(e) => updateFormData('name', e.target.value)}
                      placeholder="John Smith"
                      className={validationErrors.name ? 'border-destructive' : ''}
                    />
                    {validationErrors.name && <p className="text-sm text-destructive">{validationErrors.name}</p>}
                  </div>
                  
                  <div className="space-y-2">
                    <Label htmlFor="email">Email</Label>
                    <Input
                      id="email"
                      type="email"
                      value={formData.email}
                      onChange={(e) => updateFormData('email', e.target.value)}
                      placeholder="john@company.com"
                      className={validationErrors.email ? 'border-destructive' : ''}
                    />
                    {validationErrors.email && <p className="text-sm text-destructive">{validationErrors.email}</p>}
                  </div>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="company">Company</Label>
                    <Input
                      id="company"
                      value={formData.company}
                      onChange={(e) => updateFormData('company', e.target.value)}
                      placeholder="Acme Corp"
                      className={validationErrors.company ? 'border-destructive' : ''}
                    />
                    {validationErrors.company && <p className="text-sm text-destructive">{validationErrors.company}</p>}
                  </div>
                  
                  <div className="space-y-2">
                    <Label htmlFor="role">Your Role</Label>
                    <Input
                      id="role"
                      value={formData.role}
                      onChange={(e) => updateFormData('role', e.target.value)}
                      placeholder="Customer Success Manager"
                      className={validationErrors.role ? 'border-destructive' : ''}
                    />
                    {validationErrors.role && <p className="text-sm text-destructive">{validationErrors.role}</p>}
                  </div>
                </div>
              </div>
            )}

            {/* Step 2: Current Process */}
            {currentStep === 2 && (
              <div className="space-y-4">
                <div className="text-center mb-6">
                  <h3 className="text-lg font-semibold mb-2">Your current situation</h3>
                  <p className="text-muted-foreground">Help us understand your current customer monitoring process</p>
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="current_tools">What tools do you currently use for customer support/monitoring?</Label>
                  <Textarea
                    id="current_tools"
                    value={formData.current_tools}
                    onChange={(e) => updateFormData('current_tools', e.target.value)}
                    placeholder="Zendesk, Slack, Intercom, custom dashboards..."
                    rows={3}
                    className={validationErrors.current_tools ? 'border-destructive' : ''}
                  />
                  {validationErrors.current_tools && <p className="text-sm text-destructive">{validationErrors.current_tools}</p>}
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="time_spent_weekly">How much time do you spend weekly on customer issue monitoring?</Label>
                  <Select value={formData.time_spent_weekly} onValueChange={(value) => updateFormData('time_spent_weekly', value)}>
                    <SelectTrigger className={validationErrors.time_spent_weekly ? 'border-destructive' : ''}>
                      <SelectValue placeholder="Select time range" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="1-5 hours">1-5 hours</SelectItem>
                      <SelectItem value="5-10 hours">5-10 hours</SelectItem>
                      <SelectItem value="10-20 hours">10-20 hours</SelectItem>
                      <SelectItem value="20+ hours">20+ hours</SelectItem>
                    </SelectContent>
                  </Select>
                  {validationErrors.time_spent_weekly && <p className="text-sm text-destructive">{validationErrors.time_spent_weekly}</p>}
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="pain_points">What are your biggest pain points with current customer monitoring?</Label>
                  <Textarea
                    id="pain_points"
                    value={formData.pain_points}
                    onChange={(e) => updateFormData('pain_points', e.target.value)}
                    placeholder="Issues are discovered too late, manual monitoring is time-consuming, no early warning system..."
                    rows={4}
                    className={validationErrors.pain_points ? 'border-destructive' : ''}
                  />
                  {validationErrors.pain_points && <p className="text-sm text-destructive">{validationErrors.pain_points}</p>}
                </div>
              </div>
            )}

            {/* Step 3: Fit Assessment */}
            {currentStep === 3 && (
              <div className="space-y-4">
                <div className="text-center mb-6">
                  <h3 className="text-lg font-semibold mb-2">Company fit assessment</h3>
                  <p className="text-muted-foreground">Help us understand if Catchalyze is right for your organization</p>
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="company_size">Company size</Label>
                  <Select value={formData.company_size} onValueChange={(value) => updateFormData('company_size', value)}>
                    <SelectTrigger className={validationErrors.company_size ? 'border-destructive' : ''}>
                      <SelectValue placeholder="Select company size" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="1-10 employees">1-10 employees</SelectItem>
                      <SelectItem value="11-50 employees">11-50 employees</SelectItem>
                      <SelectItem value="51-200 employees">51-200 employees</SelectItem>
                      <SelectItem value="201-1000 employees">201-1000 employees</SelectItem>
                      <SelectItem value="1000+ employees">1000+ employees</SelectItem>
                    </SelectContent>
                  </Select>
                  {validationErrors.company_size && <p className="text-sm text-destructive">{validationErrors.company_size}</p>}
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="why_interested">Why are you interested in Catchalyze?</Label>
                  <Textarea
                    id="why_interested"
                    value={formData.why_interested}
                    onChange={(e) => updateFormData('why_interested', e.target.value)}
                    placeholder="We need early warning for customer issues, proactive customer success, real-time sentiment monitoring..."
                    rows={4}
                    className={validationErrors.why_interested ? 'border-destructive' : ''}
                  />
                  {validationErrors.why_interested && <p className="text-sm text-destructive">{validationErrors.why_interested}</p>}
                </div>
              </div>
            )}

            {/* Step 4: Commitment */}
            {currentStep === 4 && (
              <div className="space-y-4">
                <div className="text-center mb-6">
                  <h3 className="text-lg font-semibold mb-2">Ready to get started?</h3>
                  <p className="text-muted-foreground">Final details to complete your beta application</p>
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="start_timeline">When would you like to start using Catchalyze?</Label>
                  <Select value={formData.start_timeline} onValueChange={(value) => updateFormData('start_timeline', value)}>
                    <SelectTrigger className={validationErrors.start_timeline ? 'border-destructive' : ''}>
                      <SelectValue placeholder="Select timeline" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Immediately">Immediately</SelectItem>
                      <SelectItem value="Within 1 week">Within 1 week</SelectItem>
                      <SelectItem value="Within 1 month">Within 1 month</SelectItem>
                      <SelectItem value="Within 3 months">Within 3 months</SelectItem>
                    </SelectContent>
                  </Select>
                  {validationErrors.start_timeline && <p className="text-sm text-destructive">{validationErrors.start_timeline}</p>}
                </div>
                
                <div className="bg-gradient-to-br from-blue-50 to-indigo-50 p-6 rounded-lg border border-blue-200">
                  <div className="flex items-start space-x-3">
                    <Checkbox
                      id="ready_to_pay"
                      checked={formData.ready_to_pay}
                      onCheckedChange={(checked) => updateFormData('ready_to_pay', checked)}
                      className={validationErrors.ready_to_pay ? 'border-destructive' : ''}
                    />
                    <div className="space-y-2">
                      <Label htmlFor="ready_to_pay" className="text-base font-medium cursor-pointer">
                        I'm ready to invest $199 for beta access
                      </Label>
                      <p className="text-sm text-muted-foreground">
                        This one-time payment includes full platform access during beta, priority support, 
                        and exclusive pricing when we launch.
                      </p>
                    </div>
                  </div>
                  {validationErrors.ready_to_pay && <p className="text-sm text-destructive mt-2">{validationErrors.ready_to_pay}</p>}
                </div>

                {submitError && (
                  <div className="bg-destructive/10 border border-destructive/20 rounded-md p-4">
                    <p className="text-destructive text-sm">{submitError}</p>
                  </div>
                )}
              </div>
            )}

            {/* Navigation buttons */}
            <div className="flex gap-3 pt-4">
              {canGoBack && (
                <Button variant="outline" onClick={() => setCurrentStep(prev => prev - 1)}>
                  Previous
                </Button>
              )}
              {currentStep < 4 ? (
                <Button onClick={nextStep} className="flex-1">
                  Continue
                </Button>
              ) : (
                <Button 
                  onClick={submitApplication} 
                  className="flex-1 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700" 
                  disabled={isSubmitting || !formData.ready_to_pay || !formData.start_timeline}
                >
                  {isSubmitting ? (
                    <>
                      <CheckCircle className="w-4 h-4 mr-2 animate-spin" />
                      Submitting...
                    </>
                  ) : (
                    'Submit Application'
                  )}
                </Button>
              )}
            </div>
          </>
          )}
        </CardContent>
      </Card>
    </div>
  );
};