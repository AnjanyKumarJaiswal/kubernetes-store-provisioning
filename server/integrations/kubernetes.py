from kubernetes import client, config
from kubernetes.client.rest import ApiException
from typing import Optional, Dict, Any, List
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KubernetesClient:
    
    def __init__(self, in_cluster: bool = False):
        try:
            if in_cluster:
                config.load_incluster_config()
            else:
                config.load_kube_config()
        except Exception as e:
            logger.warning(f"Failed to load standard Kubernetes configuration: {e}")
            # If we don't have an override, we must raise
            if not os.getenv("KUBERNETES_API_BASE_URL"):
                raise

        # Check for manual API URL override
        api_url = os.getenv("KUBERNETES_API_BASE_URL")
        if api_url:
            logger.info(f"Overriding Kubernetes API URL with {api_url}")
            configuration = client.Configuration.get_default_copy()
            configuration.host = api_url

            # For local development with self-signed certs
            if "localhost" in api_url or "127.0.0.1" in api_url:
                configuration.verify_ssl = False

            client.Configuration.set_default(configuration)
        
        self.core_api = client.CoreV1Api()
        self.apps_api = client.AppsV1Api()
        self.networking_api = client.NetworkingV1Api()
        self.custom_api = client.CustomObjectsApi()
    
    def create_namespace(self, name: str, labels: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        namespace_name = f"store-{name}"
        
        default_labels = {
            "app.kubernetes.io/managed-by": "store-provisioning-platform",
            "store-name": name,
            "purpose": "ecommerce-store"
        }
        
        if labels:
            default_labels.update(labels)
        
        namespace = client.V1Namespace(
            metadata=client.V1ObjectMeta(
                name=namespace_name,
                labels=default_labels
            )
        )
        
        try:
            result = self.core_api.create_namespace(body=namespace)
            return {"success": True, "namespace": namespace_name, "uid": result.metadata.uid}
        except ApiException as e:
            if e.status == 409:
                return {"success": True, "namespace": namespace_name, "already_exists": True}
            logger.error(f"Failed to create namespace {namespace_name}: {e}")
            return {"success": False, "error": str(e)}
    
    def delete_namespace(self, name: str) -> Dict[str, Any]:
        namespace_name = f"store-{name}"
        
        try:
            self.core_api.delete_namespace(
                name=namespace_name,
                body=client.V1DeleteOptions(propagation_policy="Foreground")
            )
            return {"success": True, "namespace": namespace_name}
        except ApiException as e:
            if e.status == 404:
                return {"success": True, "namespace": namespace_name, "already_deleted": True}
            logger.error(f"Failed to delete namespace {namespace_name}: {e}")
            return {"success": False, "error": str(e)}
    
    def get_namespace(self, name: str) -> Optional[Dict[str, Any]]:
        namespace_name = f"store-{name}"
        
        try:
            ns = self.core_api.read_namespace(name=namespace_name)
            return {
                "name": ns.metadata.name,
                "status": ns.status.phase,
                "created_at": ns.metadata.creation_timestamp.isoformat(),
                "labels": ns.metadata.labels
            }
        except ApiException as e:
            if e.status == 404:
                return None
            raise
    
    def create_secret(self, name: str, namespace: str, data: Dict[str, str], secret_type: str = "Opaque") -> Dict[str, Any]:
        import base64
        
        encoded_data = {
            key: base64.b64encode(value.encode()).decode()
            for key, value in data.items()
        }
        
        secret = client.V1Secret(
            metadata=client.V1ObjectMeta(
                name=name,
                namespace=namespace,
                labels={"app.kubernetes.io/managed-by": "store-provisioning-platform"}
            ),
            type=secret_type,
            data=encoded_data
        )
        
        try:
            self.core_api.create_namespaced_secret(namespace=namespace, body=secret)
            return {"success": True, "secret": name}
        except ApiException as e:
            if e.status == 409:
                self.core_api.replace_namespaced_secret(name=name, namespace=namespace, body=secret)
                return {"success": True, "secret": name, "updated": True}
            logger.error(f"Failed to create secret {name}: {e}")
            return {"success": False, "error": str(e)}
    
    def create_pvc(self, name: str, namespace: str, storage_size: str = "5Gi", 
                   storage_class: Optional[str] = None, access_modes: List[str] = None) -> Dict[str, Any]:
        if access_modes is None:
            access_modes = ["ReadWriteOnce"]
        
        pvc = client.V1PersistentVolumeClaim(
            metadata=client.V1ObjectMeta(
                name=name,
                namespace=namespace,
                labels={"app.kubernetes.io/managed-by": "store-provisioning-platform"}
            ),
            spec=client.V1PersistentVolumeClaimSpec(
                access_modes=access_modes,
                storage_class_name=storage_class,
                resources=client.V1ResourceRequirements(requests={"storage": storage_size})
            )
        )
        
        try:
            self.core_api.create_namespaced_persistent_volume_claim(namespace=namespace, body=pvc)
            return {"success": True, "pvc": name, "size": storage_size}
        except ApiException as e:
            if e.status == 409:
                return {"success": True, "pvc": name, "already_exists": True}
            logger.error(f"Failed to create PVC {name}: {e}")
            return {"success": False, "error": str(e)}
    
    def create_deployment(self, name: str, namespace: str, image: str, replicas: int = 1,
                          ports: List[int] = None, env_vars: Dict[str, str] = None,
                          env_from_secrets: List[str] = None, volume_mounts: List[Dict[str, str]] = None,
                          pvc_name: Optional[str] = None, resources: Optional[Dict[str, Dict[str, str]]] = None) -> Dict[str, Any]:
        if ports is None:
            ports = [80]
        
        env = []
        if env_vars:
            env = [client.V1EnvVar(name=key, value=value) for key, value in env_vars.items()]
        
        env_from = []
        if env_from_secrets:
            env_from = [client.V1EnvFromSource(secret_ref=client.V1SecretEnvSource(name=secret_name)) 
                        for secret_name in env_from_secrets]
        
        container_ports = [client.V1ContainerPort(container_port=port) for port in ports]
        
        volumes = []
        container_volume_mounts = []
        
        if pvc_name:
            volumes.append(client.V1Volume(
                name="data-volume",
                persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(claim_name=pvc_name)
            ))
            container_volume_mounts.append(client.V1VolumeMount(name="data-volume", mount_path="/var/lib/data"))
        
        resource_requirements = None
        if resources:
            resource_requirements = client.V1ResourceRequirements(
                requests=resources.get("requests", {}),
                limits=resources.get("limits", {})
            )
        
        container = client.V1Container(
            name=name,
            image=image,
            ports=container_ports,
            env=env if env else None,
            env_from=env_from if env_from else None,
            volume_mounts=container_volume_mounts if container_volume_mounts else None,
            resources=resource_requirements,
            liveness_probe=client.V1Probe(
                http_get=client.V1HTTPGetAction(path="/", port=ports[0]),
                initial_delay_seconds=30,
                period_seconds=10
            ),
            readiness_probe=client.V1Probe(
                http_get=client.V1HTTPGetAction(path="/", port=ports[0]),
                initial_delay_seconds=5,
                period_seconds=5
            )
        )
        
        deployment = client.V1Deployment(
            metadata=client.V1ObjectMeta(
                name=name,
                namespace=namespace,
                labels={"app": name, "app.kubernetes.io/managed-by": "store-provisioning-platform"}
            ),
            spec=client.V1DeploymentSpec(
                replicas=replicas,
                selector=client.V1LabelSelector(match_labels={"app": name}),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(labels={"app": name}),
                    spec=client.V1PodSpec(
                        containers=[container],
                        volumes=volumes if volumes else None
                    )
                )
            )
        )
        
        try:
            self.apps_api.create_namespaced_deployment(namespace=namespace, body=deployment)
            return {"success": True, "deployment": name}
        except ApiException as e:
            if e.status == 409:
                return {"success": True, "deployment": name, "already_exists": True}
            logger.error(f"Failed to create deployment {name}: {e}")
            return {"success": False, "error": str(e)}
    
    def get_deployment_status(self, name: str, namespace: str) -> Dict[str, Any]:
        namespace_name = f"store-{namespace}" if not namespace.startswith("store-") else namespace
        
        try:
            deployment = self.apps_api.read_namespaced_deployment_status(name=name, namespace=namespace_name)
            status = deployment.status
            return {
                "name": name,
                "replicas": status.replicas or 0,
                "ready_replicas": status.ready_replicas or 0,
                "available_replicas": status.available_replicas or 0,
                "is_ready": (status.ready_replicas or 0) >= (deployment.spec.replicas or 1)
            }
        except ApiException as e:
            if e.status == 404:
                return {"name": name, "error": "not_found"}
            raise
    
    def create_service(self, name: str, namespace: str, ports: List[Dict[str, int]],
                       selector: Dict[str, str], service_type: str = "ClusterIP") -> Dict[str, Any]:
        service_ports = [
            client.V1ServicePort(
                port=p.get("port", 80),
                target_port=p.get("target_port", p.get("port", 80)),
                name=p.get("name", f"port-{p.get('port', 80)}")
            )
            for p in ports
        ]
        
        service = client.V1Service(
            metadata=client.V1ObjectMeta(
                name=name,
                namespace=namespace,
                labels={"app.kubernetes.io/managed-by": "store-provisioning-platform"}
            ),
            spec=client.V1ServiceSpec(type=service_type, ports=service_ports, selector=selector)
        )
        
        try:
            result = self.core_api.create_namespaced_service(namespace=namespace, body=service)
            return {"success": True, "service": name, "cluster_ip": result.spec.cluster_ip}
        except ApiException as e:
            if e.status == 409:
                existing = self.core_api.read_namespaced_service(name=name, namespace=namespace)
                return {"success": True, "service": name, "cluster_ip": existing.spec.cluster_ip, "already_exists": True}
            logger.error(f"Failed to create service {name}: {e}")
            return {"success": False, "error": str(e)}
    
    def get_service_url(self, service_name: str, namespace: str) -> Optional[str]:
        try:
            # Minikube Check reverted as per user request
            # api_host = self.core_api.api_client.configuration.host
            # is_local = "127.0.0.1" in api_host or "localhost" in api_host
            
            # if is_local:
            #     ... (code removed) ...

            svc = self.core_api.read_namespaced_service(name=service_name, namespace=namespace)
            svc_type = svc.spec.type
            
            if svc_type == "NodePort" and svc.spec.ports:
                node_port = svc.spec.ports[0].node_port
                if node_port:
                    return f"http://127.0.0.1:{node_port}"
            
            if svc_type == "LoadBalancer":
                # For basic LB support
                if svc.status.load_balancer and svc.status.load_balancer.ingress:
                    ingress_list = svc.status.load_balancer.ingress
                    host = ingress_list[0].ip or ingress_list[0].hostname
                    port = svc.spec.ports[0].port if svc.spec.ports else 80
                    return f"http://{host}:{port}"
            
            if svc_type == "ClusterIP" and svc.spec.cluster_ip:
                 # Standard internal URL (not useful for external access typically but fallback)
                port = svc.spec.ports[0].port if svc.spec.ports else 80
                return f"http://{svc.spec.cluster_ip}:{port}"
            
            return None
        except ApiException as e:
            logger.error(f"Failed to get service URL for {service_name}: {e}")
            return None
    
    def create_ingress(self, name: str, namespace: str, host: str, service_name: str,
                       service_port: int = 80, tls_enabled: bool = False,
                       tls_secret_name: Optional[str] = None, annotations: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        default_annotations = {
            "kubernetes.io/ingress.class": "nginx",
            "nginx.ingress.kubernetes.io/proxy-body-size": "50m"
        }
        
        if annotations:
            default_annotations.update(annotations)
        
        ingress_rule = client.V1IngressRule(
            host=host,
            http=client.V1HTTPIngressRuleValue(
                paths=[
                    client.V1HTTPIngressPath(
                        path="/",
                        path_type="Prefix",
                        backend=client.V1IngressBackend(
                            service=client.V1IngressServiceBackend(
                                name=service_name,
                                port=client.V1ServiceBackendPort(number=service_port)
                            )
                        )
                    )
                ]
            )
        )
        
        tls = None
        if tls_enabled and tls_secret_name:
            tls = [client.V1IngressTLS(hosts=[host], secret_name=tls_secret_name)]
        
        ingress = client.V1Ingress(
            metadata=client.V1ObjectMeta(
                name=name,
                namespace=namespace,
                labels={"app.kubernetes.io/managed-by": "store-provisioning-platform"},
                annotations=default_annotations
            ),
            spec=client.V1IngressSpec(rules=[ingress_rule], tls=tls)
        )
        
        try:
            self.networking_api.create_namespaced_ingress(namespace=namespace, body=ingress)
            return {"success": True, "ingress": name, "host": host}
        except ApiException as e:
            if e.status == 409:
                return {"success": True, "ingress": name, "host": host, "already_exists": True}
            logger.error(f"Failed to create ingress {name}: {e}")
            return {"success": False, "error": str(e)}
    
    def create_resource_quota(self, namespace: str, cpu_limit: str = "4", memory_limit: str = "8Gi",
                              pvc_limit: str = "20Gi", max_pods: int = 20) -> Dict[str, Any]:
        quota = client.V1ResourceQuota(
            metadata=client.V1ObjectMeta(name="store-quota", namespace=namespace),
            spec=client.V1ResourceQuotaSpec(
                hard={
                    "limits.cpu": cpu_limit,
                    "limits.memory": memory_limit,
                    "requests.storage": pvc_limit,
                    "pods": str(max_pods)
                }
            )
        )
        
        try:
            self.core_api.create_namespaced_resource_quota(namespace=namespace, body=quota)
            return {"success": True, "namespace": namespace}
        except ApiException as e:
            if e.status == 409:
                return {"success": True, "namespace": namespace, "already_exists": True}
            logger.error(f"Failed to create resource quota: {e}")
            return {"success": False, "error": str(e)}
    
    def list_store_namespaces(self) -> List[Dict[str, Any]]:
        try:
            namespaces = self.core_api.list_namespace(
                label_selector="app.kubernetes.io/managed-by=store-provisioning-platform"
            )
            return [
                {
                    "name": ns.metadata.name,
                    "store_name": ns.metadata.labels.get("store-name"),
                    "status": ns.status.phase,
                    "created_at": ns.metadata.creation_timestamp.isoformat()
                }
                for ns in namespaces.items
            ]
        except ApiException as e:
            logger.error(f"Failed to list namespaces: {e}")
            return []
    
    def get_store_resources(self, store_name: str) -> Dict[str, Any]:
        namespace = f"store-{store_name}"
        
        try:
            deployments = self.apps_api.list_namespaced_deployment(namespace=namespace)
            services = self.core_api.list_namespaced_service(namespace=namespace)
            ingresses = self.networking_api.list_namespaced_ingress(namespace=namespace)
            pvcs = self.core_api.list_namespaced_persistent_volume_claim(namespace=namespace)
            
            return {
                "namespace": namespace,
                "deployments": [d.metadata.name for d in deployments.items],
                "services": [s.metadata.name for s in services.items],
                "ingresses": [i.metadata.name for i in ingresses.items],
                "pvcs": [p.metadata.name for p in pvcs.items]
            }
        except ApiException as e:
            if e.status == 404:
                return {"namespace": namespace, "error": "namespace_not_found"}
            raise
    
    def check_cluster_connection(self) -> Dict[str, Any]:
        try:
            version = client.VersionApi().get_code()
            return {
                "connected": True,
                "kubernetes_version": version.git_version,
                "platform": version.platform
            }
        except Exception as e:
            logger.error(f"Failed to connect to Kubernetes cluster: {e}")
            return {"connected": False, "error": str(e)}
