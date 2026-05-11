import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Brain, Lock, Users, Zap, Home } from 'lucide-react';

interface BetaAccessRequiredProps {
  onBetaAccess: () => void;
  onBackToHome: () => void;
}

export const BetaAccessRequired: React.FC<BetaAccessRequiredProps> = ({ onBetaAccess, onBackToHome }) => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <Card className="max-w-lg w-full">
        <CardHeader className="text-center">
          <div className="w-16 h-16 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-xl flex items-center justify-center mx-auto mb-4">
            <Lock className="w-8 h-8 text-white" />
          </div>
          <CardTitle className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
            Beta Access Required
          </CardTitle>
        </CardHeader>
        
        <CardContent className="space-y-6">
          <div className="text-center">
            <p className="text-muted-foreground text-lg leading-relaxed">
              Catchalyze is currently in private beta. Join our exclusive early access program to start monitoring customer insights.
            </p>
          </div>

          {/* Features Preview */}
          <div className="space-y-4">
            <h3 className="font-semibold text-center text-slate-900">What You'll Get Access To:</h3>
            <div className="grid gap-3">
              <div className="flex items-center space-x-3 p-3 bg-blue-50 rounded-lg">
                <Brain className="h-5 w-5 text-blue-600" />
                <span className="text-sm font-medium">Real-time customer sentiment analysis</span>
              </div>
              <div className="flex items-center space-x-3 p-3 bg-emerald-50 rounded-lg">
                <Zap className="h-5 w-5 text-emerald-600" />
                <span className="text-sm font-medium">Trending issue detection</span>
              </div>
              <div className="flex items-center space-x-3 p-3 bg-purple-50 rounded-lg">
                <Users className="h-5 w-5 text-purple-600" />
                <span className="text-sm font-medium">Unified customer health scoring</span>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            <Button 
              onClick={onBetaAccess} 
              className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700"
              size="lg"
            >
              Apply for Beta Access
            </Button>
            <p className="text-sm text-center text-muted-foreground">
              Already paid? Your access will be approved within a few minutes. Refresh the page or contact support if you need assistance.
            </p>
            <Button 
              onClick={onBackToHome} 
              variant="outline"
              className="w-full"
              size="lg"
            >
              <Home className="w-4 h-4 mr-2" />
              Back to Home
            </Button>
            <p className="text-xs text-center text-muted-foreground">
              Applications are reviewed within 24 hours
            </p>
          </div>

        </CardContent>
      </Card>
    </div>
  );
};
