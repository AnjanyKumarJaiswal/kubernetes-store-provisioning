from flask import request, jsonify
from datetime import datetime
import uuid
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import stores_db


async def create_store():
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "Request body is required"}), 400
    
    name = data.get("name")
    store_type = data.get("type")
    
    if not name:
        return jsonify({"error": "Store name is required"}), 400
    
    if not store_type:
        return jsonify({"error": "Store type is required"}), 400
    
    if store_type not in ["woocommerce", "medusa"]:
        return jsonify({"error": "Store type must be 'woocommerce' or 'medusa'"}), 400
    
    normalized_name = name.lower().replace(" ", "-")
    
    if normalized_name in stores_db:
        return jsonify({"error": f"Store '{normalized_name}' already exists"}), 409
    
    store_id = str(uuid.uuid4())
    store = {
        "id": store_id,
        "name": normalized_name,
        "type": store_type,
        "status": "provisioning",
        "url": None,
        "createdAt": datetime.utcnow().isoformat() + "Z"
    }
    
    stores_db[normalized_name] = store
    
    return jsonify(store), 201


async def simulate_ready(name):
    normalized_name = name.lower().replace(" ", "-")
    
    if normalized_name not in stores_db:
        return jsonify({"error": f"Store '{normalized_name}' not found"}), 404
    
    stores_db[normalized_name]["status"] = "ready"
    stores_db[normalized_name]["url"] = f"http://{normalized_name}.local"
    
    return jsonify(stores_db[normalized_name]), 200
