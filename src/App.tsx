import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { LandingPage } from '@/components/LandingPage';
import { AuthProvider } from '@/contexts/AuthContext';
import Auth from '@/pages/Auth';
import { LoadingSpinner } from '@/components/common/LoadingSpinner';
import { 
  MessageSquare, 
  Zap, 
  TrendingUp, 
  Users, 
  MessageCircle, 
  Ticket, 
  Activity,
  Calendar,
  CheckCircle,
  AlertCircle,
  Clock,
  Loader2,
  RefreshCw,
  Search,
  AlertTriangle,
  Filter,
  ExternalLink,
  Brain
} from 'lucide-react';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar
} from 'recharts';

// Shadcn/ui Components
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { AlertDialog, AlertDialogAction, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from '@/hooks/use-toast';
import { Toaster } from '@/components/ui/toaster';
import { useToast } from "@/hooks/use-toast";
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert';
import { ZendeskOnboardingWizard } from '@/components/ZendeskOnboardingWizard';
import { BetaApplicationForm } from '@/components/BetaApplicationForm';
import { BetaAccessRequired } from '@/components/BetaAccessRequired';

// Types
interface Customer {
  id: string;
  name: string;
  email?: string;
  health_score: number;
  sentiment_score?: number;
  churn_risk: 'low' | 'medium' | 'high';
  last_interaction?: string;
}

interface Ticket {
  id: string;
  zendesk_ticket_id: string;
  subject: string;
  status: string;
  priority: string;
  sentiment_score?: number;
  created_at: string;
  customer_id?: string;
}

interface SlackMessage {
  id: string;
  text: string;
  user_id: string;
  sentiment_score?: number;
  created_at: string;
  slack_channel_id: string;
}

interface TrendingTopic {
  topic_id: string;
  title: string;
  keywords: string[];
  count_in_window: number;
  avg_sentiment: number;
  severity: 'critical' | 'high' | 'medium' | 'low';
  trend_type: string;
  window_duration: string;
  detected_at: string;
  timestamp?: string;
  evidence_ids?: {
    tickets: string[];
    slack_messages: string[];
  };
  evidence?: {
    tickets: any[];
    slack_messages: any[];
    details?: Array<{
      text: string;
      source: string;
      timestamp: string;
      type: 'ticket' | 'slack';
      link: string;
    }>;
  };
  recommended_action?: string;
  playbook_steps?: string[];
  affected_customers?: number;
  customer_percentage?: number;
  root_cause_hint?: string;
}

interface DashboardData {
  overview: {
    total_customers: number;
    average_health_score: number;
    high_risk_customers: number;
    critical_insights: number;
    todays_tickets: number;
    average_sentiment: number;
  };
  customers: Customer[];
  recent_tickets: Ticket[];
  recent_slack_messages: SlackMessage[];
  sentiment_trend?: Array<{ date: string; sentiment: number }>;
  ticket_status_breakdown?: Array<{ status: string; count: number }>;
  message_volume?: Array<{ date: string; messages: number }>;
  generated_at?: string;
  insights?: Array<{
    type: string;
    title: string;
    severity: string;
    keywords?: string[];
    evidence_counts?: { total: number };
  }>;
}

interface OAuthStatus {
  zendesk_connected: boolean;
  slack_connected: boolean;
}

interface ZendeskInfo {
  subdomain?: string;
  needs_security_upgrade?: boolean;
  encryption_version?: string;
}

const PUBLIC_BASE_URL = import.meta.env.VITE_PUBLIC_BASE_URL || 'http://localhost:8000';

const SHOW_DEBUG_PANELS = import.meta.env.VITE_SHOW_DEBUG_PANELS === 'true';



// Constants
const API_BASE_URL = PUBLIC_BASE_URL;

const TIME_RANGES = [
  { value: '24h', label: 'Last 24 hours' },
  { value: '7d', label: 'Last 7 days' },
  { value: '30d', label: 'Last 30 days' },
  { value: '90d', label: 'Last 90 days' }
];

const COLORS = ['hsl(var(--primary))', 'hsl(var(--secondary))', 'hsl(var(--accent))', 'hsl(var(--muted))'];

// Custom Hook for MCP API calls
// useMcpApi
const useMcpApi = () => {
  const makeRequest = React.useCallback(async (toolName: string, params: any = {}) => {
    // --- helpers ---
    const unwrapMcp = (payload: any) => {
      if (payload?.error) throw new Error(payload.error.message || 'MCP error');
      const res = payload?.result;
      if (res?.content?.length) {
        const item = res.content[0];
        if (item.type === 'json') return item.json;
        if (item.type === 'text') {
          try { return JSON.parse(item.text); } catch { return item.text; }
        }
      }
      return res ?? payload;
    };

    // Parse Server-Sent Events until a JSON-RPC envelope (`result` or `error`) arrives.
    const readSseAsJson = async (resp: Response) => {
      const body = resp.body;
      if (!body) throw new Error('Empty SSE body');

      const reader = body.getReader();
      const decoder = new TextDecoder();

      // Accumulate partial chunk data across reads
      let chunkBuf = '';
      // Per-event accumulators
      let dataLines: string[] = [];

      const processEvent = (): any | null => {
        if (dataLines.length === 0) return null;
        const data = dataLines.join('\n'); // SSE spec: join multiple data lines with \n
        dataLines = [];
        try {
          const obj = JSON.parse(data);
          if (obj?.result || obj?.error) {
            return obj; // JSON-RPC envelope
          }
        } catch {
          // Not JSON or partial — ignore and continue
        }
        return null;
      };

      while (true) {
        const { value, done } = await reader.read();
        if (done) {
          // Flush any pending event at EOF
          const maybe = processEvent();
          if (maybe) return maybe;
          break;
        }

        chunkBuf += decoder.decode(value, { stream: true });

        // Split into lines; keep last partial line in buffer
        const lines = chunkBuf.split('\n');
        chunkBuf = lines.pop() ?? '';

        for (const line of lines) {
          const trimmed = line.replace(/\r$/, '');

          // Blank line = end of one SSE event
          if (trimmed === '') {
            const maybe = processEvent();
            if (maybe) return maybe;
            continue;
          }

          // Comments start with ":" — ignore
          if (trimmed.startsWith(':')) continue;

          // We only need `data:` lines; ignore `event:`, `id:`, etc.
          if (trimmed.startsWith('data:')) {
            dataLines.push(trimmed.slice(5).trimStart());
          }
        }
      }

      throw new Error('SSE ended without a JSON-RPC result');
    };

    const timeRangeToMinutes = (range: string) => {
      const map: { [key: string]: number } = {
        '1h': 60,
        '6h': 360, 
        '24h': 1440,
        '7d': 10080,
        '30d': 43200
      };
      return map[range] || 1440;
    };

    // --- request ---
    const resp = await fetch(`${PUBLIC_BASE_URL}/mcp/rpc`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // Must accept both; server may choose JSON or SSE
        'Accept': 'application/json, text/event-stream',
      },
      credentials: 'include',
      body: JSON.stringify({
        jsonrpc: '2.0',
        id: (crypto as any).randomUUID ? (crypto as any).randomUUID() : Date.now().toString(),
        method: 'tools/call',
        params: {
          name: toolName,      // e.g., "get_dashboard_data"
          arguments: params,   // e.g., { time_range: '7d' }
          stream: false,       // ask for non-streaming; still handle SSE just in case
        },
      }),
    });

    if (resp.status === 401 || resp.status === 403) {
      const w = window as any;
      if (w.isReauthenticating) {
        throw new Error('Already reauthenticating');
      }
      w.isReauthenticating = true;
    
      try {
        await fetch(`${PUBLIC_BASE_URL}/api/auth/logout`, {
          method: 'POST',
          credentials: 'include',
        });
      } catch {}
    
      // Re-init OAuth (use replace to avoid back-nav loop)
      window.location.replace(`${PUBLIC_BASE_URL}/auth/google`);
      throw new Error('Session expired - reauth');
    }

    if (!resp.ok) {
      const text = await resp.text().catch(() => '');
      throw new Error(`HTTP ${resp.status}${text ? `: ${text}` : ''}`);
    }
    

    const ct = (resp.headers.get('content-type') || '').toLowerCase();

    // Handle SSE vs JSON
    if (ct.startsWith('text/event-stream')) {
      const payload = await readSseAsJson(resp);
      const result = unwrapMcp(payload);
      
      // Simple rate limit logging
      if (result?.rate_limited) {
        console.log(`Rate limited, showing cached data`);
      }
      
      return result;
    } else {
      const payload = await resp.json();
      const result = unwrapMcp(payload);
      
      // Simple rate limit logging  
      if (result?.rate_limited) {
        console.log(`Rate limited, showing cached data`);
      }
      
      return result;
    }
  }, []);

  return { makeRequest };
};

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  });
};

const getHealthScoreColor = (score: number) => {
  if (score >= 80) return 'hsl(142 76% 36%)'; // green
  if (score >= 60) return 'hsl(45 93% 47%)'; // yellow
  return 'hsl(0 84% 60%)'; // red
};

const getSentimentColor = (score?: number) => {
  if (!score) return 'hsl(var(--muted-foreground))';
  if (score >= 0.6) return 'hsl(142 76% 36%)';
  if (score >= 0.4) return 'hsl(45 93% 47%)';
  return 'hsl(0 84% 60%)';
};

const getChurnRiskBadge = (risk: string) => {
  const colors = {
    low: 'bg-green-100 text-green-800',
    medium: 'bg-yellow-100 text-yellow-800',
    high: 'bg-red-100 text-red-800'
  };
  return colors[risk as keyof typeof colors] || colors.low;
};

