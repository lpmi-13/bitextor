
/*
CREATE DATABASE paracrawl;
CREATE USER 'paracrawl_user'@'localhost' IDENTIFIED BY 'paracrawl_password';
GRANT ALL PRIVILEGES ON paracrawl.* TO 'paracrawl_user'@'localhost';

mysql -u paracrawl_user -pparacrawl_password -Dparacrawl
*/

DROP TABLE IF EXISTS document;
DROP TABLE IF EXISTS url;

CREATE TABLE IF NOT EXISTS document
(
    id INT AUTO_INCREMENT PRIMARY KEY,
    lang CHAR(2),
    md5 VARCHAR(32) UNIQUE KEY
);

CREATE TABLE IF NOT EXISTS url
(
    id INT AUTO_INCREMENT PRIMARY KEY,
    val VARCHAR(255) UNIQUE KEY,
    document_id INT REFERENCES document(id)
);

CREATE TABLE IF NOT EXISTS link
(
    id INT AUTO_INCREMENT PRIMARY KEY,
    text VARCHAR(255),
    hover VARCHAR(255),
    image_url VARCHAR(255),
    url_id INT REFERENCES url(id)
);

CREATE TABLE IF NOT EXISTS document_align
(
    id INT AUTO_INCREMENT PRIMARY KEY,
    document1 INT REFERENCES document(id),
    document2 INT REFERENCES document(id),
    score FLOAT
);

