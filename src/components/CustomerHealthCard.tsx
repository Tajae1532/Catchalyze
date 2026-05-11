
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface CustomerHealthCardProps {
  customer: {
    name: string;
    healthScore: number;
    trend: 'up' | 'down' | 'stable';
    risk: 'low' | 'medium' | 'high';
    lastContact: string;
    ticketCount: number;
  };
}

export const CustomerHealthCard = ({ customer }: CustomerHealthCardProps) => {
  const getTrendIcon = () => {
    switch (customer.trend) {
      case 'up':
        return <TrendingUp className="w-4 h-4 text-green-500" />;
      case 'down':
        return <TrendingDown className="w-4 h-4 text-red-500" />;
      default:
        return <Minus className="w-4 h-4 text-slate-400" />;
    }
  };

  const getRiskColor = () => {
    switch (customer.risk) {
      case 'high':
        return 'destructive';
      case 'medium':
        return 'default';
      default:
        return 'secondary';
    }
  };

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">{customer.name}</CardTitle>
          <Badge variant={getRiskColor() as any}>
            {customer.risk} risk
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">Health Score</span>
            <div className="flex items-center space-x-1">
              {getTrendIcon()}
              <span className="text-sm font-bold">{customer.healthScore}/100</span>
            </div>
          </div>
          <Progress value={customer.healthScore} className="h-2" />
        </div>
        
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-slate-500">Tickets</span>
            <p className="font-medium">{customer.ticketCount}</p>
          </div>
          <div>
            <span className="text-slate-500">Last Contact</span>
            <p className="font-medium">{customer.lastContact}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
