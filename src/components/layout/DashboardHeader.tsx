import { Brain, Settings, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { UserDropdown } from '@/components/auth/UserDropdown';

interface User {
  id: string;
  email: string;
  name: string;
  avatar_url?: string;
}

interface Account {
  id: string;
  name: string;
  slug: string;
}

interface DashboardHeaderProps {
  user: User;
  account: Account;
  onLogout: () => Promise<void>;
  onRefresh?: () => void;
  onGenerateInsights?: () => void;
  refreshing?: boolean;
}

export function DashboardHeader({ 
  user, 
  account, 
  onLogout, 
  onRefresh, 
  onGenerateInsights, 
  refreshing = false 
}: DashboardHeaderProps) {
  return (
    <header className="bg-white border-b">
      <div className="container mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-lg flex items-center justify-center">
                <Brain className="w-5 h-5 text-white" />
              </div>
              <span className="text-xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                Catchalyze
              </span>
            </div>
            <div className="hidden md:flex items-center">
              <span className="text-sm text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
                {account.name}
              </span>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            {onRefresh && (
              <Button variant="ghost" size="sm" onClick={onRefresh} disabled={refreshing}>
                <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
              </Button>
            )}
            {onGenerateInsights && (
              <Button variant="ghost" size="sm" onClick={onGenerateInsights} disabled={refreshing}>
                <Brain className="w-4 h-4" />
              </Button>
            )}
            <Button variant="ghost" size="sm">
              <Settings className="w-4 h-4" />
            </Button>
            <UserDropdown user={user} onLogout={onLogout} />
          </div>
        </div>
      </div>
    </header>
  );
}