
/*
CREATE USER 'paracrawl_user'@'localhost' IDENTIFIED BY 'paracrawl_password';

CREATE DATABASE paracrawl CHARACTER SET 'utf8' COLLATE 'utf8_unicode_ci';
GRANT ALL PRIVILEGES ON paracrawl.* TO 'paracrawl_user'@'localhost';

mysql -u paracrawl_user -pparacrawl_password -Dparacrawl < create.sql
*/

DROP TABLE IF EXISTS document;
DROP TABLE IF EXISTS url;
DROP TABLE IF EXISTS link;
DROP TABLE IF EXISTS document_align;

CREATE TABLE IF NOT EXISTS document
(
    id INT AUTO_INCREMENT PRIMARY KEY,
    mime VARCHAR(255),
    lang CHAR(2),
    md5 VARCHAR(32) UNIQUE KEY
);

CREATE TABLE IF NOT EXISTS url
(
    id INT AUTO_INCREMENT PRIMARY KEY,
    val VARCHAR(1024) UNIQUE KEY,
    document_id INT REFERENCES document(id)
);

CREATE TABLE IF NOT EXISTS link
(
    id INT AUTO_INCREMENT PRIMARY KEY,
    text VARCHAR(255),
    hover VARCHAR(255),
    image_url VARCHAR(255),
    document_id INT REFERENCES document(id),
    url_id INT REFERENCES url(id)
);

CREATE TABLE IF NOT EXISTS document_align
(
    id INT AUTO_INCREMENT PRIMARY KEY,
    document1 INT REFERENCES document(id),
    document2 INT REFERENCES document(id),
    score FLOAT
);

