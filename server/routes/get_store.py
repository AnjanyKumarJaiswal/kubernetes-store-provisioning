from flask import jsonify
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import stores_db


async def get_store(name):
    normalized_name = name.lower().replace(" ", "-")
    
    if normalized_name not in stores_db:
        return jsonify({"error": f"Store '{normalized_name}' not found"}), 404
    
    return jsonify(stores_db[normalized_name]), 200


async def get_store_status(name):
    normalized_name = name.lower().replace(" ", "-")
    
    if normalized_name not in stores_db:
        return jsonify({"error": f"Store '{normalized_name}' not found"}), 404
    
    store = stores_db[normalized_name]
    
    return jsonify({
        "name": store["name"],
        "status": store["status"],
        "url": store["url"]
    }), 200


async def delete_store(name):
    normalized_name = name.lower().replace(" ", "-")
    
    if normalized_name not in stores_db:
        return jsonify({"error": f"Store '{normalized_name}' not found"}), 404
    
    deleted_store = stores_db.pop(normalized_name)
    
    return jsonify({
        "message": f"Store '{normalized_name}' deleted successfully",
        "store": deleted_store
    }), 200
