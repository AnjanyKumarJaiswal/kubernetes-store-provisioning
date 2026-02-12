import logging
import secrets
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum
import threading
import time

from integrations.kubernetes import KubernetesClient
from integrations.helm_charts import HelmManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StoreStatus(str, Enum):
    PENDING = "pending"
    PROVISIONING = "provisioning"
    READY = "ready"
    FAILED = "failed"
    DELETING = "deleting"
    DELETED = "deleted"


class StoreType(str, Enum):
    WOOCOMMERCE = "woocommerce"


class StoreProvisioner:
    
    def __init__(self, in_cluster: bool = False, domain_suffix: str = ".local", kubeconfig: Optional[str] = None):
        self.k8s = KubernetesClient(in_cluster=in_cluster)
        self.helm = HelmManager(kubeconfig=kubeconfig)
        self.domain_suffix = domain_suffix
        self._stores: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        

        self._sync_stores_from_cluster()

    def _sync_stores_from_cluster(self):
        logger.info("Syncing stores from cluster...")
        try:
            namespaces = self.k8s.list_store_namespaces()
            with self._lock:
                for ns in namespaces:
                    store_name = ns.get("store_name")
                    if not store_name:
                        continue
                    
                    namespace_name = ns.get("name")
                    created_at = ns.get("created_at")
                    

                    releases_result = self.helm.list_releases(namespace=namespace_name)
                    store_type = "unknown"
                    
                    if releases_result.get("success"):
                        for release in releases_result.get("releases", []):
                            chart_name = release.get("chart", "").lower()
                            if "woocommerce" in chart_name or "woo" in release.get("name", ""):
                                store_type = StoreType.WOOCOMMERCE.value
                                break
                    
                    if store_type == "unknown":
                        logger.warning(f"Could not determine store type for {store_name} in {namespace_name}")
                        continue


                    import hashlib
                    store_id = hashlib.md5(store_name.encode()).hexdigest()[:16]
                    store_url = self._generate_store_url(store_name)
                    
                    self._stores[store_name] = {
                        "id": store_id,
                        "name": store_name,
                        "type": store_type,
                        "status": StoreStatus.READY.value,
                        "url": store_url,
                        "namespace": namespace_name,
                        "admin_email": "unknown@example.com",
                        "created_at": created_at,
                        "updated_at": created_at,
                        "error": None,
                        "credentials": None
                    }
                    logger.info(f"Restored store {store_name} ({store_type}) from cluster")
                    
        except Exception as e:
            logger.error(f"Failed to sync stores from cluster: {e}")
    
    def _generate_store_url(self, store_name: str) -> str:
        return f"http://{store_name}{self.domain_suffix}"
    
    def _update_store_status(self, store_name: str, status: StoreStatus, url: Optional[str] = None,
                              error: Optional[str] = None, credentials: Optional[Dict[str, str]] = None) -> None:
        with self._lock:
            if store_name in self._stores:
                self._stores[store_name]["status"] = status.value
                self._stores[store_name]["updated_at"] = datetime.utcnow().isoformat() + "Z"
                
                if url:
                    self._stores[store_name]["url"] = url
                if error:
                    self._stores[store_name]["error"] = error
                if credentials:
                    self._stores[store_name]["credentials"] = credentials
    
    def create_store(self, name: str, store_type: str, admin_email: str = "admin@example.com",
                     async_provision: bool = True) -> Dict[str, Any]:
        normalized_name = name.lower().replace(" ", "-").replace("_", "-")
        
        try:

            if store_type.lower() != "woocommerce":
                return {"success": False, "error": "Only 'woocommerce' store type is supported"}
            store_type_enum = StoreType.WOOCOMMERCE
        except ValueError:
            return {"success": False, "error": f"Invalid store type: {store_type}. Must be 'woocommerce'"}
        
        with self._lock:
            if normalized_name in self._stores:
                existing = self._stores[normalized_name]
                if existing["status"] not in [StoreStatus.DELETED.value, StoreStatus.FAILED.value]:
                    return {"success": False, "error": f"Store '{normalized_name}' already exists"}
        
        store_url = self._generate_store_url(normalized_name)
        namespace = f"store-{normalized_name}"
        
        store_record = {
            "id": secrets.token_hex(8),
            "name": normalized_name,
            "type": store_type_enum.value,
            "status": StoreStatus.PENDING.value,
            "url": None,
            "namespace": namespace,
            "admin_email": admin_email,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "error": None,
            "credentials": None
        }
        
        with self._lock:
            self._stores[normalized_name] = store_record
        
        if async_provision:
            thread = threading.Thread(
                target=self._provision_store,
                args=(normalized_name, store_type_enum, admin_email),
                daemon=True
            )
            thread.start()
        else:
            self._provision_store(normalized_name, store_type_enum, admin_email)
        
        return {"success": True, "store": self._stores[normalized_name].copy()}
    

    def _provision_store(self, store_name: str, store_type: StoreType, admin_email: str) -> None:
        namespace = f"store-{store_name}"
        
        try:
            self._update_store_status(store_name, StoreStatus.PROVISIONING)
            logger.info(f"Starting provisioning for store: {store_name}")
            

            
            ingress_host = f"{store_name}{self.domain_suffix}"
            
            if store_type == StoreType.WOOCOMMERCE:
                logger.info(f"Installing WooCommerce for store: {store_name}")
                helm_result = self.helm.install_woocommerce(
                    store_name=store_name, namespace=namespace, admin_email=admin_email, ingress_host=ingress_host
                )
            else:
                logger.warning(f"Unsupported store type {store_type}, defaulting to WooCommerce")
                helm_result = self.helm.install_woocommerce(
                    store_name=store_name, namespace=namespace, admin_email=admin_email, ingress_host=ingress_host
                )
            
            if not helm_result.get("success"):
                error_msg = helm_result.get("error", "Unknown error")
                if helm_result.get("message"):
                    error_msg = helm_result.get("message")
                raise Exception(f"Failed to install Helm release: {error_msg}")
            
            store_url = f"http://{ingress_host}"
            credentials = helm_result.get("credentials")
            
            self._update_store_status(store_name, StoreStatus.READY, url=store_url, credentials=credentials)
            logger.info(f"Store {store_name} provisioned successfully. URL: {store_url}")
            
        except Exception as e:
            logger.error(f"Failed to provision store {store_name}: {e}")
            self._update_store_status(store_name, StoreStatus.FAILED, error=str(e))
    
    def get_store(self, name: str) -> Optional[Dict[str, Any]]:
        normalized_name = name.lower().replace(" ", "-").replace("_", "-")
        with self._lock:
            store = self._stores.get(normalized_name)
            if store:
                return store.copy()
        return None
    
    def get_store_status(self, name: str) -> Dict[str, Any]:
        normalized_name = name.lower().replace(" ", "-").replace("_", "-")
        store = self.get_store(normalized_name)
        
        if not store:
            return {"success": False, "error": "Store not found"}
        
        if store["status"] in [StoreStatus.PROVISIONING.value, StoreStatus.READY.value]:
            try:
                resources = self.k8s.get_store_resources(normalized_name)
                store["kubernetes_resources"] = resources
            except Exception as e:
                logger.warning(f"Failed to get K8s resources for {normalized_name}: {e}")
        
        return {"success": True, "store": store}
    
    def list_stores(self) -> Dict[str, Any]:
        with self._lock:
            stores = [s.copy() for s in self._stores.values()]
        return {"success": True, "stores": stores, "count": len(stores)}
    
    def delete_store(self, name: str, force: bool = False) -> Dict[str, Any]:
        normalized_name = name.lower().replace(" ", "-").replace("_", "-")
        store = self.get_store(normalized_name)
        
        if not store:
            return {"success": False, "error": "Store not found"}
        
        if store["status"] == StoreStatus.PROVISIONING.value and not force:
            return {"success": False, "error": "Store is still provisioning. Use force=true to delete anyway."}
        
        self._update_store_status(normalized_name, StoreStatus.DELETING)
        
        try:
            namespace = f"store-{normalized_name}"
            
            logger.info(f"Uninstalling Helm release for store: {normalized_name}")
            helm_result = self.helm.uninstall_store(
                store_name=normalized_name, store_type=store["type"], namespace=namespace
            )
            
            if not helm_result.get("success") and not helm_result.get("already_deleted"):
                logger.warning(f"Helm uninstall might have failed: {helm_result}")
            
            logger.info(f"Deleting namespace: {namespace}")
            ns_result = self.k8s.delete_namespace(normalized_name)
            
            if not ns_result.get("success") and not ns_result.get("already_deleted"):
                raise Exception(f"Failed to delete namespace: {ns_result.get('error')}")
            
            self._update_store_status(normalized_name, StoreStatus.DELETED)
            
            with self._lock:
                if normalized_name in self._stores:
                    del self._stores[normalized_name]
            
            logger.info(f"Store {normalized_name} deleted successfully")
            return {"success": True, "message": f"Store '{normalized_name}' deleted successfully"}
            
        except Exception as e:
            logger.error(f"Failed to delete store {normalized_name}: {e}")
            self._update_store_status(normalized_name, StoreStatus.FAILED, error=f"Deletion failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def check_cluster_health(self) -> Dict[str, Any]:
        k8s_status = self.k8s.check_cluster_connection()
        
        try:
            helm_releases = self.helm.list_releases(all_namespaces=True)
            helm_status = {"connected": True, "releases_count": len(helm_releases.get("releases", []))}
        except Exception as e:
            helm_status = {"connected": False, "error": str(e)}
        
        return {
            "kubernetes": k8s_status,
            "helm": helm_status,
            "healthy": k8s_status.get("connected", False) and helm_status.get("connected", False)
        }


_provisioner: Optional[StoreProvisioner] = None


def get_provisioner() -> StoreProvisioner:
    global _provisioner
    
    if _provisioner is None:
        import os
        in_cluster = os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount/token")
        domain_suffix = os.getenv("STORE_DOMAIN_SUFFIX", ".local")
        _provisioner = StoreProvisioner(in_cluster=in_cluster, domain_suffix=domain_suffix)
    
    return _provisioner
