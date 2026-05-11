
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { AlertTriangle, Info, CheckCircle, TrendingUp } from 'lucide-react';

interface InsightCardProps {
  insight: {
    id: string;
    title: string;
    description: string;
    type: 'alert' | 'info' | 'success' | 'trend';
    priority: 'high' | 'medium' | 'low';
    confidence: number;
    actionable: boolean;
  };
}

export const InsightCard = ({ insight }: InsightCardProps) => {
  const getIcon = () => {
    switch (insight.type) {
      case 'alert':
        return <AlertTriangle className="w-5 h-5 text-red-500" />;
      case 'success':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'trend':
        return <TrendingUp className="w-5 h-5 text-blue-500" />;
      default:
        return <Info className="w-5 h-5 text-blue-500" />;
    }
  };

  const getBorderColor = () => {
    switch (insight.type) {
      case 'alert':
        return 'border-red-200';
      case 'success':
        return 'border-green-200';
      case 'trend':
        return 'border-blue-200';
      default:
        return 'border-slate-200';
    }
  };

  const getPriorityColor = () => {
    switch (insight.priority) {
      case 'high':
        return 'destructive';
      case 'medium':
        return 'default';
      default:
        return 'secondary';
    }
  };

  return (
    <Card className={`${getBorderColor()} border-2 hover:shadow-md transition-all`}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-3">
            {getIcon()}
            <div>
              <CardTitle className="text-base">{insight.title}</CardTitle>
              <div className="flex items-center space-x-2 mt-1">
                <Badge variant={getPriorityColor() as any} className="text-xs">
                  {insight.priority}
                </Badge>
                <span className="text-xs text-slate-500">
                  {insight.confidence}% confidence
                </span>
              </div>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <CardDescription className="text-sm leading-relaxed">
          {insight.description}
        </CardDescription>
        
        {insight.actionable && (
          <div className="flex space-x-2">
            <Button size="sm" variant="outline">
              View Details
            </Button>
            <Button size="sm">
              Take Action
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
