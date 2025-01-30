from flask import Flask, request, jsonify
import mysql.connector
from kafka import KafkaProducer, KafkaConsumer
import json
import threading
import uuid
import os

app = Flask(__name__)

db_config = {
    'user': 'root',
    'password': 'contra1',
    'host': 'db_productos',
    'database': 'db_productos',
    'port': '3306'
}

producer = KafkaProducer(
    bootstrap_servers='kafka:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

consumer = KafkaConsumer(
    'availability-response',
    bootstrap_servers='kafka:9092',
    group_id='booking-service',
    value_deserializer=lambda v: json.loads(v.decode('utf-8')),
    auto_offset_reset='earliest' 
)

pending_responses = {}

def consume_requests():
    for message in consumer: 
        response = message.value
        correlation_id = response.get('correlation_id')
        if message.topic == 'room-id-request':
            print("a")
        elif message.topic == 'availability-response':
                correlation_id = response.get("correlation_id")
                pending_responses[correlation_id] = response

threading.Thread(target=consume_requests, daemon=True).start()

@app.route('/list-products', methods=['GET'])
def getProducts():
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)  
        cursor.execute("SELECT * FROM productos")
        productos = cursor.fetchall()
        cursor.close()
        connection.close()
        return jsonify(productos)
    except Exception as e:
        return jsonify({"error": str(e)}), 500  
         
if __name__ == "__main__":
    app.run(port=5000, host='0.0.0.0')
