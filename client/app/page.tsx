"use client";

import { useState, useEffect, useCallback } from "react";
import Sidebar from "./components/Sidebar";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000";

interface Store {
  id: string;
  name: string;
  type: "woocommerce";
  status: "provisioning" | "ready" | "failed";
  url: string | null;
  createdAt: string;
}

export default function Dashboard() {
  const [stores, setStores] = useState<Store[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newStoreName, setNewStoreName] = useState("");
  const [newStoreType, setNewStoreType] = useState<"woocommerce">("woocommerce");
  const [isLoading, setIsLoading] = useState(false);
  const [isFetching, setIsFetching] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [deletingStores, setDeletingStores] = useState<Set<string>>(new Set());

  const fetchStores = useCallback(async (showLoader = false) => {
    if (showLoader) setIsFetching(true);
    try {
      const res = await fetch(`${API_BASE}/api/stores`);
      if (!res.ok) throw new Error(`Failed to fetch stores (${res.status})`);
      const data = await res.json();
      const storeList: Store[] = Array.isArray(data) ? data : data.stores || [];
      setStores(storeList);
      setError(null);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to connect to server";
      setError(message);
    } finally {
      setIsFetching(false);
    }
  }, []);

  useEffect(() => {
    fetchStores(true);
  }, [fetchStores]);

  useEffect(() => {
    const hasProvisioning = stores.some((s) => s.status === "provisioning");
    if (!hasProvisioning) return;

    const interval = setInterval(() => {
      fetchStores(false);
    }, 5000);

    return () => clearInterval(interval);
  }, [stores, fetchStores]);

  const handleCreateStore = async () => {
    if (!newStoreName.trim()) return;

    setIsLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API_BASE}/api/stores`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newStoreName.trim(),
          type: newStoreType,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || `Failed to create store (${res.status})`);
      }

      setNewStoreName("");
      setNewStoreType("woocommerce");
      setIsModalOpen(false);

      await fetchStores(false);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to create store";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteStore = async (name: string) => {
    setDeletingStores((prev) => new Set(prev).add(name));
    setError(null);

    try {
      const res = await fetch(`${API_BASE}/api/stores/${name}`, {
        method: "DELETE",
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || `Failed to delete store (${res.status})`);
      }

      await fetchStores(false);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to delete store";
      setError(message);
    } finally {
      setDeletingStores((prev) => {
        const next = new Set(prev);
        next.delete(name);
        return next;
      });
    }
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
      <main className={`main-content ${!sidebarOpen ? "sidebar-closed" : ""}`}>
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
            <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
              <button
                className="btn btn-secondary"
                style={{ padding: "8px 14px", fontSize: "13px" }}
                onClick={() => fetchStores(true)}
                disabled={isFetching}
              >
                {isFetching ? "Refreshing..." : "↻ Refresh"}
              </button>
              <button className="btn btn-primary" onClick={() => setIsModalOpen(true)}>
                + New Store
              </button>
            </div>
          </div>
        </header>

        {error && (
          <div
            style={{
              padding: "12px 16px",
              marginBottom: "20px",
              background: "rgba(239, 68, 68, 0.1)",
              border: "1px solid rgba(239, 68, 68, 0.3)",
              borderRadius: "8px",
              color: "#ef4444",
              fontSize: "14px",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <span>{error}</span>
            <button
              onClick={() => setError(null)}
              style={{
                background: "none",
                border: "none",
                color: "#ef4444",
                cursor: "pointer",
                fontSize: "18px",
                padding: "0 4px",
              }}
            >
              ×
            </button>
          </div>
        )}

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: "16px",
            marginBottom: "32px",
          }}
        >
          <div className="card">
            <p
              style={{
                fontSize: "12px",
                color: "#737373",
                marginBottom: "4px",
                textTransform: "uppercase",
                letterSpacing: "0.05em",
              }}
            >
              Total Stores
            </p>
            <p style={{ fontSize: "28px", fontWeight: "600" }}>{stores.length}</p>
          </div>
          <div className="card">
            <p
              style={{
                fontSize: "12px",
                color: "#737373",
                marginBottom: "4px",
                textTransform: "uppercase",
                letterSpacing: "0.05em",
              }}
            >
              Ready
            </p>
            <p style={{ fontSize: "28px", fontWeight: "600", color: "#22c55e" }}>
              {stores.filter((s) => s.status === "ready").length}
            </p>
          </div>
          <div className="card">
            <p
              style={{
                fontSize: "12px",
                color: "#737373",
                marginBottom: "4px",
                textTransform: "uppercase",
                letterSpacing: "0.05em",
              }}
            >
              Provisioning
            </p>
            <p style={{ fontSize: "28px", fontWeight: "600", color: "#eab308" }}>
              {stores.filter((s) => s.status === "provisioning").length}
            </p>
          </div>
          <div className="card">
            <p
              style={{
                fontSize: "12px",
                color: "#737373",
                marginBottom: "4px",
                textTransform: "uppercase",
                letterSpacing: "0.05em",
              }}
            >
              Failed
            </p>
            <p style={{ fontSize: "28px", fontWeight: "600", color: "#ef4444" }}>
              {stores.filter((s) => s.status === "failed").length}
            </p>
          </div>
        </div>

        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <div
            style={{
              padding: "16px 20px",
              borderBottom: "1px solid #2a2a2a",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <h2 style={{ fontSize: "16px", fontWeight: "600" }}>All Stores</h2>
            {stores.some((s) => s.status === "provisioning") && (
              <span style={{ fontSize: "12px", color: "#eab308" }}>● Auto-refreshing...</span>
            )}
          </div>

          {isFetching && stores.length === 0 ? (
            <div className="empty-state">
              <p className="empty-state-title">Loading stores...</p>
              <p className="empty-state-description">Connecting to server</p>
            </div>
          ) : stores.length === 0 ? (
            <div className="empty-state">
              <p className="empty-state-title">No stores yet</p>
              <p className="empty-state-description">Create your first store to get started</p>
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
                          <a
                            href={store.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="link"
                          >
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
                          onClick={() => handleDeleteStore(store.name)}
                          disabled={deletingStores.has(store.name)}
                        >
                          {deletingStores.has(store.name) ? "..." : "Delete"}
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
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && newStoreName.trim()) handleCreateStore();
                  }}
                  autoFocus
                />
              </div>

              <div className="form-group">
                <label className="form-label">Store Type</label>
                <select
                  className="form-select"
                  value={newStoreType}
                  disabled
                  onChange={(e) => {}}
                >
                  <option value="woocommerce">WooCommerce</option>
                </select>
              </div>

              <div style={{ display: "flex", gap: "12px", marginTop: "24px" }}>
                <button
                  className="btn btn-secondary"
                  style={{ flex: 1 }}
                  onClick={() => setIsModalOpen(false)}
                  disabled={isLoading}
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
