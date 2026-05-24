CREATE DATABASE IF NOT EXISTS a3_learning
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'a3'@'127.0.0.1' IDENTIFIED BY 'replace_with_a_strong_password';
CREATE USER IF NOT EXISTS 'a3'@'localhost' IDENTIFIED BY 'replace_with_a_strong_password';

GRANT ALL PRIVILEGES ON a3_learning.* TO 'a3'@'127.0.0.1';
GRANT ALL PRIVILEGES ON a3_learning.* TO 'a3'@'localhost';

FLUSH PRIVILEGES;
