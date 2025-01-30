CREATE DATABASE IF NOT EXISTS db_productos;
USE db_productos;

CREATE TABLE productos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    price DECIMAL(10,2) NOT NULL, 
    stock INT NOT NULL,
    description VARCHAR(100) NOT NULL
);
