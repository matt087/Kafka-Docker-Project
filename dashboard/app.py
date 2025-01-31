from flask import Flask, request, jsonify
import mysql.connector
from kafka import KafkaProducer, KafkaConsumer
import json
import threading
import uuid

app = Flask(__name__)

producer = KafkaProducer(
    bootstrap_servers='kafka:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

consumer = KafkaConsumer(
    'room-id-response',  
    'room-price-response',  
    bootstrap_servers='kafka:9092',
    group_id='payment-service',
    value_deserializer=lambda v: json.loads(v.decode('utf-8')),
    auto_offset_reset='earliest' 
)

def consumeRequests():
    while True:
        msg = consumer.poll(1)
        if not msg:
            continue
        try:
            response = msg.value
            
        except Exception as e:
            print(f"Error: {e}")