function RadarPanel({ data, realtimeActivity = [], sseConnected }: { 
  data: DashboardData, 
  realtimeActivity?: Array<{
    id?: string;
    type: string;
    title: string;
    timestamp: string;
    source: string;
  }>,
  sseConnected: boolean
}) {
  const [now, setNow] = React.useState(Date.now());
  const [activityIndex, setActivityIndex] = React.useState(0);
  
  React.useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  // Rotate activity messages every 12 seconds
  React.useEffect(() => {
    const activityId = setInterval(() => {
      setActivityIndex(prev => (prev + 1) % 4);
    }, 12000);
    return () => clearInterval(activityId);
  }, []);

  const systemHealth = (data as any).insights?.filter((insight: any) => insight.type === 'trend')?.map((insight: any) => ({
    topic: insight.title || insight.keywords?.join(' ') || 'Unknown',
    status: insight.severity === 'high' ? '🔴' : insight.severity === 'medium' ? '🟡' : '🟢',
    count: insight.evidence_counts?.total || 0,
    severity: insight.severity || 'low'
  })) || [];

  const lastScan = new Date(data.generated_at || Date.now()).getTime();
  const secsSince = Math.max(0, Math.floor((now - lastScan) / 1000));
  const nextPulse = Math.max(0, 15 * 60 - secsSince);
  const nextInsight = Math.max(0, 45 * 60 - secsSince);

  // Window
  const tenSecondsAgoISO = new Date(now - 10 * 1000).toISOString();
  const recentsT = (data.recent_tickets || []).filter(t => t.created_at >= tenSecondsAgoISO);
  const recentsS = (data.recent_slack_messages || []).filter(m => m.created_at >= tenSecondsAgoISO);

  // Helpers
  const toTime = (iso: string) => new Date(iso).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  const textOf = (t: any) => (t.subject || t.text || '').toLowerCase();

  // Heuristics for signal cards
  const featureWords = ['feature', 'request', 'export', 'integration', 'add', 'support'];
  const loginWords = ['login', 'log in', 'signin', 'sign in', 'auth', 'password'];
  const payWords = ['payment', 'checkout', 'billing', 'invoice', 'card', 'stripe'];
  const mobileWords = ['mobile', 'ios', 'android', 'app'];
  const apiWords = ['api', 'endpoint', 'rate limit', 'timeout', 'server'];

  const allItems = [
    ...recentsT.map(t => ({ kind: 'ticket' as const, at: t.created_at, text: textOf(t), sentiment: t.sentiment_score ?? 0 })),
    ...recentsS.map(m => ({ kind: 'slack' as const, at: m.created_at, text: textOf(m), sentiment: m.sentiment_score ?? 0 })),
  ].sort((a, b) => (a.at > b.at ? -1 : 1));

  // Buckets
  const countMatches = (words: string[]) => allItems.filter(i => words.some(w => i.text.includes(w))).length;
  const countNeg = allItems.filter(i => (i.sentiment ?? 0) < 0).length;
  const countPos = allItems.filter(i => (i.sentiment ?? 0) > 0.2).length;

  // Build recent signal cards (max 5)
  const signals: Array<{ icon: string; title: string; subtitle?: string; at?: string }> = [];

  // Feature request spike (very simple: >=3 mentions)
  const featMentions = countMatches(featureWords);
  if (featMentions >= 3) {
    const latest = allItems.find(i => featureWords.some(w => i.text.includes(w)));
    signals.push({
      icon: '💡',
      title: `${toTime(latest?.at || new Date().toISOString())} — Feature request spike`,
      subtitle: `"Export" or related — ${featMentions} mentions`,
    });
  }

  // Satisfaction uptick (more positive than negative in window)
  if (countPos >= countNeg + 2) {
    const latestPos = allItems.find(i => (i.sentiment ?? 0) > 0.2);
    signals.push({
      icon: '😊',
      title: `${toTime(latestPos?.at || new Date().toISOString())} — Satisfaction uptick`,
      subtitle: `Positive feedback outweighs negatives (+${(countPos - countNeg)})`,
    });
  }

  // Volume quiet (few total signals)
  if (allItems.length <= 3) {
    signals.push({
      icon: '🔇',
      title: `${toTime(new Date().toISOString())} — Volume quiet`,
      subtitle: `Signals ${allItems.length} in last 2h (below usual)`,
    });
  }

  // Fallback if none detected
  if (signals.length === 0) {
    signals.push({
      icon: '🔵',
      title: 'Volume quiet',
      subtitle: 'No noteworthy signals in last 2h',
    });
  }

  // Health Monitors (keyword counts)
  const mon = (words: string[]) => {
    const n = countMatches(words);
    return n === 0 ? { dot: '🟢', label: 'Clear' } : { dot: n >= 3 ? '🟠' : '🟡', label: `${n} mention${n > 1 ? 's' : ''}` };
  };
  const login = mon(loginWords);
  const payment = mon(payWords);
  const mobile = mon(mobileWords);
  const api = mon(apiWords);

  // Today counters
  const todayIso = new Date().toISOString().slice(0, 10);
  const todaySignals =
    (data.recent_tickets || []).filter(t => (t.created_at || '').startsWith(todayIso)).length +
    (data.recent_slack_messages || []).filter(m => (m.created_at || '').startsWith(todayIso)).length;

  // Rotating activity messages
  const activityMessages = [
    "Scanning new messages...",
    "Analyzing customer feedback...",
    "Analyzing customer feedback...",
    "Monitoring customer signals..."
  ];

  return (
    <Card className="bg-gradient-to-br from-slate-50 via-white to-slate-50/50 border-2 border-slate-200/60 shadow-lg h-full flex flex-col">
      <CardHeader className="bg-gradient-to-r from-slate-100/50 to-transparent flex-shrink-0">
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-blue-600" />
            <span className="text-xl font-semibold text-slate-900">Customer Radar</span>
            <div className="flex items-center gap-2 ml-4">
              <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse shadow-lg shadow-green-200" />
              <span className="text-sm font-semibold text-green-700">Live</span>
            </div>
          </div>
          <Badge 
            variant={data.overview.critical_insights > 0 ? 'destructive' : 'default'}
            className={data.overview.critical_insights > 0 ? 'animate-pulse bg-red-600 text-white font-bold text-sm px-3 py-1 shadow-lg' : ''}
          >
            {data.overview.critical_insights > 0 ? '🚨 Attention Required' : 'All Clear'}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 flex-1">
        <div className="text-sm text-slate-600 flex items-center justify-between">
          <span className="font-medium">Last scan: {secsSince}s ago</span>
          <span className="font-medium">Monitoring {data.overview.total_customers} customers across 2 channels</span>
        </div>

        {/* Activity Indicators */}
        <div className="border rounded p-3 bg-slate-50/30">
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span className="font-medium text-slate-900">Live monitoring active</span>
            </div>
            <span className="text-slate-600 font-medium">
              Last scan: {secsSince}s ago
            </span>
          </div>
          
          {/* Dynamic activity messages */}
          <div className="mt-2 text-sm text-slate-600 space-y-1">
            <div className="flex items-center space-x-2">
              <RefreshCw className="h-3 w-3 animate-spin text-blue-600" />
              <span className="font-medium">{activityMessages[activityIndex]}</span>
            </div>
            <div className="flex items-center space-x-2">
              <Zap className="h-3 w-3 text-blue-600" />
              <span className="font-medium">Last scan: {Math.floor(secsSince / 10)}s ago</span>
            </div>
          </div>
        </div>

        {/* Middle — Recent Signals list with real-time updates */}
        <div>
          <div className="text-lg font-semibold text-slate-900 mb-2">Recent Activity</div>
          <div className="text-sm text-slate-600 mb-2">
            Real-time updates from SSE • Last: {realtimeActivity.length > 0 ? toTime(realtimeActivity[0].timestamp) : 'None'}
          </div>
          <div className="space-y-2">
            {/* Real-time activity from SSE */}
            {realtimeActivity.length > 0 ? (
              realtimeActivity.slice(0, 3).map((activity, index) => (
                <div key={activity.id || `activity-${index}`} className="border rounded p-3 text-sm bg-blue-50/50 border-blue-200">
                  <div className="font-semibold text-slate-900 flex items-center gap-1">
                    <span className="animate-pulse">🔵</span>
                    {toTime(activity.timestamp)} — {activity.type === 'trend_detected' ? '📈 Trend detected' : 
                     activity.type === 'new_message' ? '💬 New message' : '🎫 New ticket'}
                  </div>
                  <div className="text-slate-600 font-medium">{activity.title.slice(0, 50)}...</div>
                  <div className="text-xs text-blue-600 font-medium">Source: {activity.source}</div>
                </div>
              ))
            ) : (
              /* Fallback to database activity */
              <>
                {data.recent_tickets && data.recent_tickets.length > 0 && (
                  <div className="border rounded p-3 text-sm">
                    <div className="font-semibold text-slate-900">🎫 {toTime(data.recent_tickets[0].created_at)} — New ticket</div>
                    <div className="text-slate-600 font-medium">{data.recent_tickets[0].subject?.slice(0, 50)}...</div>
                  </div>
                )}

                {data.recent_slack_messages && data.recent_slack_messages.length > 0 && (
                  <div className="border rounded p-3 text-sm">
                    <div className="font-semibold text-slate-900">💬 {toTime(data.recent_slack_messages[0].created_at)} — New message</div>
                    <div className="text-slate-600 font-medium">{data.recent_slack_messages[0].text?.slice(0, 50)}...</div>
                  </div>
                )}

                {(!data.recent_tickets || data.recent_tickets.length === 0) && 
                 (!data.recent_slack_messages || data.recent_slack_messages.length === 0) && (
                  <div className="text-slate-600 font-medium text-center py-2">No recent activity</div>
                )}
              </>
            )}
          </div>
        </div>

        {/* Combined System Status */}
        <div>
          <div className="text-lg font-semibold text-slate-900 mb-3">System Status</div>
          <div className="space-y-3">
            {/* Overall health indicator */}
            {systemHealth.length > 0 ? (
              <div className="flex items-center justify-between p-3 bg-orange-50 rounded border-l-4 border-orange-400">
                <span className="text-sm font-medium text-slate-900">Overall health</span>
                <span className="font-semibold text-orange-700">{systemHealth.length} issue{systemHealth.length !== 1 ? 's' : ''} detected</span>
              </div>
            ) : (
              <div className="flex items-center justify-between p-3 bg-green-50 rounded border-l-4 border-green-400">
                <span className="text-sm font-medium text-slate-900 flex items-center gap-2">
                  <CheckCircle className="h-4 w-4" />
                  Overall health
                </span>
                <span className="font-semibold text-green-700">All systems clear</span>
              </div>
            )}
            
            {/* Intelligence metrics */}
            <div className="grid grid-cols-2 gap-2">
              <div className="text-center p-3 bg-blue-50 rounded">
                <div className="text-xl font-bold text-blue-800">{todaySignals}</div>
                <div className="text-sm font-medium text-blue-600">Signals</div>
              </div>
              <div className="text-center p-3 bg-red-50 rounded">
                <div className="text-xl font-bold text-red-800">{data.overview.critical_insights}</div>
                <div className="text-sm font-medium text-red-600">Issues</div>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
// Main App Component

const App: React.FC = () => {
  const [showBetaApplication, setShowBetaApplication] = useState(false);

  // Beta form is completely public - no auth needed
  if (showBetaApplication) {
    return (
      <>
        <BetaApplicationForm
          onComplete={() => setShowBetaApplication(false)}
          onCancel={() => setShowBetaApplication(false)}
        />
        <Toaster />
      </>
    );
  }

  // Wrap authenticated section only
  return (
    <AuthProvider>
      <Routes>
        <Route 
          path="/" 
          element={
            <AuthenticatedApp onBetaAccess={() => setShowBetaApplication(true)} />
          } 
        />
        <Route path="/login" element={<Auth />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
};

// New component - handles all authenticated logic
const AuthenticatedApp: React.FC<{ onBetaAccess: () => void }> = ({ onBetaAccess }) => {
  const { isAuthenticated, isLoading, user, account, login, logout } = useAuth();
  const [oauthSuccess, setOauthSuccess] = useState(false);
  // State
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState('7d');
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [isGenerating, setIsGenerating] = useState(false);
  const [lastGeneratedAt, setLastGeneratedAt] = useState<string | null>(
    localStorage.getItem('last_insights_generated_at')
  ); //dummy commit

  // Trending Topics State
  const [trendingTopics, setTrendingTopics] = useState<TrendingTopic[]>([]);
  const [selectedTopic, setSelectedTopic] = useState<TrendingTopic | null>(null);
  const [activeAlerts, setActiveAlerts] = useState<TrendingTopic[]>([]);
  const [dismissedAlerts, setDismissedAlerts] = useState<Set<string>>(new Set());
  
  // SSE connection state
  const [sseConnected, setSseConnected] = useState(false);
  const [eventSource, setEventSource] = useState<EventSource | null>(null);

  const [oauthChecked, setOauthChecked] = useState(false);

  const [realtimeActivity, setRealtimeActivity] = useState<Array<{
    id?: string;
    type: string;
    title: string;
    timestamp: string;
    source: string;
  }>>([]);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isHistoricalModalOpen, setIsHistoricalModalOpen] = useState(false);

  // OAuth State
  const [oauthStatus, setOauthStatus] = useState({ zendesk_connected: false, slack_connected: false });
  const [oauthMessage, setOauthMessage] = useState('');
  const [showOAuthDialog, setShowOAuthDialog] = useState(false);
  
  // Integration metadata for disconnect operations
  const [slackInfo, setSlackInfo] = useState<any>(null);
  const [zendeskInfo, setZendeskInfo] = useState<ZendeskInfo | null>(null);

  // Add these state declarations at the top with other useState hooks
  const [slackBusy, setSlackBusy] = useState(false);
  const [zendeskBusy, setZendeskBusy] = useState(false);
  const [showZendeskWizard, setShowZendeskWizard] = useState(false);
  const hasLoadedRef = useRef(false);
  const [lastTrendsFetchTime, setLastTrendsFetchTime] = useState<number>(0);

  // Hooks
  const { makeRequest } = useMcpApi();
  // Functions
  // Helper function to calculate trend severity
  const calculateSeverity = (topic: any): string => {
    const messageRate = topic.messages_per_minute || 0;
    const sentiment = topic.avg_sentiment || 0;
    const count = topic.count_in_window || 0;
    
    // Critical: High volume OR significant count
    if (messageRate > 1.5 || count > 5) {
      return 'critical';
    }
    // High: Moderate activity
    if (messageRate > 0.5 || count > 2) {
      return 'high';
    }
    // Medium: Some activity with negative sentiment
    if (messageRate > 0.2 && sentiment < 0) {
      return 'medium';
    }
    // Low: Basic activity
    return 'low';
  };
  
  // Trending Topics Functions
  const loadTrendingTopics = async (useCache = true) => {
    // Don't refetch if less than 30 seconds ago
    if (useCache && lastTrendsFetchTime && Date.now() - lastTrendsFetchTime < 30000) {
      return;
    }
    
    try {
      const data = await makeRequest('get_active_trends_with_insights', {});
      
      if (data.trends) {
        const transformedTopics = data.trends.map((topic: any) => ({
          ...topic,
          severity: calculateSeverity(topic),
          timestamp: topic.created_at || topic.window_start,
          display_timestamp: new Date().toISOString()
        }));
        
        // Fetch evidence for all topics in parallel, then update state once
        const topicsWithEvidence = await Promise.all(
          transformedTopics.map(async (topic) => {
            if (topic.evidence_ids) {
              try {
                const evidenceData = await fetchEvidenceDetails(topic.evidence_ids);
                return { ...topic, evidence: evidenceData };
              } catch (error) {
                console.error('Error fetching evidence for topic');
                return topic; // Return topic without evidence if fetch fails
              }
            }
            return topic;
          })
        );
        
        // Split into two different time filters:
        const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000);  // Active alerts
        const twentyFourHoursAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);  // Recent trends

        // 🚨 Active Alerts (1-hour filter - urgent/actionable)
        const activeAlerts = topicsWithEvidence.filter((topic: any) => {
          const trendTime = new Date(topic.timestamp);
          return trendTime > oneHourAgo && 
                 ['critical', 'high'].includes(topic.severity) && 
                 !dismissedAlerts.has(topic.topic_id);
        });

        // 📈 Recent Trends (24-hour filter - all trends for context)
        const recentTrends = topicsWithEvidence.filter((topic: any) => {
          const trendTime = new Date(topic.timestamp);
          return trendTime > twentyFourHoursAgo;  // Show all trends from last 24h
        });

        setActiveAlerts(activeAlerts);  // ✅ Only urgent recent alerts
        setTrendingTopics(recentTrends); // ✅ All recent trends for analysis
      }
      
      setLastTrendsFetchTime(Date.now());
      
    } catch (err) {
      console.error('Error loading trending topics:', err);
      setTrendingTopics([]);
      setActiveAlerts([]);
    }
  };

  // Helper functions
  const zendeskTicketUrl = (sub: string | undefined, id: string | number | undefined) =>
    sub && id ? `https://${sub}.zendesk.com/agent/tickets/${id}` : undefined;

  const slackMessageUrl = (
    teamId: string | undefined,
    channelId: string | undefined,
    ts?: string,
    threadTs?: string
  ) => {
    if (!teamId || !channelId) return undefined;
    if (!ts) return `https://app.slack.com/client/${teamId}/${channelId}`;
    const p = 'p' + String(ts).replace('.', '');
    return threadTs
      ? `https://app.slack.com/client/${teamId}/${channelId}/thread/${channelId}-${threadTs.replace('.', '')}/${p}`
      : `https://app.slack.com/client/${teamId}/${channelId}/${p}`;
  };

  // Function to fetch evidence details and link to original sources
  const fetchEvidenceDetails = async (evidenceIds: any) => {
    const evidence: Array<{
      text: string;
      source: string;
      timestamp: string;
      type: 'ticket' | 'slack';
      link: string;
    }> = [];
  
    try {
      const evidenceData = await makeRequest('get_evidence_details', { evidence_ids: evidenceIds });
  
      if (evidenceData) {
        const zdSub = zendeskInfo?.subdomain;
        const teamId = slackInfo?.workspace_id;
  
        // Only add tickets if we can generate links
        for (const ticket of evidenceData.tickets || []) {
          const link = zendeskTicketUrl(zdSub, ticket.zendesk_ticket_id);
          if (link) { // Only add if link can be generated
            evidence.push({
              text: ticket.subject,
              source: `Zendesk #${ticket.zendesk_ticket_id}`,
              timestamp: ticket.created_at,
              type: 'ticket',
              link
            });
          }
        }
  
        // Only add messages if we can generate links
        for (const message of evidenceData.slack_messages || []) {
          const link = slackMessageUrl(teamId, message.slack_channel_id, message.slack_message_id, message.thread_ts);
          if (link) {
            evidence.push({
              text: message.text,
              source: `Slack #${message.slack_channel_id}`,
              timestamp: message.created_at,
              type: 'slack',
              link
            });
          }
        }
      }
  
      return evidence;
    } catch (error) {
      console.error('Error fetching evidence details:', error);
      return [];
    }
  };

  const dismissAlert = (alertId: string) => {
    const newDismissed = new Set(dismissedAlerts);
    newDismissed.add(alertId);
    setDismissedAlerts(newDismissed);
    setActiveAlerts(alerts => alerts.filter(alert => alert.topic_id !== alertId));
  };

  const handleTopicClick = async (topic: TrendingTopic) => {
    setSelectedTopic(topic);
    
    // Fetch evidence details if not already loaded
    if (topic.evidence_ids && !topic.evidence?.details) {
      try {
        const evidenceDetails = await fetchEvidenceDetails(topic.evidence_ids);
        setSelectedTopic({
          ...topic,
          evidence: {
            ...topic.evidence,
            details: evidenceDetails
          }
        });
      } catch (error) {
        console.error('Error fetching evidence details:', error);
      }
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'hsl(var(--alert-critical))';
      case 'high': return 'hsl(var(--alert-high))';
      case 'medium': return 'hsl(var(--alert-medium))';
      case 'low': return 'hsl(var(--neutral))';
      default: return 'hsl(var(--neutral))';
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical': return '🔴';
      case 'high': return '🟠';
      case 'medium': return '🟡';
      case 'low': return '🟢';
      default: return '🔵';
    }
  };

  const handleHistoricalModalClose = () => {
    setIsHistoricalModalOpen(false);
  };

  // Historical Trends Modal Component
  const HistoricalTrendsModal = ({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) => {
    const [selectedTimeRange, setSelectedTimeRange] = useState('7d');
    const [customDateRange, setCustomDateRange] = useState({ start: '', end: '' });
    const [historicalTrends, setHistoricalTrends] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [historicalLoading, setHistoricalLoading] = useState(false);
    const [historicalTimeRange, setHistoricalTimeRange] = useState('24h');
    const [selectedHistoricalTopic, setSelectedHistoricalTopic] = useState<any>(null);
  
    const timeRangeOptions = [
      { value: '24h', label: 'Last 24 Hours' },
      { value: '7d', label: 'Last 7 Days' },
      { value: '30d', label: 'Last 30 Days' },
      { value: 'custom', label: 'Custom Range' }
    ];
  
    const timeRangeToMinutes = (range: string) => {
      const map: { [key: string]: number } = {
        '1h': 60,
        '6h': 360, 
        '24h': 1440,
        '7d': 10080,
        '30d': 43200
      };
      return map[range] || 1440;
    };
  
    const loadHistoricalTrends = async (timeRange: string) => {
      try {
        setHistoricalLoading(true);
        
        // Use the new historical endpoint instead of detect_trending_topics
        const data = await makeRequest('get_historical_trends', {
          time_window_minutes: timeRangeToMinutes(timeRange)
        });
        
        if (data.trends && data.trends.length > 0) {
          const transformedTrends = data.trends.map((trend: any) => ({
            ...trend,
            severity: calculateSeverity(trend),
            timestamp: trend.created_at || trend.window_start || new Date().toISOString(),
            display_timestamp: new Date().toISOString()
          }));
          
          setHistoricalTrends(transformedTrends);
        } else {
          setHistoricalTrends([]);
        }
      } catch (error) {
        console.error('Error loading historical trends:', error);
        setHistoricalTrends([]);
      } finally {
        setHistoricalLoading(false);
      }
    };
  
    const fetchEvidence = useCallback(async (topic: any) => {
      if (!topic || !topic.evidence_ids) return;
      
      try {
        const evidenceData = await makeRequest('get_evidence_details', { 
          evidence_ids: topic.evidence_ids 
        });
        
        const evidence: Array<{
          text: string;
          source: string;
          timestamp: string;
          type: 'ticket' | 'slack';
          link: string;
        }> = [];

        const zdSub = zendeskInfo?.subdomain;
        const teamId = slackInfo?.workspace_id;
        
        for (const ticket of evidenceData.tickets || []) {
          const link = zendeskTicketUrl(zdSub, ticket.zendesk_ticket_id);
          if (link) {
            evidence.push({
              text: ticket.subject,
              source: `Zendesk #${ticket.zendesk_ticket_id}`,
              timestamp: ticket.created_at,
              type: 'ticket',
              link
            });
          }
        }
        
        for (const message of evidenceData.slack_messages || []) {
          const link = slackMessageUrl(
            teamId,
            message.slack_channel_id,
            message.slack_message_id,   // Slack ts
            message.thread_ts
          );
          if (link) {
            evidence.push({
              text: message.text,
              source: `Slack #${message.slack_channel_id}`,
              timestamp: message.created_at,
              type: 'slack',
              link
            });
          }
        }
        
        setSelectedHistoricalTopic(prev => ({
          ...prev,
          evidence: { details: evidence }
        }));
      } catch (error) {
        console.error('Error fetching evidence for historical topic:', error);
      }
    }, [makeRequest, zendeskInfo, slackInfo]);
    
    useEffect(() => {
      if (selectedHistoricalTopic) {
        fetchEvidence(selectedHistoricalTopic);
      }
    }, [selectedHistoricalTopic?.topic_id, fetchEvidence]);

    const handleClose = () => {
      setSelectedHistoricalTopic(null);
      onClose();
    };
  
    return (
      <Dialog open={isOpen} onOpenChange={handleClose}>
        <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Historical Trends Analysis</DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <Select value={historicalTimeRange} onValueChange={setHistoricalTimeRange}>
                  <SelectTrigger className="w-48">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1h">Last 1 hour</SelectItem>
                    <SelectItem value="6h">Last 6 hours</SelectItem>
                    <SelectItem value="24h">Last 24 hours</SelectItem>
                    <SelectItem value="7d">Last 7 days</SelectItem>
                    <SelectItem value="30d">Last 30 days</SelectItem>
                  </SelectContent>
                </Select>
                <Button 
                  onClick={() => loadHistoricalTrends(historicalTimeRange)}
                  disabled={historicalLoading}
                >
                  {historicalLoading ? 'Loading...' : 'Load Trends'}
                </Button>
              </div>
            </div>
  
            {/* Display historical trends */}
            {historicalTrends.length > 0 ? (
              <div className="space-y-4">
                <h3 className="text-lg font-semibold">Historical Trends ({historicalTrends.length})</h3>
                <div className="grid gap-4">
                  {historicalTrends.map((trend: any) => (
                    <Card 
                      key={trend.topic_id} 
                      className="cursor-pointer hover:bg-muted/50 transition-colors"
                      onClick={() => setSelectedHistoricalTopic(trend)}
                    >
                      <CardContent className="p-6">
                        <div className="flex items-center justify-between">
                          <div className="flex-1 min-w-0">
                            <h4 className="font-medium flex items-center gap-1 mb-1">
                              <span>{getSeverityIcon(trend.severity || 'low')}</span>
                              <span className="truncate">
                                {trend.name || trend.title || trend.keywords?.slice(0, 3).join(' • ') || 'Unnamed Topic'}
                              </span>
                            </h4>
                            <p className="text-sm text-muted-foreground">
                              {trend.count_in_window} messages • {formatRelativeTime(trend.timestamp)}
                            </p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                {historicalLoading ? 'Loading trends...' : 'No trends found for the selected time period'}
              </div>
            )}
  
            {/* Historical Topic Detail Modal */}
            {selectedHistoricalTopic && (
              <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                <div className="fixed inset-0 bg-black/20 backdrop-blur-sm" onClick={() => setSelectedHistoricalTopic(null)} />
                <Card className="relative z-10 w-full max-w-6xl max-h-[98vh] overflow-hidden flex flex-col">
                  <CardHeader className="border-b bg-muted/30 flex-shrink-0">
                    <div className="flex items-center justify-between">
                      <CardTitle className="flex items-center gap-2 text-lg">
                        <span>{getSeverityIcon(selectedHistoricalTopic.severity)}</span>
                        <span className="truncate">
                          {selectedHistoricalTopic.name || selectedHistoricalTopic.title || selectedHistoricalTopic.keywords?.slice(0, 3).join(' • ')}
                        </span>
                        <span className="text-sm font-normal text-muted-foreground">
                          ({selectedHistoricalTopic.count_in_window} messages)
                        </span>
                      </CardTitle>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setSelectedHistoricalTopic(null)}
                        className="h-8 w-8 p-0"
                      >
                        ✕
                      </Button>
                    </div>
                  </CardHeader>
                  
                  <div className="flex-1 overflow-y-auto">
                    <CardContent className="p-6 space-y-6">
                      {/* Topic Details - Simplified */}
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-muted/20 rounded-lg flex-shrink-0">
                        <div>
                          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Keywords</span>
                          <p className="text-sm font-medium mt-1">{selectedHistoricalTopic.keywords?.join(' • ')}</p>
                        </div>
                        <div>
                          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Messages</span>
                          <p className="text-sm font-medium mt-1">{selectedHistoricalTopic.count_in_window}</p>
                        </div>
                        <div>
                          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Sentiment</span>
                          <p className="text-sm font-medium mt-1">{selectedHistoricalTopic.avg_sentiment > 0 ? '😊 Positive' : '😞 Negative'}</p>
                        </div>
                        <div>
                          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Detected</span>
                          <p className="text-sm font-medium mt-1">{formatRelativeTime(selectedHistoricalTopic.timestamp)}</p>
                        </div>
                      </div>

                      {/* Evidence Section - Enhanced */}
                      {selectedHistoricalTopic.evidence_ids && (
                        <div className="space-y-4 flex-1">
                          <div className="flex items-center justify-between flex-shrink-0">
                            <h4 className="text-lg font-semibold">Evidence</h4>
                            <span className="text-sm text-muted-foreground">
                              {selectedHistoricalTopic.evidence?.details?.length || 0} items
                            </span>
                          </div>
                          <div className="space-y-3">
                            {selectedHistoricalTopic.evidence?.details?.map((evidence: any, index: number) => (
                              <div key={index} className="border rounded-lg p-4 bg-white shadow-sm hover:shadow-md transition-shadow">
                                <div className="flex items-start justify-between mb-3">
                                  <span className="text-sm font-medium text-muted-foreground bg-muted px-2 py-1 rounded">
                                    {evidence.source}
                                  </span>
                                  <span className="text-sm text-muted-foreground">
                                    {formatRelativeTime(evidence.timestamp)}
                                  </span>
                                </div>
                                <p className="text-base leading-relaxed mb-3">{evidence.text}</p>
                                {evidence.link && (
                                  <a 
                                    href={evidence.link} 
                                    target="_blank" 
                                    rel="noopener noreferrer"
                                    className="text-sm text-blue-600 hover:text-blue-800 hover:underline inline-flex items-center gap-1 transition-colors"
                                  >
                                    View Original <ExternalLink className="w-3 h-3" />
                                  </a>
                                )}
                              </div>
                            )) || (
                              <div className="text-center py-8 text-muted-foreground">
                                <div className="animate-pulse">Loading evidence...</div>
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </div>
                </Card>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    );
  };

  // Trending Topics Panel Component
  const TrendIntelligencePanel = () => {
    return (
      <div className="space-y-4">
        {/* Alert Banner - Only show for critical/high severity topics */}
        {activeAlerts.length > 0 && (  // ← Use activeAlerts directly
          <Card className="border-2 animate-pulse" style={{ borderColor: getSeverityColor(activeAlerts[0].severity) }}>
            <CardContent className="p-4">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-semibold text-sm mb-1">
                    🚨 {activeAlerts[0].title}  {/* ← Use activeAlerts directly */}
                  </h3>
                  <p className="text-xs text-muted-foreground mb-2">
                    {activeAlerts[0].count_in_window} reports in {activeAlerts[0].window_duration} • {activeAlerts[0].severity} • {formatRelativeTime(activeAlerts[0].timestamp)}
                  </p>
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => dismissAlert(activeAlerts[0].topic_id)}
                  className="h-6 w-6 p-0"
                >
                  ✕
                </Button>
              </div>
              <div className="flex gap-2">
                <Button 
                  size="sm" 
                  onClick={() => handleTopicClick(activeAlerts[0])}
                  className="text-xs"
                >
                  View Evidence
                </Button>
                <Button 
                  size="sm" 
                  variant="outline"
                  onClick={() => dismissAlert(activeAlerts[0].topic_id)}
                  className="text-xs"
                >
                  Dismiss
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Trending Topics List */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                📈 Recent Trends (24h)
              </CardTitle>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsHistoricalModalOpen(true)}
                className="text-xs"
              >
                View All Trends
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {trendingTopics.length === 0 ? (
              <div className="text-center py-6 text-muted-foreground">
                <TrendingUp className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">All systems stable</p>
                <p className="text-xs">No trending issues detected</p>
              </div>
            ) : (
              trendingTopics.map((topic) => (
                <div
                  key={topic.topic_id}
                  className="border rounded-lg p-3 cursor-pointer hover:bg-muted/50 transition-colors animate-fade-in"
                  onClick={() => handleTopicClick(topic)}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1 min-w-0">
                      <h4 className="text-sm font-medium flex items-center gap-1 mb-1">
                        <span>{getSeverityIcon(topic.severity)}</span>
                        <span className="truncate">{topic.title || topic.keywords.slice(0, 3).join(', ')}</span>
                      </h4>
                      <p className="text-xs text-muted-foreground">
                        {topic.keywords.slice(0, 3).join(', ')} • {formatRelativeTime(topic.timestamp)}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>{topic.count_in_window} messages</span>
                    <span>{topic.avg_sentiment > 0 ? '😊' : '😞'}</span>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>


      </div>
    );
  };

  const RateLimitMonitoringPanel = () => {
    const [analytics, setAnalytics] = useState<any>(null);
    const [loading, setLoading] = useState(false);
  
    const loadAnalytics = async () => {
      setLoading(true);
      const data = await loadRateLimitAnalytics();
      setAnalytics(data);
      setLoading(false);
    };
  
    useEffect(() => {
      loadAnalytics();
      const interval = setInterval(loadAnalytics, 60000);
      return () => clearInterval(interval);
    }, []);
  
    if (loading) {
      return <div className="p-4">Loading rate limit analytics...</div>;
    }
  
    if (!analytics) {
      return <div className="p-4 text-red-600">Failed to load analytics</div>;
    }
  
    return (
      <Card className="w-full">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Rate Limit Monitoring
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {analytics.analytics?.success_rate || 0}%
              </div>
              <div className="text-sm text-muted-foreground">Success Rate</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-orange-600">
                {analytics.analytics?.rate_limit_hit_rate || 0}%
              </div>
              <div className="text-sm text-muted-foreground">Rate Limit Hits</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                {analytics.analytics?.current_rate_per_minute || 0}
              </div>
              <div className="text-sm text-muted-foreground">Requests/Min</div>
            </div>
          </div>
          
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm">Rate Limiter Status:</span>
              <Badge variant="default">
                Active ({analytics.rate_limiter_state?.requests_per_minute || 0} req/min)
              </Badge>
            </div>
          </div>
  
          {analytics.analytics?.alerts && analytics.analytics.alerts.length > 0 && (
            <div className="space-y-2">
              <h4 className="font-medium">Active Alerts</h4>
              {analytics.analytics.alerts.map((alert: any, index: number) => (
                <Alert key={index} variant={alert.severity === 'critical' ? 'destructive' : 'default'}>
                  <AlertTriangle className="h-4 w-4" />
                  <AlertTitle>{alert.type}</AlertTitle>
                  <AlertDescription>{alert.message}</AlertDescription>
                </Alert>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    );
  };

  // Topic Detail Modal Component
  const TopicDetailModal = () => {
    if (!selectedTopic) return null;

    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center">
        <div className="fixed inset-0 bg-black/20 backdrop-blur-sm" onClick={() => setSelectedTopic(null)} />
        <Card className="relative z-10 w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <span>{getSeverityIcon(selectedTopic.severity)}</span>
                {selectedTopic.title} - {selectedTopic.count_in_window} messages
              </CardTitle>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSelectedTopic(null)}
                className="h-6 w-6 p-0"
              >
                ✕
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Customer Evidence */}
            <div>
              <h3 className="font-semibold mb-3">Customer Evidence:</h3>
              <div className="space-y-3">
                {selectedTopic.evidence?.details ? (
                  selectedTopic.evidence.details.map((evidence: any, index: number) => (
                    <div key={index} className="border-l-4 border-muted pl-4 py-2">
                      <p className="text-sm italic mb-1">"{evidence.text}"</p>
                      <div className="flex items-center justify-between">
                        <p className="text-xs text-muted-foreground">
                          {evidence.source} • {formatRelativeTime(evidence.timestamp)}
                        </p>
                        <a 
                          href={evidence.link} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="text-primary hover:underline flex items-center gap-1 text-xs"
                        >
                          View <ExternalLink className="w-3 h-3" />
                        </a>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-sm text-muted-foreground">
                    Loading evidence...
                  </div>
                )}
              </div>
            </div>

            {/* AI Recommendation */}
            {selectedTopic.recommended_action && (
              <div>
                <h3 className="font-semibold mb-2">AI Recommendation:</h3>
                <p className="text-sm bg-muted/50 p-3 rounded-lg">
                  {selectedTopic.recommended_action}
                </p>
              </div>
            )}

            {/* Action Steps */}
            {selectedTopic.playbook_steps && selectedTopic.playbook_steps.length > 0 && (
              <div>
                <h3 className="font-semibold mb-3">📋 Action Steps:</h3>
                <ol className="space-y-2">
                  {selectedTopic.playbook_steps.map((step, index) => (
                    <li key={index} className="flex items-start gap-2 text-sm">
                      <span className="font-medium text-muted-foreground min-w-6">
                        {index + 1}.
                      </span>
                      <span>{step}</span>
                    </li>
                  ))}
                </ol>
              </div>
            )}

            {/* Impact Metrics */}
            <div className="grid grid-cols-2 gap-4 pt-4 border-t">
              <div>
                <p className="text-sm font-medium mb-1">📊 Impact:</p>
                <p className="text-lg font-bold">
                  {selectedTopic.affected_customers} customers
                </p>
                <p className="text-xs text-muted-foreground">
                  ({selectedTopic.customer_percentage}% of total)
                </p>
              </div>
              {selectedTopic.root_cause_hint && (
                <div>
                  <p className="text-sm font-medium mb-1">🔍 Root Cause:</p>
                  <p className="text-sm text-muted-foreground">
                    {selectedTopic.root_cause_hint}
                  </p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  };

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);
      if (oauthChecked && !oauthStatus.slack_connected && !oauthStatus.zendesk_connected) {
        const emptyData: DashboardData = {
          overview: { total_customers: 0, average_health_score: 0, high_risk_customers: 0, critical_insights: 0, todays_tickets: 0, average_sentiment: 0 },
          customers: [], recent_tickets: [], recent_slack_messages: [],
          sentiment_trend: [], ticket_status_breakdown: [], message_volume: [], insights: []
        };
        setDashboardData(emptyData);
        setTrendingTopics([]); setActiveAlerts([]); setRealtimeActivity([]);
        return;
      }
      // If both integrations are disconnected, show empty/clean slate data
      // if (!oauthStatus.slack_connected && !oauthStatus.zendesk_connected) {
      //   const emptyData: DashboardData = {
      //     overview: {
      //       total_customers: 0,
      //       average_health_score: 0,
      //       high_risk_customers: 0,
      //       critical_insights: 0,
      //       todays_tickets: 0,
      //       average_sentiment: 0
      //     },
      //     customers: [],
      //     recent_tickets: [],
      //     recent_slack_messages: [],
      //     sentiment_trend: [],
      //     ticket_status_breakdown: [],
      //     message_volume: [],
      //     insights: []
      //   };
      //   setDashboardData(emptyData);
      //   // Clear trending topics and alerts too
      //   setTrendingTopics([]);
      //   setActiveAlerts([]);
      //   setRealtimeActivity([]);
      //   setLoading(false);
      //   return;
      // }
      
      const data = await makeRequest('get_dashboard_data', { time_range: timeRange });
      
      // Mock additional chart data if not provided
      const mockSentimentTrend = Array.from({ length: 7 }, (_, i) => ({
        date: new Date(Date.now() - (6 - i) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
        sentiment: 0.4 + Math.random() * 0.4
      }));

      const mockTicketStatusBreakdown = [
        { status: 'open', count: Math.floor(Math.random() * 50) + 10 },
        { status: 'pending', count: Math.floor(Math.random() * 30) + 5 },
        { status: 'solved', count: Math.floor(Math.random() * 100) + 20 }
      ];

      const mockMessageVolume = Array.from({ length: 7 }, (_, i) => ({
        date: new Date(Date.now() - (6 - i) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
        messages: Math.floor(Math.random() * 50) + 10
      }));

      setDashboardData({
        ...data,
        sentiment_trend: data.sentiment_trend || mockSentimentTrend,
        ticket_status_breakdown: data.ticket_status_breakdown || mockTicketStatusBreakdown,
        message_volume: data.message_volume || mockMessageVolume
      });

      // Also load trending topics when dashboard refreshes (fallback if SSE fails)
      if (!sseConnected) {
        await loadTrendingTopics();
      }

      // Check OAuth status
      checkOAuthStatus();
      
      // Load trending topics
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard data');
      toast({
        title: "Error",
        description: "Failed to load dashboard data. Please try again.",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const checkOAuthStatus = async () => {
    try {
      // Get Slack status
      const slackResponse = await fetch(`${PUBLIC_BASE_URL}/api/integration-status`, {
        credentials: 'include'
      });
      
      // Get detailed Zendesk status
      const zendeskResponse = await fetch(`${PUBLIC_BASE_URL}/api/zendesk/credentials`, {
        credentials: 'include'
      });
      
      if (slackResponse.ok) {
        const status = await slackResponse.json();
        setOauthStatus(prev => ({
          ...prev,
          slack_connected: status.slack_connected
        }));
        if (status.slack_info) setSlackInfo(status.slack_info);
      }
      
      if (zendeskResponse.ok) {
        const zendeskStatus = await zendeskResponse.json();
        setOauthStatus(prev => ({
          ...prev,
          zendesk_connected: zendeskStatus.configured
        }));
        
        if (zendeskStatus.configured) {
          setZendeskInfo({
            subdomain: zendeskStatus.subdomain,
            needs_security_upgrade: zendeskStatus.needs_security_upgrade,
            encryption_version: zendeskStatus.encryption_version
          });
        }
      }
    } catch (err) {
      console.error('Error checking OAuth status:', err);
      // Fallback to disconnected state
      setOauthStatus({
        zendesk_connected: false,
        slack_connected: false
      });
    }
  };

  const checkOAuthCallback = () => {
    const params = new URLSearchParams(window.location.search);
    const provider = params.get('oauth');       // 'slack' | 'zendesk' | null
    const ok = params.get('ok');                // '1' | '0' | null
    const error = params.get('error');          // optional
    const team = params.get('team');            // Slack team name (optional)
    const subdomain = params.get('subdomain');  // Zendesk subdomain (optional)
    const intg = params.get('intg') === '1';    // Zendesk integration setup flag
    const wsid = params.get('wsid') || params.get('workspace_id'); // Slack workspace id (from backend redirect)

    // If the URL isn't an OAuth return, do nothing.
    if (!provider || !ok) return;

    if (ok === '1') {
      setOauthSuccess(true);
      if (provider === 'slack') {
        setOauthMessage(
          `Slack connected successfully${team ? ` for ${team}` : ''}! ` +
          `Important: To analyze messages from specific channels, please invite the @Catchalyze bot ` +
          `to those channels by typing /invite @Catchalyze in each channel you wish to monitor.`
        );
      } else if (provider === 'zendesk') {
        setOauthMessage(
          `Zendesk connected${subdomain ? ` for ${subdomain}` : ''}! ` +
          (intg ? `Webhook & trigger configured. ` : `Webhook/trigger setup pending. `) +
          `Your support tickets are now being monitored.`
        );
      }
      setShowOAuthDialog(true);
      // Refresh from server instead of localStorage
      checkOAuthStatus();
    } else {
      setOauthSuccess(false);
      const pretty = provider === 'slack' ? 'Slack' : 'Zendesk';
      
      // Handle specific error cases with clearer messages
      if (error === 'workspace_already_connected') {
        setOauthMessage(
          'This Slack workspace is already connected to another Catchalyze account. ' +
          'Each workspace can only be connected to one account at a time.'
        );
      } else if (error === 'subdomain_already_connected') {
        setOauthMessage(
          'This Zendesk subdomain is already connected to another Catchalyze account. ' +
          'Each subdomain can only be connected to one account at a time.'
        );
      } else {
        setOauthMessage(`OAuth Error (${pretty}): ${error || 'Unknown error'}`);
      }
      
      setShowOAuthDialog(true);
    }

    // Clean the URL so refreshes don't re-trigger the dialog
    window.history.replaceState({}, document.title, window.location.pathname);
  };

  // Add this after your existing handler functions (around line 400-450)
  const handleRunEvaluation = async () => {
    try {
      const result = await makeRequest('run_evaluation_harness');
      toast({
        title: "Evaluation Complete",
        description: `Quality Score: ${result.quality_score}/100 - ${result.recommendation}`,
      });
      // Evaluation completed
    } catch (error) {
      toast({
        title: "Evaluation Failed",
        description: "Failed to run evaluation tests",
        variant: "destructive"
      });
    }
  };

  const handleRegenerateTopicNames = async () => {
    try {
      await callMCPTool('regenerate_topic_names', {});
      
      // Optionally refresh the dashboard data
      await loadDashboardData();
      
      // Show success message
      toast({
        title: "Topic Names",
        description: "Topic name regeneration started in background",
      });
    } catch (error) {
      console.error('Error regenerating topic names:', error);
      toast({
        title: "Error",
        description: "Failed to regenerate topic names",
        variant: "destructive",
      });
    }
  };

  const loadRateLimitAnalytics = async () => {
    try {
      return await callMCPTool('get_rate_limit_analytics', { hours: 24 });
    } catch (error) {
      console.error('Error loading rate limit analytics:', error);
      return null;
    }
  };

  const isValidSubdomain = (s: string) => /^[a-z0-9-]{1,63}$/i.test(s);
  const handleZendeskConnect = async () => {
    if (zendeskBusy) return;

    setZendeskBusy(true);
    // Get current status to check if already connected
    const response = await fetch(`${PUBLIC_BASE_URL}/api/integration-status`, {
      credentials: 'include'
    });
    const status = await response.json();
    setZendeskBusy(false);
    
    if (status.zendesk_connected) {
      toast({
        title: 'Zendesk',
        description: 'Already connected to Zendesk.',
      });
      return;
    }
    
    // Show the onboarding wizard instead of prompt
    setShowZendeskWizard(true);
  };


  const handleSlackConnect = () => {
    window.location.href = `${PUBLIC_BASE_URL}/slack/oauth/start`;
  };

  const handleZendeskDisconnect = async () => {
    if (zendeskBusy) return;
    const ok = window.confirm('Disconnect Zendesk? This will remove your saved credentials and webhooks. You can reconnect anytime.');
    if (!ok) return;

    setZendeskBusy(true);
    try {
      let subdomain = zendeskInfo?.subdomain;
      
      if (!subdomain) {
        const response = await fetch(`${PUBLIC_BASE_URL}/api/integration-status`, {
          credentials: 'include'
        });
        const status = await response.json();
        subdomain = status.zendesk_info?.subdomain;
      }
      
      if (!subdomain) {
        toast({
          title: 'Zendesk',
          description: 'No Zendesk integration found for this account.',
          variant: 'destructive',
        });
        return;
      }

      const res = await fetch(`${PUBLIC_BASE_URL}/zendesk/disconnect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ subdomain }),
      });
      
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      setZendeskInfo(null);
      setOauthStatus(s => ({ ...s, zendesk_connected: false }));
      // await checkOAuthStatus();
      // setTimeout(() => checkOAuthStatus(), 500);
      toast({ title: 'Zendesk', description: 'Disconnected.' });
    } catch (e) {
      toast({
        title: 'Zendesk',
        description: 'Disconnect failed (continuing as disconnected).',
        variant: 'destructive',
      });
    } finally {
      setZendeskBusy(false);
    }
  };

const handleSlackDisconnect = async () => {
  if (slackBusy) return;
    const ok = window.confirm('Disconnect Slack? This will remove your saved credentials. You can reconnect anytime.');
    if (!ok) return;

    setSlackBusy(true);
    try {
      // Get current integration info from server if not cached
      let workspaceId = slackInfo?.workspace_id;
      
      if (!workspaceId) {
        const response = await fetch(`${PUBLIC_BASE_URL}/api/integration-status`, {
          credentials: 'include'
        });
        const status = await response.json();
        workspaceId = status.slack_info?.workspace_id;
      }
      
      if (!workspaceId) {
        toast({
          title: 'Slack',
          description: 'No Slack integration found for this account.',
          variant: 'destructive',
        });
        return;
      }

      const res = await fetch(`${PUBLIC_BASE_URL}/slack/disconnect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ workspace_id: workspaceId }),
      });
      
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      // Clear state and refresh from server
      setSlackInfo(null);
      setOauthStatus(s => ({ ...s, slack_connected: false }));
      // await checkOAuthStatus();
      // setTimeout(() => checkOAuthStatus(), 500);
      toast({ title: 'Slack', description: 'Disconnected.' });
    } catch (e) {
      toast({
        title: 'Slack',
        description: 'Disconnect failed (continuing as disconnected).',
        variant: 'destructive',
      });
    } finally {
      setSlackBusy(false);
    }
  };

  // Helper functions for insights generation
  const callMCPTool = async (name: string, args: any) => {
    const res = await fetch(`${API_BASE_URL}/mcp/rpc`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/event-stream',
      },
      body: JSON.stringify({
        jsonrpc: '2.0',
        id: 'ui-run',
        method: 'tools/call',
        params: { name, arguments: args },
      }),
    });

    const text = await res.text();

    // If server replied JSON, parse directly.
    if (text.trim().startsWith('{')) {
      return JSON.parse(text);
    }

    // Otherwise treat as SSE: find the first "data: " line and parse its JSON.
    const dataLine = text.split('\n').find(l => l.startsWith('data: '));
    if (!dataLine) throw new Error('No SSE data');
    return JSON.parse(dataLine.slice('data: '.length));
  };

  const getDashboardData = async (timeRange = '7d') => {
    const r = await callMCPTool('get_dashboard_data', { time_range: timeRange });
    // r.result.structuredContent holds the parsed object on JSON,
    // or nested JSON string at r.result.content[0].text (if present).
    const sc = r?.result?.structuredContent;
    if (sc) return sc;
    const txt = r?.result?.content?.[0]?.text;
    return txt ? JSON.parse(txt) : null;
  };

  const formatRelativeTime = (timestamp: string) => {
    if (!timestamp) return 'Unknown time';
    
    try {
      const now = new Date();
      
      // Handle the timezone issue: treat timestamps as local time if they look like UTC
      let date;
      if (timestamp.includes('+00:00') || timestamp.endsWith('Z')) {
        // This is a UTC timestamp, but it's actually local time
        // Remove the timezone info and parse as local
        const localTimestamp = timestamp.replace('+00:00', '').replace('Z', '');
        date = new Date(localTimestamp);
      } else {
        date = new Date(timestamp);
      }
      
      if (isNaN(date.getTime())) {
        // Invalid timestamp detected
        return 'Invalid time';
      }
      
      const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60));
      
      if (diffInMinutes < 1) return 'Just now';
      if (diffInMinutes < 60) return `${diffInMinutes}m ago`;
      
      const diffInHours = Math.floor(diffInMinutes / 60);
      if (diffInHours < 24) return `${diffInHours}h ago`;
      
      const diffInDays = Math.floor(diffInHours / 24);
      if (diffInDays < 7) return `${diffInDays}d ago`;
      
      const diffInWeeks = Math.floor(diffInDays / 7);
      if (diffInWeeks < 4) return `${diffInWeeks}w ago`;
      
      const diffInMonths = Math.floor(diffInDays / 30);
      if (diffInMonths < 12) return `${diffInMonths}mo ago`;
      
      const diffInYears = Math.floor(diffInDays / 365);
      return `${diffInYears}y ago`;
      
    } catch (error) {
      // Error formatting timestamp
      return 'Invalid time';
    }
  };
  const handleGenerateInsights = async () => {
    if (isGenerating) return;
    
    setIsGenerating(true);
    try {
      await callMCPTool('generate_customer_insights', { time_range: '7d' });
      
      // Success - store timestamp and refresh dashboard
      const timestamp = new Date().toISOString();
      localStorage.setItem('last_insights_generated_at', timestamp);
      setLastGeneratedAt(timestamp);
      
      toast({
        title: "Success",
        description: "Insights generated successfully.",
      });
      
      // Refresh dashboard data
      const newData = await getDashboardData('7d');
      if (newData) {
        const mockSentimentTrend = Array.from({ length: 7 }, (_, i) => ({
          date: new Date(Date.now() - (6 - i) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
          sentiment: 0.4 + Math.random() * 0.4
        }));

        const mockTicketStatusBreakdown = [
          { status: 'open', count: Math.floor(Math.random() * 50) + 10 },
          { status: 'pending', count: Math.floor(Math.random() * 30) + 5 },
          { status: 'solved', count: Math.floor(Math.random() * 100) + 20 }
        ];

        const mockMessageVolume = Array.from({ length: 7 }, (_, i) => ({
          date: new Date(Date.now() - (6 - i) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
          messages: Math.floor(Math.random() * 50) + 10
        }));

        setDashboardData({
          ...newData,
          sentiment_trend: newData.sentiment_trend || mockSentimentTrend,
          ticket_status_breakdown: newData.ticket_status_breakdown || mockTicketStatusBreakdown,
          message_volume: newData.message_volume || mockMessageVolume
        });
      }
    } catch (error) {
      console.error('Failed to generate insights:', error);
      toast({
        title: "Error",
        description: "Failed to generate insights. Please try again.",
        variant: "destructive"
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const filteredTickets = dashboardData?.recent_tickets?.filter(ticket => {
    const matchesSearch = ticket.subject.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesFilter = filterStatus === 'all' || ticket.status === filterStatus;
    return matchesSearch && matchesFilter;
  }) || [];
  useEffect(() => {
    if (isAuthenticated) {
      setOauthChecked(false);
      checkOAuthStatus().finally(() => setOauthChecked(true));
    }
  }, [isAuthenticated]);
  // Effects - Must come before conditional returns
  useEffect(() => {
    if (isAuthenticated && oauthChecked && !hasLoadedRef.current) {
      loadDashboardData();
      checkOAuthCallback();
      hasLoadedRef.current = true;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timeRange, isAuthenticated, oauthChecked, oauthStatus.slack_connected, oauthStatus.zendesk_connected]);

  useEffect(() => {
    hasLoadedRef.current = false;
  }, [isAuthenticated]);

  useEffect(() => {
    if (isAuthenticated) {
      // Load trending topics on initial load, regardless of dashboardData
      loadTrendingTopics();
    }
  }, [isAuthenticated]);

  // Sync trending topics with existing scheduler cycles
  useEffect(() => {
    if (isAuthenticated && dashboardData) {
      loadTrendingTopics();
    }
  }, [dashboardData, timeRange, isAuthenticated]);

  // SSE connection setup
  useEffect(() => {
    if (!isAuthenticated) return;
    
    const connectSSE = () => {
      try {
        // Replace with your actual ngrok URL or production URL
        const sse = new EventSource(`${API_BASE_URL}/api/realtime-updates`, {
          withCredentials: true
        });
        
        sse.onopen = () => {
          console.log('SSE connection established');
          setSseConnected(true);
          if (oauthChecked) loadDashboardData();
        };

        sse.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            
            if (data.type === 'new_trends') {
              console.log('Received new trends via SSE:', data.trends);
              
              // Replace the filtering logic around line 688 with this debug version:
              const activeTrends = data.trends.filter((trend: any) => {
                const trendTime = new Date(trend.created_at || trend.window_start || trend.timestamp);
                const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000); // 7 days instead of 24 hours
                
                return trendTime > sevenDaysAgo;
              });
              
              // Only proceed if we have active trends
              if (activeTrends.length === 0) {
                return;
              }
              
              // Transform backend format to frontend format
              const transformedTopics = activeTrends.map((topic: any) => ({
                ...topic,
                severity: calculateSeverity(topic),
                timestamp: topic.created_at || topic.window_start || new Date().toISOString(),
                display_timestamp: new Date().toISOString()
              }));
              
              // Update trending topics immediately
              setTrendingTopics(prev => {
                // Apply 24-hour filter consistently 
                const twentyFourHoursAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);
                const filteredExisting = prev.filter(t => new Date(t.timestamp) > twentyFourHoursAgo);
                const existingIds = new Set(filteredExisting.map(t => t.topic_id));
                const newTrends = transformedTopics.filter(t => !existingIds.has(t.topic_id));
                return [...filteredExisting, ...newTrends];
              });
              
              // Show toast notifications for critical/high severity trends (keep 1-hour filter for alerts)
              const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000);  // ← Keep 1-hour filter for alerts
              const criticalTrends = transformedTopics.filter((topic: any) => {
                const trendTime = new Date(topic.timestamp);
                return trendTime > oneHourAgo && 
                       ['critical', 'high'].includes(topic.severity) && 
                       !dismissedAlerts.has(topic.topic_id);
              });
              
              criticalTrends.forEach((trend: any) => {
                toast({
                  title: `🚨 ${trend.title || trend.name || 'Critical Trend Detected'}`,
                  description: `${trend.count_in_window} reports detected - requires immediate attention`,
                  duration: 10000, // Show for 10 seconds
                });
              });
              
              // Update active alerts (keep 1-hour filter for alerts)
              setActiveAlerts(criticalTrends);

              // Also update radar with real-time trend activity
              setRealtimeActivity(prev => {
                // Create new trend activities
                const newTrendActivities = data.trends.map((t: any, index: number) => ({
                  id: `trend-${t.id || t.topic_id}-${Date.now()}-${index}`,
                  type: 'trend_detected',
                  title: t.title || t.name || 'New trend detected',
                  timestamp: new Date().toISOString(),
                  source: t.sources?.[0] || 'unknown'
                }));
                
                // Check for duplicates based on title and type
                const filteredNewActivities = newTrendActivities.filter(newActivity => 
                  !prev.some(activity => 
                    activity.title === newActivity.title && 
                    activity.type === newActivity.type &&
                    Math.abs(new Date(activity.timestamp).getTime() - new Date(newActivity.timestamp).getTime()) < 30000 // Within 30 seconds
                  )
                );
                
                if (filteredNewActivities.length === 0) {
                  return prev;
                }
                
                return [...filteredNewActivities, ...prev.slice(0, 4)]; // Keep last 5 activities
              });
              
            } else if (data.type === 'new_message' || data.type === 'new_ticket') {
              // Add individual message/ticket activity to radar
              const newActivity = {
                id: `${data.type}-${Date.now()}-${Math.random()}`, // Unique ID
                type: data.type,
                title: data.text || data.subject || 'New activity',
                timestamp: new Date().toISOString(),
                source: data.type === 'new_message' ? 'slack' : 'zendesk'
              };
              
              setRealtimeActivity(prev => {
                // Check for duplicates based on title and type to prevent duplicate messages
                const isDuplicate = prev.some(activity => 
                  activity.title === newActivity.title && 
                  activity.type === newActivity.type &&
                  Math.abs(new Date(activity.timestamp).getTime() - new Date(newActivity.timestamp).getTime()) < 5000 // Within 5 seconds
                );
                
                if (isDuplicate) {
                  return prev;
                }
                
                return [newActivity, ...prev.slice(0, 4)]; // Keep last 5 activities
              });
              
            } else if (data.type === 'connected') {
              console.log('SSE handshake confirmed');
            } else if (data.type === 'heartbeat') {
              // Keep connection alive
            }
          } catch (error) {
            console.error('Error parsing SSE message:', error);
          }
        };

        sse.onerror = (error) => {
          console.error('SSE connection error:', error);
          setSseConnected(false);
          
          // Attempt to reconnect after 5 seconds
          setTimeout(() => {
            if (sse.readyState === EventSource.CLOSED) {
              connectSSE();
            }
          }, 5000);
        };

        setEventSource(sse);
        
        return sse;
      } catch (error) {
        console.error('Failed to establish SSE connection:', error);
        setSseConnected(false);
        return null;
      }
    };

    const sse = connectSSE();

    // Cleanup on unmount
    return () => {
      if (sse) {
        sse.close();
        setSseConnected(false);
      }
    };
  }, [isAuthenticated]); // Add isAuthenticated to dependency array

  useEffect(() => {
    if (isAuthenticated && sseConnected && oauthChecked) {
      loadDashboardData();
    }
  }, [isAuthenticated, sseConnected, oauthChecked]);

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (!isAuthenticated) {
    return (
      <LandingPage 
        onBetaAccess={onBetaAccess}
      />
    );
  }

  // Check beta access
  if (!user?.beta_access) {
    return <BetaAccessRequired onBetaAccess={onBetaAccess} onBackToHome={logout} />;
  }

  if (loading && !dashboardData) {
    return (
      <div className="min-h-screen bg-background">
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-center space-y-4">
            <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
            <p className="text-muted-foreground">Loading dashboard...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error && !dashboardData) {
    return (
      <div className="min-h-screen bg-background">
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-center space-y-4">
            <AlertCircle className="h-8 w-8 mx-auto text-destructive" />
            <p className="text-destructive">{error}</p>
            <Button onClick={loadDashboardData}>Try Again</Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50/30 font-calibri">
          <header className="border-b bg-card">
            <div className="container mx-auto px-4 py-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <MessageSquare className="h-6 w-6 text-primary" />
                  <span className="text-xl font-semibold text-foreground">Catchalyze</span>
                  {account && (
                    <Badge variant="secondary" className="ml-4">
                      {account.name}
                    </Badge>
                  )}
                </div>
                <div className="flex items-center space-x-4">
                  {user && (
                    <div className="flex items-center space-x-3">
                      <div className="text-right">
                        <div className="text-sm font-medium text-foreground">{user.name}</div>
                        <div className="text-xs text-muted-foreground">{user.email}</div>
                      </div>
                      <Button variant="outline" onClick={logout}>
                        Sign Out
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </header>

          <div className="container mx-auto px-4 py-8">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 lg:items-stretch">
            <div className="lg:col-span-2 space-y-8 flex flex-col">
            {/* Controls */}
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-slate-900 via-blue-800 to-indigo-800 bg-clip-text text-transparent">Dashboard</h1>
                  <p className="text-lg text-slate-600 mt-2">
                    Real-time customer intelligence • Monitoring {dashboardData?.overview.total_customers || 0} customers
                  </p>
                </div>
                <div className="flex items-center space-x-4">
                  <Select value={timeRange} onValueChange={setTimeRange}>
                    <SelectTrigger className="w-40">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {TIME_RANGES.map(range => (
                        <SelectItem key={range.value} value={range.value}>
                          {range.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Button 
                    variant="outline" 
                    onClick={loadDashboardData}
                    disabled={loading}
                  >
                    {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                    Refresh
                  </Button>
                </div>
              </div>

            {/* Integration Status */}
            <Card className="bg-white/80 backdrop-blur-sm border border-slate-200/60 shadow-sm hover:shadow-md transition-all duration-200 rounded-lg">
              <CardHeader>
                <CardTitle className="flex items-center space-x-2 text-xl font-semibold text-slate-900">
                  <Zap className="h-5 w-5 text-blue-600" />
                  <span>Integrations</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-2 gap-4">
                  <div className="flex items-center justify-between p-4 border rounded-md">
                    <div className="flex items-center space-x-3">
                      <div className="p-2 bg-purple-100 rounded-md">
                        <MessageCircle className="h-5 w-5 text-purple-600" />
                      </div>
                      <div>
                        <p className="font-medium">Slack</p>
                        <p className="text-sm text-muted-foreground">
                          {oauthStatus.slack_connected ? 'Connected' : 'Not Connected'}
                        </p>
                      </div>
                    </div>
                    {oauthStatus.slack_connected ? (
                      <div className="flex items-center space-x-2">
                        <CheckCircle className="h-5 w-5 text-green-600" />
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={handleSlackDisconnect}
                          disabled={slackBusy}
                        >
                          {slackBusy && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
                          {slackBusy ? 'Disconnecting…' : 'Disconnect'}
                        </Button>
                      </div>
                    ) : (
                      <Button onClick={handleSlackConnect} size="sm">
                        Connect
                      </Button>
                    )}
                  </div>
                  <div className="flex items-center justify-between p-4 border rounded-md">
                    <div className="flex items-center space-x-3">
                      <div className="p-2 bg-blue-100 rounded-md">
                        <Ticket className="h-5 w-5 text-blue-600" />
                      </div>
                      <div>
                        <p className="font-medium">Zendesk</p>
                        <p className="text-sm text-muted-foreground">
                          {oauthStatus.zendesk_connected ? 'Connected' : 'Not Connected'}
                        </p>
                      </div>
                    </div>
                    {oauthStatus.zendesk_connected ? (
                      <div className="flex items-center space-x-2">
                        <CheckCircle className="h-5 w-5 text-green-600" />
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={handleZendeskDisconnect}
                          disabled={zendeskBusy}
                        >
                          {zendeskBusy && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
                          {zendeskBusy ? 'Disconnecting…' : 'Disconnect'}
                        </Button>
                      </div>
                    ) : (
                      <Button onClick={handleZendeskConnect} size="sm">
                        Connect
                      </Button>
                    )}
                    
                    {/* Security Upgrade Warning */}
                    {oauthStatus.zendesk_connected && zendeskInfo?.needs_security_upgrade && (
                      <Alert variant="destructive" className="mt-3">
                        <AlertCircle className="h-4 w-4" />
                        <AlertTitle>Security Update Required</AlertTitle>
                        <AlertDescription>
                          Please re-connect your Zendesk integration to upgrade to enhanced encryption security.
                        </AlertDescription>
                      </Alert>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Zendesk Onboarding Wizard Overlay */}
            {showZendeskWizard && (
              <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                <ZendeskOnboardingWizard
                  onComplete={() => {
                    setShowZendeskWizard(false);
                    // Refresh OAuth status after completion
                    checkOAuthStatus();
                  }}
                  onCancel={() => setShowZendeskWizard(false)}
                />
              </div>
            )}


            {/* Key Metrics */}
            {dashboardData?.overview && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <Card className="group bg-gradient-to-br from-blue-50 to-blue-100/50 border border-transparent bg-gradient-to-r from-blue-200/40 via-blue-100 to-blue-200/40 bg-origin-border hover:shadow-xl hover:-translate-y-1 transition-all duration-300 ease-out rounded-lg relative overflow-hidden">
                  <div className="absolute inset-0 bg-gradient-to-r from-blue-500/10 via-blue-400/5 to-blue-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                  <CardContent className="p-6 relative z-10">
                    <div className="flex items-center space-x-2">
                      <Users className="h-5 w-5 text-blue-600 group-hover:scale-110 transition-transform duration-200" />
                      <p className="text-sm font-medium text-blue-700">Total Customers</p>
                    </div>
                    <p className="text-2xl font-bold text-blue-800 group-hover:scale-105 transition-transform duration-200">{dashboardData.overview.total_customers}</p>
                  </CardContent>
                </Card>

                <Card className="group bg-gradient-to-br from-emerald-50 to-emerald-100/50 border border-transparent bg-gradient-to-r from-emerald-200/40 via-emerald-100 to-emerald-200/40 bg-origin-border hover:shadow-xl hover:-translate-y-1 transition-all duration-300 ease-out rounded-lg relative overflow-hidden">
                  <div className="absolute inset-0 bg-gradient-to-r from-emerald-500/10 via-emerald-400/5 to-emerald-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                  <CardContent className="p-6 relative z-10">
                    <div className="flex items-center space-x-2">
                      <Activity className="h-5 w-5 text-emerald-600 group-hover:scale-110 transition-transform duration-200" />
                      <p className="text-sm font-medium text-emerald-700">Avg Health Score</p>
                    </div>
                    <p className="text-2xl font-bold text-emerald-800 group-hover:scale-105 transition-transform duration-200">{dashboardData.overview.average_health_score}%</p>
                  </CardContent>
                </Card>

                <Card className={`group bg-gradient-to-br border border-transparent bg-origin-border hover:shadow-xl hover:-translate-y-1 transition-all duration-300 ease-out rounded-lg relative overflow-hidden ${
                  dashboardData.overview.average_sentiment >= 0 
                    ? 'from-green-50 to-green-100/50 bg-gradient-to-r from-green-200/40 via-green-100 to-green-200/40' 
                    : 'from-red-50 to-red-100/50 bg-gradient-to-r from-red-200/40 via-red-100 to-red-200/40'
                }`}>
                  <div className={`absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 ${
                    dashboardData.overview.average_sentiment >= 0 
                      ? 'bg-gradient-to-r from-green-500/10 via-green-400/5 to-green-500/10' 
                      : 'bg-gradient-to-r from-red-500/10 via-red-400/5 to-red-500/10'
                  }`}></div>
                  <CardContent className="p-6 relative z-10">
                    <div className="flex items-center space-x-2">
                      <MessageCircle className={`h-5 w-5 group-hover:scale-110 transition-transform duration-200 ${
                        dashboardData.overview.average_sentiment >= 0 ? 'text-green-600' : 'text-red-600'
                      }`} />
                      <p className={`text-sm font-medium ${
                        dashboardData.overview.average_sentiment >= 0 ? 'text-green-700' : 'text-red-700'
                      }`}>Avg Sentiment</p>
                    </div>
                    <p className={`text-2xl font-bold group-hover:scale-105 transition-transform duration-200 ${
                      dashboardData.overview.average_sentiment >= 0 ? 'text-green-800' : 'text-red-800'
                    }`}>
                      {(dashboardData.overview.average_sentiment * 100).toFixed(0)}%
                    </p>
                  </CardContent>
                </Card>

                <Card className="group bg-gradient-to-br from-orange-50 to-orange-100/50 border border-transparent bg-gradient-to-r from-orange-200/40 via-orange-100 to-orange-200/40 bg-origin-border hover:shadow-xl hover:-translate-y-1 transition-all duration-300 ease-out rounded-lg relative overflow-hidden">
                  <div className="absolute inset-0 bg-gradient-to-r from-orange-500/10 via-orange-400/5 to-orange-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                  <CardContent className="p-6 relative z-10">
                    <div className="flex items-center space-x-2">
                      <TrendingUp className="h-5 w-5 text-orange-600 group-hover:scale-110 transition-transform duration-200" />
                      <p className="text-sm font-medium text-orange-700">Critical Insights</p>
                    </div>
                    <p className="text-2xl font-bold text-orange-800 group-hover:scale-105 transition-transform duration-200">{dashboardData.overview.critical_insights}</p>
                  </CardContent>
                </Card>
              </div>
            )}

            {/* RadarPanel - Moved to main content area for operational prominence */}
            {dashboardData && (
              <div className="flex-1 flex flex-col">
                <RadarPanel 
                  data={dashboardData} 
                  realtimeActivity={realtimeActivity}
                  sseConnected={sseConnected}
                />
              </div>
            )}

            {SHOW_DEBUG_PANELS && <RateLimitMonitoringPanel />}
            </div>
            <div className="lg:col-span-1 space-y-6 flex flex-col">
              <TrendIntelligencePanel />
              
              {/* Charts - Moved under Trending Topics */}
              {dashboardData && (
                <div className="space-y-6">
                  {/* Sentiment Trend */}
                  <Card className="bg-gradient-to-br from-white to-slate-50/30 border border-slate-200/60 rounded-lg">
                    <CardHeader className="border-b border-slate-100">
                      <CardTitle className="text-xl font-bold text-slate-900">Sentiment Trend</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <ResponsiveContainer width="100%" height={200}>
                        <LineChart data={dashboardData.sentiment_trend}>
                          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                          <XAxis 
                            dataKey="date" 
                            stroke="hsl(var(--muted-foreground))"
                            fontSize={12}
                          />
                          <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} />
                          <Tooltip 
                            contentStyle={{ 
                              backgroundColor: 'hsl(var(--card))', 
                              border: '1px solid hsl(var(--border))',
                              borderRadius: 'var(--radius)'
                            }}
                          />
                          <Line 
                            type="monotone" 
                            dataKey="sentiment" 
                            stroke="hsl(var(--primary))" 
                            strokeWidth={2}
                            dot={{ fill: 'hsl(var(--primary))' }}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    </CardContent>
                  </Card>

                  {/* Ticket Status Breakdown */}
                  <Card className="bg-gradient-to-br from-white to-slate-50/30 border border-slate-200/60 rounded-lg">
                    <CardHeader className="border-b border-slate-100">
                      <CardTitle className="text-xl font-bold text-slate-900">Ticket Status</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <ResponsiveContainer width="100%" height={200}>
                        <PieChart>
                          <Pie
                            data={dashboardData.ticket_status_breakdown}
                            cx="50%"
                            cy="50%"
                            outerRadius={80}
                            dataKey="count"
                            nameKey="status"
                          >
                            {dashboardData.ticket_status_breakdown?.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                            ))}
                          </Pie>
                          <Tooltip 
                            contentStyle={{ 
                              backgroundColor: 'hsl(var(--card))', 
                              border: '1px solid hsl(var(--border))',
                              borderRadius: 'var(--radius)'
                            }}
                          />
                        </PieChart>
                      </ResponsiveContainer>
                    </CardContent>
                  </Card>

                  {/* Message Volume */}
                  <Card className="bg-gradient-to-br from-white to-slate-50/30 border border-slate-200/60 rounded-lg">
                    <CardHeader className="border-b border-slate-100">
                      <CardTitle className="text-xl font-bold text-slate-900">Message Volume</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <ResponsiveContainer width="100%" height={200}>
                        <BarChart data={dashboardData.message_volume}>
                          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                          <XAxis 
                            dataKey="date" 
                            stroke="hsl(var(--muted-foreground))"
                            fontSize={12}
                          />
                          <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} />
                          <Tooltip 
                            contentStyle={{ 
                              backgroundColor: 'hsl(var(--card))', 
                              border: '1px solid hsl(var(--border))',
                              borderRadius: 'var(--radius)'
                            }}
                          />
                          <Bar dataKey="messages" fill="hsl(var(--primary))" radius={4} />
                        </BarChart>
                      </ResponsiveContainer>
                    </CardContent>
                  </Card>
                </div>
              )}
            </div>
            </div>

          </div>

          {/* Topic Detail Modal */}
          <TopicDetailModal />

          {/* OAuth Success/Error Dialog */}
          <AlertDialog open={showOAuthDialog} onOpenChange={setShowOAuthDialog}>
            <AlertDialogContent className="rounded-lg">
              <AlertDialogHeader>
                <AlertDialogTitle>
                  {oauthSuccess ? 'Connection Successful' : 'Connection Failed'}
                </AlertDialogTitle>
                <AlertDialogDescription>
                  {oauthMessage}
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogAction onClick={() => setShowOAuthDialog(false)}>
                  Continue
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>

          <Toaster />

          {/* Historical Trends Modal */}
          <HistoricalTrendsModal 
            isOpen={isHistoricalModalOpen} 
            onClose={handleHistoricalModalClose} 
          />
        </div>
      );
    };

export default App;