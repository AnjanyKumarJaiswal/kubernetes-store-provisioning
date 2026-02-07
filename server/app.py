from flask import Flask
from flask_cors import CORS
import os

from routes.list_store import list_stores
from routes.create_store import create_store, simulate_ready
from routes.get_store import get_store, get_store_status, delete_store

app = Flask(__name__)
CORS(app)


@app.route("/", methods=["GET"])
async def health_check():
    return {"message": "Urumi Kubernetes Server is running", "status": "healthy"}


@app.route("/api/stores", methods=["GET"])
async def handle_list_stores():
    return await list_stores()


@app.route("/api/stores", methods=["POST"])
async def handle_create_store():
    return await create_store()


@app.route("/api/stores/<name>", methods=["GET"])
async def handle_get_store(name):
    return await get_store(name)


@app.route("/api/stores/<name>", methods=["DELETE"])
async def handle_delete_store(name):
    return await delete_store(name)


@app.route("/api/stores/<name>/status", methods=["GET"])
async def handle_get_store_status(name):
    return await get_store_status(name)


@app.route("/api/stores/<name>/simulate-ready", methods=["POST"])
async def handle_simulate_ready(name):
    return await simulate_ready(name)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    
    print(f"\n  Urumi Kubernetes Server running on http://localhost:{port}")
    print(f"  Endpoints:")
    print(f"    GET  /api/stores           - List all stores")
    print(f"    POST /api/stores           - Create a new store")
    print(f"    GET  /api/stores/<name>    - Get store details")
    print(f"    DELETE /api/stores/<name>  - Delete a store")
    print(f"    GET  /api/stores/<name>/status - Check store status\n")
    
    app.run(host="0.0.0.0", port=port, debug=debug)