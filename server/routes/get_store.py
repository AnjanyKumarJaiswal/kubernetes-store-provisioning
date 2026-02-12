from flask import jsonify
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


def get_store(name):
    try:
        provisioner = get_provisioner()
    except Exception as e:
        return jsonify({"error": "Kubernetes cluster is not connected."}), 503

    store = provisioner.get_store(name)
    if not store:
        return jsonify({"error": f"Store '{name}' not found"}), 404

    return jsonify(format_store(store)), 200


def get_store_status(name):
    try:
        provisioner = get_provisioner()
    except Exception as e:
        return jsonify({"error": "Kubernetes cluster is not connected."}), 503

    result = provisioner.get_store_status(name)

    if not result.get("success"):
        return jsonify({"error": result.get("error", "Store not found")}), 404

    store = result["store"]
    response = {
        "name": store.get("name"),
        "status": store.get("status"),
        "url": store.get("url"),
    }

    if "kubernetes_resources" in store:
        response["kubernetesResources"] = store["kubernetes_resources"]

    return jsonify(response), 200


def delete_store(name):
    try:
        provisioner = get_provisioner()
    except Exception as e:
        return jsonify({"error": "Kubernetes cluster is not connected."}), 503

    result = provisioner.delete_store(name)

    if not result.get("success"):
        error_msg = result.get("error", "Failed to delete store")
        status_code = 404 if "not found" in error_msg.lower() else 500
        return jsonify({"error": error_msg}), status_code

    return jsonify({
        "message": result.get("message", f"Store '{name}' deleted successfully"),
    }), 200
