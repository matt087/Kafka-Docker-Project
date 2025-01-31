from flask import Flask, request, jsonify
import mysql.connector
from kafka import KafkaProducer, KafkaConsumer
import json
import threading
import uuid

app = Flask(__name__)

db_config = {
    'user': 'root',
    'password': 'contra1',
    'host': 'db_pedidos',  
    'database': 'db_pedidos',
    'port': '3306'
}

producer = KafkaProducer(
    bootstrap_servers='kafka:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

consumer = KafkaConsumer(
    'availability-response',
    bootstrap_servers='kafka:9092',
    group_id='servicio-pedidos',
    value_deserializer=lambda v: json.loads(v.decode('utf-8')),
    auto_offset_reset='earliest' 
)

pending_responses = {}

def consume_requests():
    for message in consumer:
        response = message.value
        correlation_id = response.get('correlation_id')
        if message.topic == 'availability-response':
            pending_responses[correlation_id] = response

threading.Thread(target=consume_requests, daemon=True).start()

@app.route('/list-pedidos', methods=['GET'])
def getProducts():
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)  
        cursor.execute("SELECT * FROM pedidos")
        productos = cursor.fetchall()
        cursor.close()
        connection.close()
        return jsonify(productos)
    except Exception as e:
        return jsonify({"error": str(e)}), 500 
    
@app.route('/list-pedidos-extend', methods=['GET'])
def getPedidosExtend():
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)  
        cursor.execute("SELECT * FROM pedido_detalles")
        productos = cursor.fetchall()
        cursor.close()
        connection.close()
        return jsonify(productos)
    except Exception as e:
        return jsonify({"error": str(e)}), 500     
    
@app.route('/add-pedido', methods=['POST'])
def add_pedido():
    data = request.json

    if not all(k in data for k in ("sucursal", "producto_id", "cantidad", "subtotal")):
        return jsonify({"error": "Faltan datos requeridos"}), 400
    
    if len(data["producto_id"]) != len(data["cantidad"]):
        return jsonify({"error": "Los arrays de producto_id y cantidad deben tener la misma longitud"}), 400
    
    productos = data['producto_id']
    cantidades = data['cantidad']
    correlation_id = str(uuid.uuid4())
    pending_responses[correlation_id] = None
    producer.send('availability-request', value = {"correlation_id":correlation_id,
                                                    "producto_id":productos, "cantidad":cantidades})
    while True:
        if pending_responses[correlation_id] is not None:
            response = pending_responses.pop(correlation_id)
            break
    if response["valid"]:
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            
            pedido_query = "INSERT INTO pedidos (sucursal) VALUES (%s)"
            cursor.execute(pedido_query, (data["sucursal"],))
            pedido_id = cursor.lastrowid
            
            detalle_query = """
                INSERT INTO pedido_detalles 
                (pedido_id, producto_id, cantidad, subtotal) 
                VALUES (%s, %s, %s, %s)
            """
            
            cursor.execute(detalle_query, (
                pedido_id,
                json.dumps(data["producto_id"]),  
                json.dumps(data["cantidad"]),      
                data["subtotal"]
            ))
            
            conn.commit()
            producer.send('update-products-request', value={"correlation_id":correlation_id,
                                            "producto_id":productos, "cantidad":cantidades})
            return jsonify({
                "message": "Pedido creado correctamente",
                "pedido_id": pedido_id
            }), 201     
        except mysql.connector.Error as err:
            return jsonify({"error": str(err)}), 500
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()
    else:
        return jsonify({"message": "No se puede proceder con el pedido"}), 500 

if __name__ == "__main__":
    app.run(port=5000, host='0.0.0.0')