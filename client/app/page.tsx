"use client";

import { useState } from "react";
import Sidebar from "./components/Sidebar";

interface Store {
  id: string;
  name: string;
  type: "woocommerce" | "medusa";
  status: "provisioning" | "ready" | "failed";
  url: string | null;
  createdAt: string;
}

const mockStores: Store[] = [
  {
    id: "1",
    name: "my-shop",
    type: "woocommerce",
    status: "ready",
    url: "http://my-shop.local",
    createdAt: "2026-02-07T10:30:00Z",
  },
  {
    id: "2",
    name: "test-store",
    type: "medusa",
    status: "provisioning",
    url: null,
    createdAt: "2026-02-07T11:00:00Z",
  },
  {
    id: "3",
    name: "demo-store",
    type: "woocommerce",
    status: "failed",
    url: null,
    createdAt: "2026-02-07T09:00:00Z",
  },
];

export default function Dashboard() {
  const [stores, setStores] = useState<Store[]>(mockStores);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newStoreName, setNewStoreName] = useState("");
  const [newStoreType, setNewStoreType] = useState<"woocommerce" | "medusa">("woocommerce");
  const [isLoading, setIsLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const handleCreateStore = async () => {
    if (!newStoreName.trim()) return;

    setIsLoading(true);

    const newStore: Store = {
      id: Date.now().toString(),
      name: newStoreName.toLowerCase().replace(/\s+/g, "-"),
      type: newStoreType,
      status: "provisioning",
      url: null,
      createdAt: new Date().toISOString(),
    };

    setStores([...stores, newStore]);
    setNewStoreName("");
    setNewStoreType("woocommerce");
    setIsModalOpen(false);
    setIsLoading(false);
  };

  const handleDeleteStore = async (id: string) => {
    setStores(stores.filter((store) => store.id !== id));
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getStatusBadge = (status: Store["status"]) => {
    const statusClass = `status-badge status-${status}`;
    const labels = {
      ready: "Ready",
      provisioning: "Provisioning",
      failed: "Failed",
    };

    return (
      <span className={statusClass}>
        <span className="status-dot"></span>
        {labels[status]}
      </span>
    );
  };

  return (
    <div className="app-layout">
      <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
      <main className={`main-content ${!sidebarOpen ? 'sidebar-closed' : ''}`}>
        <header style={{ marginBottom: "32px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <h1 style={{ fontSize: "24px", fontWeight: "600", marginBottom: "4px" }}>
                Store Provisioning Dashboard
              </h1>
              <p style={{ fontSize: "14px", color: "#737373" }}>
                Manage and provision your e-commerce stores
              </p>
            </div>
            <button className="btn btn-primary" onClick={() => setIsModalOpen(true)}>
              + New Store
            </button>
          </div>
        </header>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "16px", marginBottom: "32px" }}>
          <div className="card">
            <p style={{ fontSize: "12px", color: "#737373", marginBottom: "4px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Total Stores
            </p>
            <p style={{ fontSize: "28px", fontWeight: "600" }}>{stores.length}</p>
          </div>
          <div className="card">
            <p style={{ fontSize: "12px", color: "#737373", marginBottom: "4px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Ready
            </p>
            <p style={{ fontSize: "28px", fontWeight: "600", color: "#22c55e" }}>
              {stores.filter((s) => s.status === "ready").length}
            </p>
          </div>
          <div className="card">
            <p style={{ fontSize: "12px", color: "#737373", marginBottom: "4px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Provisioning
            </p>
            <p style={{ fontSize: "28px", fontWeight: "600", color: "#eab308" }}>
              {stores.filter((s) => s.status === "provisioning").length}
            </p>
          </div>
          <div className="card">
            <p style={{ fontSize: "12px", color: "#737373", marginBottom: "4px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Failed
            </p>
            <p style={{ fontSize: "28px", fontWeight: "600", color: "#ef4444" }}>
              {stores.filter((s) => s.status === "failed").length}
            </p>
          </div>
        </div>

        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <div style={{ padding: "16px 20px", borderBottom: "1px solid #2a2a2a" }}>
            <h2 style={{ fontSize: "16px", fontWeight: "600" }}>All Stores</h2>
          </div>

          {stores.length === 0 ? (
            <div className="empty-state">
              <p className="empty-state-title">No stores yet</p>
              <p className="empty-state-description">
                Create your first store to get started
              </p>
            </div>
          ) : (
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th>URL</th>
                    <th>Created</th>
                    <th style={{ width: "80px" }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {stores.map((store) => (
                    <tr key={store.id}>
                      <td style={{ fontWeight: "500" }}>{store.name}</td>
                      <td style={{ textTransform: "capitalize" }}>{store.type}</td>
                      <td>{getStatusBadge(store.status)}</td>
                      <td>
                        {store.url ? (
                          <a href={store.url} target="_blank" rel="noopener noreferrer" className="link">
                            {store.url}
                          </a>
                        ) : (
                          <span style={{ color: "#525252" }}>--</span>
                        )}
                      </td>
                      <td style={{ color: "#737373" }}>{formatDate(store.createdAt)}</td>
                      <td>
                        <button
                          className="btn btn-danger"
                          style={{ padding: "6px 12px", fontSize: "12px" }}
                          onClick={() => handleDeleteStore(store.id)}
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {isModalOpen && (
          <div className="modal-overlay" onClick={() => setIsModalOpen(false)}>
            <div className="modal" onClick={(e) => e.stopPropagation()}>
              <h3 className="modal-title">Create New Store</h3>

              <div className="form-group">
                <label className="form-label">Store Name</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="my-awesome-store"
                  value={newStoreName}
                  onChange={(e) => setNewStoreName(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Store Type</label>
                <select
                  className="form-select"
                  value={newStoreType}
                  onChange={(e) => setNewStoreType(e.target.value as "woocommerce" | "medusa")}
                >
                  <option value="woocommerce">WooCommerce</option>
                  <option value="medusa">MedusaJS</option>
                </select>
              </div>

              <div style={{ display: "flex", gap: "12px", marginTop: "24px" }}>
                <button
                  className="btn btn-secondary"
                  style={{ flex: 1 }}
                  onClick={() => setIsModalOpen(false)}
                >
                  Cancel
                </button>
                <button
                  className="btn btn-primary"
                  style={{ flex: 1 }}
                  onClick={handleCreateStore}
                  disabled={isLoading || !newStoreName.trim()}
                >
                  {isLoading ? "Creating..." : "Create Store"}
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
