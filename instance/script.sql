-- Author table
CREATE TABLE IF NOT EXISTS `author` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `first_name` VARCHAR(50),
  `last_name` VARCHAR(50),
  `patronymic` VARCHAR(50),
  `birth_year` VARCHAR(10),
  `country` VARCHAR(45)
);

-- Genre table
CREATE TABLE IF NOT EXISTS `genre` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `genre_type` VARCHAR(45),
  `name` VARCHAR(45)
);

-- Book table
CREATE TABLE IF NOT EXISTS `book` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `isbn` VARCHAR(250),
  `name` VARCHAR(250),
  `year` VARCHAR(10),
  `quantity` INTEGER,
  `author_id` INTEGER NOT NULL,
  `genre_id` INTEGER NOT NULL,
  `publishing_house` VARCHAR(100),
  FOREIGN KEY (`author_id`) REFERENCES `author` (`id`),
  FOREIGN KEY (`genre_id`) REFERENCES `genre` (`id`)
);

-- Debiting act table
CREATE TABLE IF NOT EXISTS `debiting_act` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `date` TIMESTAMP,
  `quantity` INTEGER,
  `commentary` VARCHAR(250),
  `book_id` INTEGER NOT NULL,
  FOREIGN KEY (`book_id`) REFERENCES `book` (`id`)
);

-- Employee table
CREATE TABLE IF NOT EXISTS `employee` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `first_name` VARCHAR(50),
  `last_name` VARCHAR(50),
  `patronymic` VARCHAR(50),
  `position` VARCHAR(50),
  `login` VARCHAR(250),
  `password` VARCHAR(250)
);

-- Order request table
CREATE TABLE IF NOT EXISTS `order_request` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `date` TIMESTAMP,
  `quantity` INTEGER,
  `book_id` INTEGER NOT NULL,
  `employee_id` INTEGER NOT NULL,
  FOREIGN KEY (`book_id`) REFERENCES `book` (`id`),
  FOREIGN KEY (`employee_id`) REFERENCES `employee` (`id`)
);

-- Supplier table
CREATE TABLE IF NOT EXISTS `supplier` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `name` VARCHAR(250),
  `contact` VARCHAR(250),
  `contact_person` VARCHAR(250)
);

-- Lading bill table
CREATE TABLE IF NOT EXISTS `lading_bill` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `date` TIMESTAMP,
  `book_id` INTEGER NOT NULL,
  `order_request_id` INTEGER NOT NULL,
  `supplier_id` INTEGER NOT NULL,
  FOREIGN KEY (`book_id`) REFERENCES `book` (`id`),
  FOREIGN KEY (`order_request_id`) REFERENCES `order_request` (`id`),
  FOREIGN KEY (`supplier_id`) REFERENCES `supplier` (`id`)
);

-- Reader table
CREATE TABLE IF NOT EXISTS `reader` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `ticket_number` VARCHAR(30) UNIQUE,
  `first_name` VARCHAR(50),
  `last_name` VARCHAR(50),
  `patronymic` VARCHAR(50),
  `date_birth` TIMESTAMP,
  `address` VARCHAR(250),
  `email` VARCHAR(250),
  `phone` VARCHAR(50),
  `registered_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `status` VARCHAR(20) DEFAULT 'ACTIVE',
  `penalty_points` INT DEFAULT 0
);

-- Given book table
CREATE TABLE IF NOT EXISTS `given_book` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `quantity` INTEGER,
  `given_date` TIMESTAMP,
  `return_date` TIMESTAMP,
  `return_date_fact` TIMESTAMP,
  `reader_id` INTEGER NOT NULL,
  `employee_id` INTEGER NOT NULL,
  `book_id` INTEGER NOT NULL,
  FOREIGN KEY (`reader_id`) REFERENCES `reader` (`id`),
  FOREIGN KEY (`employee_id`) REFERENCES `employee` (`id`),
  FOREIGN KEY (`book_id`) REFERENCES `book` (`id`)
);

CREATE TABLE IF NOT EXISTS `system_settings` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `standart_rental_period` INTEGER NOT NULL,
  `max_books_per_reader` INTEGER NOT NULL,
  `late_return_penalty` INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS `reader_penalty_history` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `reader_id` INTEGER NOT NULL,
  `delta_points` INTEGER NOT NULL,
  `reason` VARCHAR(30) NOT NULL,
  `commentary` VARCHAR(250),
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `employee_id` INTEGER,
  FOREIGN KEY (`reader_id`) REFERENCES `reader` (`id`),
  FOREIGN KEY (`employee_id`) REFERENCES `employee` (`id`)
);

CREATE TABLE IF NOT EXISTS `reader_action_history` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `reader_id` INTEGER NOT NULL,
  `action_type` VARCHAR(50) NOT NULL,
  `details` VARCHAR(500),
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `employee_id` INTEGER,
  FOREIGN KEY (`reader_id`) REFERENCES `reader` (`id`),
  FOREIGN KEY (`employee_id`) REFERENCES `employee` (`id`)
);
