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


def list_stores():
    try:
        provisioner = get_provisioner()
    except Exception as e:
        logger.error(f"Failed to initialize provisioner: {e}")
        return jsonify([]), 200

    result = provisioner.list_stores()
    stores = [format_store(s) for s in result.get("stores", [])]
    return jsonify(stores), 200
