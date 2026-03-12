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

CREATE TABLE IF NOT EXISTS `employee` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `first_name` VARCHAR(50),
  `last_name` VARCHAR(50),
  `patronymic` VARCHAR(50),
  `position` VARCHAR(50),
  `login` VARCHAR(250),
  `password` VARCHAR(250)
);

CREATE TABLE IF NOT EXISTS `reader` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `ticket_number` VARCHAR(30) UNIQUE,
  `first_name` VARCHAR(50),
  `last_name` VARCHAR(50),
  `patronymic` VARCHAR(50),
  `date_birth` TIMESTAMP,
  `address` VARCHAR(250),
  `city` VARCHAR(120),
  `street` VARCHAR(120),
  `house` VARCHAR(20),
  `apartment` VARCHAR(20),
  `email` VARCHAR(250),
  `phone` VARCHAR(50),
  `registered_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `status` VARCHAR(20) DEFAULT 'ACTIVE',
  `penalty_points` INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS `supplier` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `name` VARCHAR(250),
  `contact` VARCHAR(250),
  `contact_person` VARCHAR(250),
  `phone` VARCHAR(40),
  `email` VARCHAR(120),
  `address` VARCHAR(255),
  `commentary` VARCHAR(255),
  `is_active` INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS `system_settings` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `standart_rental_period` INTEGER NOT NULL,
  `max_books_per_reader` INTEGER NOT NULL,
  `late_return_penalty` INTEGER NOT NULL
);

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

CREATE TABLE IF NOT EXISTS `order_request` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `date` TIMESTAMP,
  `quantity` INTEGER,
  `book_id` INTEGER NOT NULL,
  `employee_id` INTEGER NOT NULL,
  FOREIGN KEY (`book_id`) REFERENCES `book` (`id`),
  FOREIGN KEY (`employee_id`) REFERENCES `employee` (`id`)
);

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

CREATE TABLE IF NOT EXISTS `debiting_act` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `date` TIMESTAMP,
  `quantity` INTEGER,
  `commentary` VARCHAR(250),
  `book_id` INTEGER NOT NULL,
  FOREIGN KEY (`book_id`) REFERENCES `book` (`id`)
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

CREATE TABLE IF NOT EXISTS `supplier_contract` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `contract_number` VARCHAR(80) NOT NULL,
  `contract_date` DATE NOT NULL,
  `supplier_id` INTEGER NOT NULL,
  `start_date` DATE,
  `end_date` DATE,
  `terms_note` VARCHAR(255),
  `commentary` VARCHAR(255),
  FOREIGN KEY (`supplier_id`) REFERENCES `supplier` (`id`)
);

CREATE TABLE IF NOT EXISTS `supplier_invoice` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `invoice_number` VARCHAR(80) NOT NULL,
  `invoice_date` DATE NOT NULL,
  `supplier_id` INTEGER NOT NULL,
  `contract_id` INTEGER,
  `employee_id` INTEGER,
  `commentary` VARCHAR(255),
  `total_amount` REAL DEFAULT 0,
  FOREIGN KEY (`supplier_id`) REFERENCES `supplier` (`id`),
  FOREIGN KEY (`contract_id`) REFERENCES `supplier_contract` (`id`),
  FOREIGN KEY (`employee_id`) REFERENCES `employee` (`id`)
);

CREATE TABLE IF NOT EXISTS `supplier_invoice_item` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `invoice_id` INTEGER NOT NULL,
  `book_id` INTEGER NOT NULL,
  `quantity` INTEGER NOT NULL,
  `unit_price` REAL DEFAULT 0,
  FOREIGN KEY (`invoice_id`) REFERENCES `supplier_invoice` (`id`),
  FOREIGN KEY (`book_id`) REFERENCES `book` (`id`)
);

CREATE TABLE IF NOT EXISTS `acceptance_act` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `act_number` VARCHAR(80) NOT NULL,
  `act_date` DATE NOT NULL,
  `supplier_id` INTEGER NOT NULL,
  `contract_id` INTEGER,
  `employee_id` INTEGER,
  `commentary` VARCHAR(255),
  `total_amount` REAL DEFAULT 0,
  `status` VARCHAR(20) DEFAULT 'DRAFT',
  FOREIGN KEY (`supplier_id`) REFERENCES `supplier` (`id`),
  FOREIGN KEY (`contract_id`) REFERENCES `supplier_contract` (`id`),
  FOREIGN KEY (`employee_id`) REFERENCES `employee` (`id`)
);

CREATE TABLE IF NOT EXISTS `acceptance_act_item` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `act_id` INTEGER NOT NULL,
  `book_id` INTEGER NOT NULL,
  `quantity` INTEGER NOT NULL,
  `unit_price` REAL DEFAULT 0,
  FOREIGN KEY (`act_id`) REFERENCES `acceptance_act` (`id`),
  FOREIGN KEY (`book_id`) REFERENCES `book` (`id`)
);

CREATE TABLE IF NOT EXISTS `book_copy` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `inventory_code` VARCHAR(80) UNIQUE,
  `book_id` INTEGER NOT NULL,
  `acceptance_act_id` INTEGER,
  `status` VARCHAR(20) DEFAULT 'AVAILABLE',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`book_id`) REFERENCES `book` (`id`),
  FOREIGN KEY (`acceptance_act_id`) REFERENCES `acceptance_act` (`id`)
);

CREATE TABLE IF NOT EXISTS `write_off_act` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `act_number` VARCHAR(80) NOT NULL,
  `act_date` DATE NOT NULL,
  `basis` VARCHAR(255),
  `employee_id` INTEGER,
  `commentary` VARCHAR(255),
  `status` VARCHAR(20) DEFAULT 'DRAFT',
  FOREIGN KEY (`employee_id`) REFERENCES `employee` (`id`)
);

CREATE TABLE IF NOT EXISTS `write_off_act_item` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `act_id` INTEGER NOT NULL,
  `copy_id` INTEGER NOT NULL,
  `reason` VARCHAR(30) NOT NULL,
  FOREIGN KEY (`act_id`) REFERENCES `write_off_act` (`id`),
  FOREIGN KEY (`copy_id`) REFERENCES `book_copy` (`id`)
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
