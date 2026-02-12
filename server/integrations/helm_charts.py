import subprocess
import json
import logging
import os
from typing import Optional, Dict, Any, List
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CHARTS_DIR = Path(__file__).parent.parent / "helm-charts"


class HelmManager:
    
    def __init__(self, kubeconfig: Optional[str] = None):
        self.kubeconfig = kubeconfig
        self._verify_helm_installed()
    
    def _verify_helm_installed(self) -> None:
        try:
            result = subprocess.run(["helm", "version", "--short"], capture_output=True, text=True, check=True)
            logger.info(f"Helm version: {result.stdout.strip()}")
        except FileNotFoundError:
            logger.error("Helm CLI not found. Please install Helm first.")
            raise RuntimeError("Helm CLI is not installed")
        except subprocess.CalledProcessError as e:
            logger.error(f"Helm version check failed: {e.stderr}")
            raise
    
    def _parse_timeout(self, timeout_str: str) -> int:
        timeout_str = timeout_str.strip()
        if timeout_str.endswith("m"):
            return int(timeout_str[:-1]) * 60 + 60
        elif timeout_str.endswith("s"):
            return int(timeout_str[:-1]) + 30
        elif timeout_str.endswith("h"):
            return int(timeout_str[:-1]) * 3600 + 60
        return 600
    
    def _run_helm_command(self, args: List[str], timeout: int = 300) -> Dict[str, Any]:
        cmd = ["helm"] + args
        
        if self.kubeconfig:
            cmd.extend(["--kubeconfig", self.kubeconfig])
        
        logger.info(f"Running Helm command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=True)
            return {"success": True, "output": result.stdout, "stderr": result.stderr}
        except subprocess.CalledProcessError as e:
            logger.error(f"Helm command failed: {e.stderr}")
            return {"success": False, "error": e.stderr, "output": e.stdout}
        except subprocess.TimeoutExpired:
            logger.error("Helm command timed out")
            return {"success": False, "error": "Command timed out"}
    
    def install_release(self, release_name: str, chart: str, namespace: str,
                        values: Optional[Dict[str, Any]] = None, values_file: Optional[str] = None,
                        wait: bool = True, timeout: str = "10m", create_namespace: bool = True) -> Dict[str, Any]:
        args = ["install", release_name, chart, "--namespace", namespace, "--timeout", timeout]
        
        if create_namespace:
            args.append("--create-namespace")
        if wait:
            args.append("--wait")
        if values_file:
            args.extend(["-f", values_file])
        if values:
            for key, value in values.items():
                args.extend(["--set", f"{key}={value}"])
        
        subprocess_timeout = self._parse_timeout(timeout)
        result = self._run_helm_command(args, timeout=subprocess_timeout)
        if result["success"]:
            logger.info(f"Successfully installed release {release_name}")
        return result
    
    def upgrade_release(self, release_name: str, chart: str, namespace: str,
                        values: Optional[Dict[str, Any]] = None, values_file: Optional[str] = None,
                        wait: bool = True, timeout: str = "10m", install: bool = True) -> Dict[str, Any]:
        args = ["upgrade", release_name, chart, "--namespace", namespace, "--timeout", timeout]
        
        if install:
            args.append("--install")
        if wait:
            args.append("--wait")
        if values_file:
            args.extend(["-f", values_file])
        if values:
            for key, value in values.items():
                args.extend(["--set", f"{key}={value}"])
        
        subprocess_timeout = self._parse_timeout(timeout)
        result = self._run_helm_command(args, timeout=subprocess_timeout)
        if result["success"]:
            logger.info(f"Successfully upgraded release {release_name}")
        return result
    
    def uninstall_release(self, release_name: str, namespace: str, wait: bool = True) -> Dict[str, Any]:
        args = ["uninstall", release_name, "--namespace", namespace]
        
        if wait:
            args.append("--wait")
        
        result = self._run_helm_command(args)
        
        if result["success"]:
            logger.info(f"Successfully uninstalled release {release_name}")
        elif "not found" in result.get("error", "").lower():
            logger.info(f"Release {release_name} not found (already deleted)")
            return {"success": True, "already_deleted": True}
        
        return result
    
    def get_release_status(self, release_name: str, namespace: str) -> Dict[str, Any]:
        args = ["status", release_name, "--namespace", namespace, "--output", "json"]
        result = self._run_helm_command(args)
        
        if result["success"]:
            try:
                status_data = json.loads(result["output"])
                return {
                    "success": True,
                    "name": status_data.get("name"),
                    "namespace": status_data.get("namespace"),
                    "status": status_data.get("info", {}).get("status"),
                    "version": status_data.get("version"),
                    "app_version": status_data.get("chart", {}).get("metadata", {}).get("appVersion"),
                    "last_deployed": status_data.get("info", {}).get("last_deployed")
                }
            except json.JSONDecodeError:
                return {"success": True, "raw_output": result["output"]}
        else:
            if "not found" in result.get("error", "").lower():
                return {"success": False, "error": "release_not_found"}
            return result
    
    def list_releases(self, namespace: Optional[str] = None, all_namespaces: bool = False) -> Dict[str, Any]:
        args = ["list", "--output", "json"]
        
        if all_namespaces:
            args.append("--all-namespaces")
        elif namespace:
            args.extend(["--namespace", namespace])
        
        result = self._run_helm_command(args)
        
        if result["success"]:
            try:
                releases = json.loads(result["output"])
                return {
                    "success": True,
                    "releases": [
                        {
                            "name": r.get("name"),
                            "namespace": r.get("namespace"),
                            "status": r.get("status"),
                            "chart": r.get("chart"),
                            "app_version": r.get("app_version")
                        }
                        for r in releases
                    ]
                }
            except json.JSONDecodeError:
                return {"success": True, "releases": []}
        return result
    
    def add_repo(self, name: str, url: str) -> Dict[str, Any]:
        result = self._run_helm_command(["repo", "add", name, url])
        
        if not result["success"] and "already exists" in result.get("error", ""):
            logger.info(f"Repository {name} already exists, updating...")
            return self._run_helm_command(["repo", "update"])
        return result
    
    def update_repos(self) -> Dict[str, Any]:
        return self._run_helm_command(["repo", "update"])
    
    def install_woocommerce(self, store_name: str, namespace: str, admin_user: str = "admin",
                            admin_password: str = None, admin_email: str = "admin@example.com",
                            site_title: str = "My Store", persistence_size: str = "5Gi",
                            db_password: str = None, ingress_host: str = None,
                            values_file: str = None) -> Dict[str, Any]:
        import secrets
        
        if not admin_password:
            admin_password = secrets.token_urlsafe(16)
        if not db_password:
            db_password = secrets.token_urlsafe(16)
        if not ingress_host:
            ingress_host = f"{store_name}.local"
        
        woo_chart_path = CHARTS_DIR / "woocommerce-store"
        
        if not woo_chart_path.exists():
            logger.error("WooCommerce chart not found at: %s", woo_chart_path)
            return {
                "success": False,
                "error": "woocommerce_chart_not_found",
                "message": f"Please create a WooCommerce Helm chart at {woo_chart_path}"
            }
        
        if not values_file:
            local_values = woo_chart_path / "values-local.yaml"
            if local_values.exists():
                values_file = str(local_values)
        
        values = {
            "wordpress.adminUser": admin_user,
            "wordpress.adminPassword": admin_password,
            "wordpress.adminEmail": admin_email,
            "wordpress.siteTitle": site_title,
            "wordpress.persistence.size": persistence_size,
            "mariadb.auth.rootPassword": db_password,
            "mariadb.auth.password": db_password,
            "ingress.host": ingress_host
        }
        
        release_name = f"woo-{store_name}"
        
        result = self.install_release(
            release_name=release_name,
            chart=str(woo_chart_path),
            namespace=namespace,
            values=values,
            values_file=values_file,
            wait=True,
            timeout="15m"
        )
        
        if result["success"]:
            result["credentials"] = {
                "admin_user": admin_user,
                "admin_password": admin_password,
                "db_password": db_password,
                "ingress_host": ingress_host
            }
        
        return result
    

    
    def uninstall_store(self, store_name: str, store_type: str, namespace: str) -> Dict[str, Any]:
        if store_type == "woocommerce":
            release_name = f"woo-{store_name}"
        else:

            release_name = f"woo-{store_name}"
        
        return self.uninstall_release(release_name, namespace)
