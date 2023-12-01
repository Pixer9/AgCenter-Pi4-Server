--Database for 'AgCenter'
--user: admin
--password: T@rleton123
--host: localhost

--Temperature/Humidity Sensor ENS160
CREATE TABLE TEMP_AHT21 (
    ID int NOT NULL AUTO_INCREMENT,
    Node it NOT NULL,
    DT datetime NOT NULL,
    temperature decimal(12, 6),
    relative_humidity decimal(12, 6),
    PRIMARY KEY(ID)
);

--CO2 Sensor ENS160
CREATE TABLE CO2_ENS160 (
    ID int NOT NULL AUTO_INCREMENT,
    Node int NOT NULL,
    DT datetime NOT NULL,
    AQI int,
    TVOC int,
    eCO2 int,
    PRIMARY KEY(ID)
);

--RGB Sensor TCS34725
CREATE TABLE RGB_TCS34725 (
    ID int NOT NULL AUTO_INCREMENT,
    Node int NOT NULL,
    DT datetime NOT NULL,
    color int,
    color_temperature int,
    lux decimal(12, 6),
    PRIMARY KEY(ID)
);

--UV/Light Intensity LTR390
CREATE TABLE UV_LTR390 (
    ID int NOT NULL AUTO_INCREMENT,
    Node int NOT NULL,
    DT datetime NOT NULL,
    uvi decimal(12, 6),
    lux decimal(12, 6),
    light int,
    uvs decimal(12, 6),
    PRIMARY KEY(ID)
);

--IR Sensor MLX90614
CREATE TABLE IR_MLX90614 (
    ID int NOT NULL AUTO_INCREMENT,
    Node int NOT NULL,
    DT datetime NOT NULL,
    ambient_temperature decimal(12, 6),
    object_temperature decimal(12, 6),
    PRIMARY KEY(ID)
);

--TDS Sensor
CREATE TABLE TDS_Meter (
    ID int NOT NULL AUTO_INCREMENT,
    Node into NOT NULL,
    DT datetime NOT NULL,
    raw_value decimal(12, 6),
    raw_voltage decimal(12, 6),
    PPM int,
    PRIMARY KEY(ID)
);

--Turbidity Sensor
CREATE TABLE Turbidity_Meter (
    ID int NOT NULL AUTO_INCREMENT,
    Node int NOT NULL,
    DT datetime NOT NULL,
    raw_value decimal(12, 6),
    raw_voltage decimal(12, 6),
    PRIMARY KEY(ID)
);

--pH Sensor
CREATE TABLE PH_Meter (
    ID int NOT NULL AUTO_INCREMENT,
    Node int NOT NULL,
    DT datetime NOT NULL,
    raw_value decimal(12, 6),
    raw_voltage decimal(12, 6),
    PRIMARY KEY(ID)
);
