export interface Customer {
  id: string;
  name: string;
  phone: string;
  address?: string;
  credit_limit: number;
  outstanding_balance: number;
  created_at: string;
}

export interface Product {
  id: string;
  sku: string;
  name: string;
  category: string;
  unit: string;
  purchase_price: number;
  selling_price: number;
  current_stock: number;
  min_stock_alert: number;
  is_low_stock: boolean;
}

export interface OrderItem {
  id?: string;
  product_id?: string;
  product_name: string;
  quantity: number;
  unit: string;
  unit_price: number;
  subtotal: number;
}

export interface Order {
  id: string;
  order_number: string;
  customer_id: string;
  customer_name: string;
  status: 'DRAFT' | 'PENDING_CONFIRMATION' | 'PENDING_APPROVAL' | 'CONFIRMED' | 'PROCESSING' | 'DISPATCHED' | 'DELIVERED' | 'CANCELLED';
  payment_method: string;
  subtotal: number;
  discount_amount: number;
  total_amount: number;
  items: OrderItem[];
  delivery_status?: string;
  requires_approval?: boolean;
  approval_reason?: string;
  created_at: string;
}

export interface Approval {
  id: string;
  order_id?: string;
  customer_id?: string;
  customer_name?: string;
  reason: string;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  action_payload?: any;
  created_at: string;
  resolved_at?: string;
}

export interface DailyMetrics {
  total_sales_today: number;
  orders_count_today: number;
  payments_received_today: number;
  total_outstanding_credit: number;
  low_stock_count: number;
  pending_deliveries_count: number;
  pending_approvals_count: number;
  automation_rate_percent: number;
  avg_transaction_time_sec: number;
  time_saved_hours: number;
}

export interface VoiceMessage {
  id: string;
  role: 'user' | 'agent' | 'system';
  text: string;
  timestamp: string;
  toolCall?: {
    tool: string;
    args: any;
    result?: any;
  };
}

// ---- Live agent events -------------------------------------------------------
export interface AgentLineItem {
  product_id?: string;
  product_name: string;
  quantity: number;
  unit: string;
  unit_price: number;
  subtotal: number;
}

export type AgentActionStatus =
  | 'AWAITING_CONFIRMATION' | 'EXECUTED' | 'PENDING_APPROVAL' | 'CANCELLED' | 'UNDONE' | 'REJECTED';

export interface AgentAction {
  action_id: string;
  kind: 'ORDER' | 'PAYMENT';
  status: AgentActionStatus;
  customer_name: string;
  warnings: string[];
  corrections: number;
  created_at: string;
  items?: AgentLineItem[];
  total_amount?: number;
  payment_method?: string;
  requires_approval?: boolean;
  approval_reason?: string | null;
  amount?: number;
  mode?: string;
  outstanding_before?: number;
  projected_balance?: number;
  result?: Record<string, any>;
}

export interface ActivityEntry {
  id: string;
  kind: 'step' | 'tool' | 'exception' | 'barge_in' | 'approval' | 'info';
  title: string;
  detail?: string;
  status?: string;
  human?: boolean;
  latencyMs?: number;
  ok?: boolean;
  at: string;
}

export interface ImpactMetrics {
  voice_sessions: number;
  transactions_completed: number;
  orders_completed: number;
  payments_completed: number;
  undone: number;
  approvals_required: number;
  automation_rate_percent: number;
  human_touch_rate_percent: number;
  exceptions_caught: number;
  exceptions_by_code: Record<string, number>;
  corrections_handled: number;
  languages: Record<string, number>;
  avg_response_latency_ms: number | null;
  p90_response_latency_ms: number | null;
  avg_tool_latency_ms: number | null;
  avg_voice_txn_seconds: number | null;
  manual_seconds_per_txn: number;
  time_saved_minutes: number;
  labour_saved_inr: number;
  total_ai_cost_inr: number;
  cost_per_transaction_inr: number | null;
  subscription_price_inr: number;
  breakeven_txns_per_month: number | null;
  assumptions: Record<string, number | string>;
}
