# WooCommerce Store Provisioning Platform

A Kubernetes-native platform for provisioning isolated, production-ready WooCommerce stores on demand. Designed to run locally (Minikube/Kind) and in production (VPS/k3s) with minimal configuration changes.

## Features

*   **One-Click Provisioning**: Automated deployment of WordPress + WooCommerce stores.
*   **Full Isolation**: Each store runs in its own implementation of a Kubernetes Namespace.
*   **Resource Management**: Strict ResourceQuota and LimitRange per namespace to prevent noisy neighbors.
*   **Persistent Storage**: Dedicated PVCs for database and WordPress content.
*   **Automated Setup**: A Kubernetes Job handles WordPress installation, theme setup (Storefront), and WooCommerce configuration automatically.
*   **Production Ready**: Helm-based architecture supports values-local.yaml and values-prod.yaml for environment-specific configs.

---

## Provisioning Workflow

The system follows a strict sequence of operations to ensure reliable store creation:

1.  **User Request**: 
    *   User clicks "Create Store" on the Dashboard.
    *   Frontend sends a POST request to `/api/stores` with store name and type.

2.  **API Orchestration**:
    *   Backend validates the request and checks for existing stores.
    *   A background thread is spawned to handle provisioning asynchronously.
    *   Status is updated to `Provisioning`.

3.  **Helm Deployment**:
    *   The backend executes `helm install` using the `woocommerce-store` chart.
    *   It creates a new Namespace: `store-<store_name>`.
    *   It applies ResourceQuotas and LimitRanges to the namespace.
    *   It deploys MySQL (StatefulSet-like Deployment with PVC).
    *   It deploys WordPress (Deployment with PVC), configured to connect to the MySQL service.

4.  **Store Setup (Kubernetes Job)**:
    *   A `setup-job` pod is launched alongside the main application.
    *   **Init Container**: Waits for the main WordPress container to be healthy and responsive.
    *   **Main Container**: 
        *   Installs `wp-cli`.
        *   Installs WordPress Core.
        *   Installs and activates WooCommerce plugin.
        *   Installs and activates Storefront theme.
        *   Generates default pages (Shop, Cart, Checkout, My Account).
        *   Configures permalinks and menus.
        *   (Optional) Creates sample products.

5.  **Completion**:
    *   Once the Job completes successfully, the store is fully functional.
    *   Backend polling detects the Helm release status.
    *   Dashboard updates status to `Ready` and displays the store URL.

---

## Prerequisites

*   **Docker Desktop** (or any container runtime)
*   **Kubernetes Cluster** (Minikube, Kind, or specific K8s setup)
    *   *Recommendation*: Minikube with Ingress addon enabled (`minikube addons enable ingress`)
*   **Helm 3+**
*   **Python 3.9+** (for the backend API)
*   **Node.js 18+** & **pnpm** (for the frontend dashboard)

---

## Local Setup Instructions

### 1. Start Kubernetes & Enable Ingress
Ensure your local cluster is running and Ingress is enabled.
```bash
minikube start
minikube addons enable ingress
```

### 2. Backend Setup
Navigate to the server directory, install dependencies, and start the Flask API.
```bash
cd server
python -m venv venv
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
python app.py
```
*The backend runs on `http://localhost:5000`.*

### 3. Frontend Setup
Navigate to the client directory and start the Next.js dashboard.
```bash
cd client
pnpm install
pnpm run dev
```
*The dashboard runs on `http://localhost:3000`.*

---

## How to Use

1.  **Open Dashboard**: Go to `http://localhost:3000`.
2.  **Create Store**: Click **"Create New Store"**.
    *   Enter a unique store name (e.g., `fashion-shop`).
    *   Select "WooCommerce".
    *   Click "Create".
3.  **Monitor Status**: The dashboard will show the status changing from `Provisioning` -> `Ready`.
4.  **Access Store**:
    *   Once `Ready`, a "Visit Store" link appears.
    *   **Important**: On local Minikube, you must add the ingress host to your `/etc/hosts` (Mac/Linux) or `C:\Windows\System32\drivers\etc\hosts` (Windows).
    *   Example: `127.0.0.1  fashion-shop.localhost` (or the Minikube IP provided by `minikube ip`).
5.  **Place Order**:
    *   Visit the store URL.
    *   Add the "Test Product" to your cart.
    *   Proceed to checkout and place an order using "Cash on Delivery".

---

## Production / VPS Setup (k3s)

This platform is designed to be deployed to a VPS running a lightweight Kubernetes distribution like **k3s**.

### Steps to Deploy on VPS:
1.  **Install k3s**:
    ```bash
    curl -sfL https://get.k3s.io | sh -
    ```
2.  **Configure Helm**: Point Helm to the k3s cluster configuration (`/etc/rancher/k3s/k3s.yaml`).
3.  **Update Configuration**:
    *   Edit `server/helm-charts/woocommerce-store/values-prod.yaml`.
    *   Set `global.domain` to your actual domain (e.g., `provisioner.example.com`).
    *   Update `storageClass` if using a specific provider (k3s `local-path` works by default).
4.  **Run Backend**: Deploy the Flask app as a Deployment or Systemd service on the VPS.
5.  **Run Frontend**: Build and serve the Next.js app or deploy via Vercel/Netlify pointing to the VPS backend API.

The provisioning logic remains identical—Helm simply applies the `values-prod.yaml` overrides securely.

---

## System Design & Tradeoffs

### Architecture Choice
*   **Helm for Orchestration**: We chose Helm over raw manifests or Kustomize because it allows easy parameterization (Values files) for different environments (Local vs Prod) and manages complex dependencies (Deployment + Service + Ingress + Secrets) as a single "Release".
*   **Why a "Setup Job"?**: Instead of using `postStart` hooks (which are hard to debug and block container start) or `initContainers` (which run before the app is ready), we use a separate **Kubernetes Job** (`setup-job.yaml`). This Job waits for WordPress to be healthy, then uses `wp-cli` to install WooCommerce, activate the theme, and configure the store. This separates "deployment" from "application logic", making the system more robust and easier to debug.

### Isolation Strategy
*   **Namespace-per-Store**: Each store gets its own namespace (`store-<name>`). This provides the strongest isolation boundary in Kubernetes.
*   **Resource Quotas**: Hard limits on CPU, Memory, and Storage per namespace ensure one store cannot potential starve the entire cluster.
*   **Secrets**: Database credentials and admin passwords are managed as K8s Secrets, not environment variables.

### Tradeoffs
*   **Resource Usage**: Running a dedicated MySQL and WordPress pod for *every* store is resource-heavy. A shared database server with separate logical databases would be more efficient but less isolated.
*   **Provisioning Time**: The setup job takes about 60-90 seconds to complete (installing plugins/themes). Pre-baking a custom Docker image with WooCommerce pre-installed would be faster but less flexible for updates.

---

## Project Structure
*   `client/`: Next.js Dashboard (Frontend)
*   `server/`: Flask API (Backend Resources)
*   `server/helm-charts/`: Helm Charts for provisioning
*   `server/integrations/`: Python modules for K8s/Helm interaction

---
**Author**: Anjany Kumar Jaiswal
