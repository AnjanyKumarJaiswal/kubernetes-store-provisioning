from flask import jsonify
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import stores_db


async def list_stores():
    stores_list = list(stores_db.values())
    return jsonify(stores_list), 200
