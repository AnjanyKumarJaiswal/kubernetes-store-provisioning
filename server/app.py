from flask import Flask, jsonify
from flask_cors import CORS
import os
import logging
from dotenv import load_dotenv

load_dotenv()

from routes.list_store import list_stores
from routes.create_store import create_store, simulate_ready
from routes.get_store import get_store, get_store_status, delete_store
from integrations.store_provisioner import get_provisioner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)


@app.route("/", methods=["GET"])
def health_check():
    return {"message": "Urumi Kubernetes Server is running", "status": "healthy"}


@app.route("/api/cluster/health", methods=["GET"])
def cluster_health():
    try:
        provisioner = get_provisioner()
        health = provisioner.check_cluster_health()
        return jsonify(health), 200
    except Exception as e:
        return jsonify({
            "kubernetes": {"connected": False, "error": str(e)},
            "helm": {"connected": False},
            "healthy": False
        }), 200


@app.route("/api/stores", methods=["GET"])
def handle_list_stores():
    return list_stores()


@app.route("/api/stores", methods=["POST"])
def handle_create_store():
    return create_store()


@app.route("/api/stores/<name>", methods=["GET"])
def handle_get_store(name):
    return get_store(name)


@app.route("/api/stores/<name>", methods=["DELETE"])
def handle_delete_store(name):
    return delete_store(name)


@app.route("/api/stores/<name>/status", methods=["GET"])
def handle_get_store_status(name):
    return get_store_status(name)


@app.route("/api/stores/<name>/simulate-ready", methods=["POST"])
def handle_simulate_ready(name):
    return simulate_ready(name)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    
    print(f"\n  Urumi Kubernetes Server running on http://localhost:{port}")
    print(f"  Endpoints:")
    print(f"    GET  /api/stores              - List all stores")
    print(f"    POST /api/stores              - Create a new store")
    print(f"    GET  /api/stores/<name>       - Get store details")
    print(f"    DELETE /api/stores/<name>     - Delete a store")
    print(f"    GET  /api/stores/<name>/status - Check store status")
    print(f"    GET  /api/cluster/health      - Check K8s + Helm health\n")
    
    app.run(host="0.0.0.0", port=port, debug=debug)