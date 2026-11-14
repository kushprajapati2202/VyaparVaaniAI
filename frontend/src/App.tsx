import React, { useState, useEffect } from 'react';
import { Navigation } from './components/Navigation';
import { VoiceCommandCenter } from './features/voice/VoiceCommandCenter';
import { Dashboard } from './features/dashboard/Dashboard';
import { OrdersPage } from './features/orders/OrdersPage';
import { InventoryPage } from './features/inventory/InventoryPage';
import { CustomersPage } from './features/customers/CustomersPage';
import { ApprovalCenter } from './features/approvals/ApprovalCenter';
import { AnalyticsPage } from './features/analytics/AnalyticsPage';
import { api } from './services/api';
import { DailyMetrics, Order, Product, Customer, Approval } from './types';

export function App() {
  const [activeTab, setActiveTab] = useState<string>('voice');
  const [currentLanguage, setCurrentLanguage] = useState<string>('gu-IN');
  const [metrics, setMetrics] = useState<DailyMetrics | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [inventory, setInventory] = useState<Product[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const loadData = async () => {
    try {
      const [m, o, inv, c, apprs] = await Promise.all([
        api.getDailyMetrics().catch(() => null),
        api.getOrders().catch(() => []),
        api.getInventory().catch(() => []),
        api.getCustomers().catch(() => []),
        api.getApprovals().catch(() => [])
      ]);
      if (m) setMetrics(m);
      setOrders(o);
      setInventory(inv);
      setCustomers(c);
      setApprovals(apprs);
    } catch (e) {
      console.warn('Initial data load warning:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  const pendingApprovalsCount = approvals.filter((a) => a.status === 'PENDING').length;

  return (
    <div className="min-h-screen bg-background text-slate-100 flex flex-col font-sans">
      <Navigation
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        pendingApprovalsCount={pendingApprovalsCount}
        currentLanguage={currentLanguage}
        setCurrentLanguage={setCurrentLanguage}
      />

      <main className="flex-1 pb-24 md:pb-12">
        {activeTab === 'voice' && (
          <VoiceCommandCenter
            currentLanguage={currentLanguage}
            onRefreshData={loadData}
          />
        )}
        {activeTab === 'dashboard' && (
          <Dashboard
            metrics={metrics}
            orders={orders}
            inventory={inventory}
            onNavigateTab={setActiveTab}
          />
        )}
        {activeTab === 'orders' && <OrdersPage orders={orders} />}
        {activeTab === 'inventory' && <InventoryPage inventory={inventory} />}
        {activeTab === 'customers' && <CustomersPage customers={customers} />}
        {activeTab === 'approvals' && (
          <ApprovalCenter approvals={approvals} onRefresh={loadData} />
        )}
        {activeTab === 'analytics' && <AnalyticsPage metrics={metrics} />}
      </main>
    </div>
  );
}

export default App;
