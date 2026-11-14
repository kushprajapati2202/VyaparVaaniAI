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
