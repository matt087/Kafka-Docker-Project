CREATE DATABASE IF NOT EXISTS db_usuarios;
USE db_usuarios;

CREATE TABLE usuarios (
    cedula VARCHAR(10) PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    role INT NOT NULL,
    email VARCHAR(50) NOT NULL,
    password VARCHAR(50) NOT NULL
);

INSERT IGNORE INTO usuarios (cedula, name, role, email, password) 
VALUES ('1725578775', 'Mateo Montenegro', 1, 'admin@gmail.com', '1234');
