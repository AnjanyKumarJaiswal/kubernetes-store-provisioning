from flask import request, jsonify
from integrations.store_provisioner import get_provisioner
import logging

logger = logging.getLogger(__name__)


def format_store(store):
    return {
        "id": store.get("id"),
        "name": store.get("name"),
        "type": store.get("type"),
        "status": store.get("status"),
        "url": store.get("url"),
        "createdAt": store.get("created_at"),
        "namespace": store.get("namespace"),
        "error": store.get("error"),
    }


def create_store():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body is required"}), 400

    name = data.get("name")

    store_type = data.get("type", "woocommerce")

    if not name:
        return jsonify({"error": "Store name is required"}), 400


    if store_type != "woocommerce":
         return jsonify({"error": "Only 'woocommerce' store type is currently supported"}), 400

    try:
        provisioner = get_provisioner()
    except Exception as e:
        logger.error(f"Failed to initialize provisioner: {e}")
        return jsonify({"error": "Kubernetes cluster is not connected. Please start Minikube and try again."}), 503

    result = provisioner.create_store(
        name=name,
        store_type=store_type,
        admin_email=data.get("adminEmail", "admin@example.com"),
        async_provision=True
    )

    if not result.get("success"):
        error_msg = result.get("error", "Failed to create store")
        status_code = 409 if "already exists" in error_msg.lower() else 500
        return jsonify({"error": error_msg}), status_code

    store = format_store(result["store"])
    return jsonify(store), 201


def simulate_ready(name):
    try:
        provisioner = get_provisioner()
    except Exception as e:
        return jsonify({"error": "Kubernetes cluster is not connected."}), 503

    normalized = name.lower().replace(" ", "-").replace("_", "-")
    store = provisioner.get_store(normalized)
    if not store:
        return jsonify({"error": f"Store '{name}' not found"}), 404

    from integrations.store_provisioner import StoreStatus
    provisioner._update_store_status(
        normalized,
        StoreStatus.READY,
        url=f"http://{normalized}.local"
    )

    updated_store = provisioner.get_store(normalized)
    return jsonify(format_store(updated_store)), 200
