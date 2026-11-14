import { DailyMetrics, Order, Product, Customer, Approval } from '../types';

const API_BASE = 'http://localhost:8000/api/v1';

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
