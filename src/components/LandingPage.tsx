import React from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Brain, 
  TrendingUp, 
  Users, 
  AlertTriangle, 
  Activity,
  Bell,
  ArrowUpRight,
  Zap
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { CookiePolicy } from '@/components/CookiePolicy';
import { PrivacyPolicy } from '@/components/PrivacyPolicy';

interface LandingPageProps {
  onBetaAccess?: () => void;
}

export const LandingPage = ({ onBetaAccess }: LandingPageProps) => {
  const navigate = useNavigate();
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-lg flex items-center justify-center">
                <Brain className="w-5 h-5 text-white" />
              </div>
              <span className="text-xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                Catchalyze
              </span>
            </div>
            <div className="flex items-center space-x-4">
              <Button variant="ghost" onClick={() => navigate('/login')}>
                Sign In
              </Button>
              <Button onClick={() => navigate('/login')} className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700">
                Get Started
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="container mx-auto px-6 pt-16 pb-8">
        <div className="text-center max-w-4xl mx-auto">
          <Badge className="mb-6 bg-blue-100 text-blue-700 hover:bg-blue-200">
            <Zap className="w-3 h-3 mr-1" />
            Customer Intelligence
          </Badge>
          <h1 className="text-5xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-slate-900 via-blue-800 to-indigo-800 bg-clip-text text-transparent leading-tight md:leading-[1.29]">
            Stop Customer Issues
            <span className="block">Before They Escalate</span>
          </h1>
          <p className="text-xl text-slate-600 mb-10 leading-relaxed">
            Real-time monitoring of customer interactions to detect emerging problems in seconds—before they impact revenue and retention.
          </p>
          <div className="grid md:grid-cols-2 gap-8 mb-12 max-w-4xl mx-auto">
            <Card className="border hover:border-slate-200 transition-colors bg-white">
              <CardHeader className="pt-6 px-6 pb-0">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-indigo-500 rounded-lg flex items-center justify-center">
                    <Activity className="w-6 h-6 text-white" />
                  </div>
                  <CardTitle>Unified Health Score</CardTitle>
                </div>
                <CardDescription className="mt-3 pb-6">
                  Customer health scoring that combines support tickets, conversation sentiment, and engagement patterns.
                </CardDescription>
              </CardHeader>
            </Card>
            
            <Card className="border hover:border-slate-200 transition-colors bg-white">
              <CardHeader className="pt-6 px-6 pb-0">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-gradient-to-br from-green-500 to-emerald-500 rounded-lg flex items-center justify-center">
                    <TrendingUp className="w-6 h-6 text-white" />
                  </div>
                  <CardTitle>Trending Issues</CardTitle>
                </div>
                <CardDescription className="mt-3 pb-6">
                  Automatically detect emerging issues in real-time before they impact hundreds of customers.
                </CardDescription>
              </CardHeader>
              </Card>
          </div>
          
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button 
              size="lg" 
              variant="outline" 
              className="px-8 py-3 text-lg"
              onClick={() => window.open('https://youtu.be/rVJit0_MLHk', '_blank')}
            >
              See How It Works
            </Button>
          </div>
        </div>
      </section>

      {/* Problem Section */}
      <section className="container mx-auto px-6 py-16 bg-slate-50">
        <div className="text-center max-w-3xl mx-auto">
          <h2 className="text-3xl font-bold text-slate-900 mb-6">The Hidden Cost of Reactive Support</h2>
          <p className="text-xl text-slate-600 leading-relaxed">
            Teams waste 5-10 hours weekly manually hunting for customer issues across Slack, Zendesk, and spreadsheets. By the time patterns emerge, it's often too late.
          </p>
        </div>
      </section>

      {/* Problem/Solution Clarity */}
      <section className="container mx-auto px-6 py-16">
        <div className="text-center mb-12">
          <h2 className="text-3xl md:text-4xl font-bold mb-6 text-slate-900">
            How many times have you discovered a widespread issue hours too late?
          </h2>
        </div>
        
        <div className="grid md:grid-cols-2 gap-8 max-w-5xl mx-auto">
          <Card className="border hover:border-slate-200 transition-colors bg-white">
            <CardHeader>
              <CardTitle className="text-slate-900">Real-time vs Hours</CardTitle>
              <CardDescription>
                When 50+ customers report login issues, you get instant alerts, not delayed discovery
              </CardDescription>
            </CardHeader>
          </Card>
          
          <Card className="border hover:border-slate-200 transition-colors bg-white">
            <CardHeader>
              <CardTitle className="text-slate-900">Prevent Escalation</CardTitle>
              <CardDescription>
                Detect emerging issues when they affect 5 customers, not 500
              </CardDescription>
            </CardHeader>
          </Card>
        </div>
      </section>

      {/* Beta Access */}
      <section className="container mx-auto px-6 py-20">
        <div className="text-center mb-16">
          <p className="text-slate-600 text-2xl">Be among the first to experience real-time customer intelligence</p>
        </div>
        
        <div className="max-w-2xl mx-auto">
          <Card className="border-2 border-blue-200 bg-gradient-to-br from-blue-50 to-indigo-50">
            <CardHeader className="text-center">
              <Badge className="mx-auto mb-4 bg-gradient-to-r from-blue-600 to-indigo-600">
                <Bell className="w-3 h-3 mr-1" />
                Early Access
              </Badge>
              <CardTitle className="text-2xl">Beta Access - $199</CardTitle>
              <CardDescription className="text-lg mt-4">
                Get exclusive early access to Catchalyze for a one-time investment of $199 and secure significant savings on launch pricing
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6 pt-0">
              <div className="space-y-3">
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span>✓ 30-day money-back guarantee</span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span>✓ Cancel anytime during beta</span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span>✓ Your data stays private and secure</span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                  <span>✓ Full platform access during beta</span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                  <span>Direct feedback channel with our team</span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                  <span>Priority support and feature requests</span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                  <span>Exclusive pricing when we launch</span>
                </div>
              </div>
              <Button 
                onClick={() => onBetaAccess?.()} 
                className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700" 
                size="lg"
              >
                Request Beta Access
              </Button>
              <p className="text-center text-sm text-slate-500">
                One-time payment • Risk-free with money-back guarantee
              </p>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="container mx-auto px-6 py-20 bg-slate-50">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-4 text-slate-900">
            Frequently Asked Questions
          </h2>
        </div>
        
        <div className="max-w-4xl mx-auto space-y-8">
          <Card>
            <CardHeader>
              <CardTitle className="text-xl">How is this different from existing support tools?</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-slate-600">
                We don't replace your support tools, we connect them. Instead of manually checking Slack, Zendesk, and other channels, Catchalyze automatically detects patterns across all your customer interactions.
              </p>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader>
              <CardTitle className="text-xl">What integrations do you support?</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-slate-600">
                Currently Slack and Zendesk, with more integrations coming based on user feedback.
              </p>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader>
              <CardTitle className="text-xl">How long does setup take?</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-slate-600">
                Under 5 minutes. Just connect your Slack and Zendesk accounts.
              </p>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-slate-900 text-white">
        <div className="container mx-auto px-6 py-12">
          <div className="grid md:grid-cols-4 gap-8">
            <div className="col-span-2">
              <div className="flex items-center space-x-3 mb-4">
                <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-lg flex items-center justify-center">
                  <Brain className="w-5 h-5 text-white" />
                </div>
                <span className="text-xl font-bold">Catchalyze</span>
              </div>
              <p className="text-slate-300 mb-4 max-w-md">
                Real-time customer intelligence to detect and prevent issues before they escalate.
              </p>
              <div className="text-sm text-slate-400">
                <p>Email: <a href="mailto:support@catchalyze.com" className="text-blue-400 hover:underline">support@catchalyze.com</a></p>
              </div>
            </div>
            
            <div className="col-start-4">
              <h4 className="font-semibold mb-4">Legal</h4>
              <ul className="space-y-2 text-slate-300">
                <li><a href="#" onClick={(e) => { e.preventDefault(); window.open('https://app.termly.io/policy-viewer/policy.html?policyUUID=12d963f9-abf2-4ee2-ab0f-2cce1aeec87c', '_blank'); }} className="hover:text-white transition-colors">Terms of Service</a></li>
                <li>
                  <PrivacyPolicy>
                    <a href="#" className="hover:text-white transition-colors">Privacy Policy</a>
                  </PrivacyPolicy>
                </li>
                <li>
                  <CookiePolicy>
                    <a href="#" className="hover:text-white transition-colors">Cookie Policy</a>
                  </CookiePolicy>
                </li>
              </ul>
            </div>
          </div>
          
          <div className="border-t border-slate-700 mt-12 pt-8 text-center text-slate-400">
            <p>&copy; 2025 Catchalyze. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
};