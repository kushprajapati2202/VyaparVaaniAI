import { DailyMetrics, Order, Product, Customer, Approval, ImpactMetrics } from '../types';

// Dev (vite on :5173) talks to uvicorn on :8000; in production the backend serves the SPA (same origin).
const API_ORIGIN: string =
  (import.meta as any).env?.VITE_API_ORIGIN ??
  (window.location.port === '5173' ? `${window.location.protocol}//${window.location.hostname}:8000` : window.location.origin);
const API_BASE = `${API_ORIGIN}/api/v1`;
export const VOICE_WS_URL = `${API_ORIGIN.replace(/^http/, 'ws')}/api/v1/voice/live`;

export const api = {
  async getDailyMetrics(): Promise<DailyMetrics> {
    const res = await fetch(`${API_BASE}/bi/daily-summary`);
    if (!res.ok) throw new Error('Failed to fetch BI metrics');
    return res.json();
  },

  async getOrders(): Promise<Order[]> {
    const res = await fetch(`${API_BASE}/orders`);
    if (!res.ok) throw new Error('Failed to fetch orders');
    return res.json();
  },

  async getInventory(search?: string): Promise<Product[]> {
    const url = search ? `${API_BASE}/inventory?search=${encodeURIComponent(search)}` : `${API_BASE}/inventory`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch inventory');
    return res.json();
  },

  async getCustomers(search?: string): Promise<Customer[]> {
    const url = search ? `${API_BASE}/customers?search=${encodeURIComponent(search)}` : `${API_BASE}/customers`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch customers');
    return res.json();
  },

  async getApprovals(): Promise<Approval[]> {
    const res = await fetch(`${API_BASE}/approvals`);
    if (!res.ok) throw new Error('Failed to fetch approvals');
    return res.json();
  },

  async resolveApproval(approvalId: string, approved: boolean, approverNotes?: string): Promise<any> {
    const res = await fetch(`${API_BASE}/approvals/${approvalId}/resolve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ approved, approver_notes: approverNotes })
    });
    if (!res.ok) throw new Error('Failed to resolve approval');
    return res.json();
  },

  async getImpact(): Promise<ImpactMetrics> {
    const res = await fetch(`${API_BASE}/bi/impact`);
    if (!res.ok) throw new Error('Failed to fetch impact metrics');
    return res.json();
  },

  async recordPayment(customerId: string, amount: number, mode: string = 'CASH'): Promise<any> {
    const res = await fetch(`${API_BASE}/ledger/payments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ customer_id: customerId, amount, mode })
    });
    if (!res.ok) throw new Error('Failed to record payment');
    return res.json();
  }
};
