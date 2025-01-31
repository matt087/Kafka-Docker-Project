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
    'availability-request',
    'update-products-request',
    bootstrap_servers='kafka:9092',
    group_id='servicio-productos',
    value_deserializer=lambda v: json.loads(v.decode('utf-8')),
    auto_offset_reset='earliest' 
)

def consume_requests():
    for message in consumer: 
        response = message.value
        correlation_id = response.get('correlation_id')
        productos = response.get('producto_id', [])
        cantidades = response.get('cantidad', [])
        if message.topic == 'availability-request':
            valid = True
            for i in range (len(productos)):
                valid = valid and verificar_stock(int(productos[i]), int(cantidades[i]))
                if not valid:
                    break
            producer.send('availability-response', value = {"correlation_id":correlation_id,
                                                        "valid":valid})
        elif message.topic == 'update-products-request':
            done = True
            for i in range (len(productos)):
                done = done and actualizar_stock(int(productos[i]), int(cantidades[i]))
                if not done:
                    break
            producer.send('update-products-response', value = {"correlation_id":correlation_id,
                                                        "done":done})
                
                

threading.Thread(target=consume_requests, daemon=True).start()

def verificar_stock(producto_id, cantidad):
    try:
        conexion = mysql.connector.connect(**db_config)
        cursor = conexion.cursor()
        consulta = "SELECT stock FROM productos WHERE id = %s"
        cursor.execute(consulta, (producto_id,))
        resultado = cursor.fetchone()
        if resultado:
            stock = resultado[0]  
            if cantidad <= stock:
                return True
            else:
                return False
        else:
            return False
    except mysql.connector.Error as error:
        print(f"Error al conectarse a la base de datos: {error}")
        return False
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conexion' in locals() and conexion.is_connected():
            conexion.close()

def actualizar_stock(producto_id, cantidad_a_restar):
    try:
        conexion = mysql.connector.connect(**db_config)
        cursor = conexion.cursor()
        consulta_stock = "SELECT stock FROM productos WHERE id = %s"
        cursor.execute(consulta_stock, (producto_id,))
        resultado = cursor.fetchone()
        if resultado:
            stock_actual = resultado[0]  
            if stock_actual >= cantidad_a_restar:
                nuevo_stock = stock_actual - cantidad_a_restar
                consulta_update = "UPDATE productos SET stock = %s WHERE id = %s"
                cursor.execute(consulta_update, (nuevo_stock, producto_id))
                conexion.commit()
                return True
            else:
                return False
        else:
            return False
    except mysql.connector.Error as error:
        return False
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conexion' in locals() and conexion.is_connected():
            conexion.close()

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

@app.route('/add-products', methods=['POST'])
def insertar_producto():
    data = request.json
    if not all(k in data for k in ("name", "price", "stock", "description")):
        return jsonify({"error": "Faltan datos"}), 400

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        query = "INSERT INTO productos (name, price, stock, description) VALUES (%s, %s, %s, %s)"
        values = (data["name"], data["price"], data["stock"], data["description"])

        cursor.execute(query, values)
        conn.commit()

        return jsonify({"message": "Producto insertado correctamente", "id": cursor.lastrowid}), 201

    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500

    finally:
        cursor.close()
        conn.close()      

if __name__ == "__main__":
    app.run(port=5000, host='0.0.0.0')
