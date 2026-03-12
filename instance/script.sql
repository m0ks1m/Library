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

-- Book card table
CREATE TABLE IF NOT EXISTS `book` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `isbn` VARCHAR(250),
  `name` VARCHAR(250),
  `year` VARCHAR(10),
  `quantity` INTEGER DEFAULT 0,
  `author_id` INTEGER NOT NULL,
  `genre_id` INTEGER NOT NULL,
  `publishing_house` VARCHAR(100),
  `description` TEXT,
  FOREIGN KEY (`author_id`) REFERENCES `author` (`id`),
  FOREIGN KEY (`genre_id`) REFERENCES `genre` (`id`)
);

-- Physical copies
CREATE TABLE IF NOT EXISTS `book_copy` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `copy_uid` VARCHAR(64) UNIQUE NOT NULL,
  `book_id` INTEGER NOT NULL,
  `status` VARCHAR(30) NOT NULL DEFAULT 'доступна',
  `arrival_date` TIMESTAMP,
  `source_type` VARCHAR(40),
  `source_id` INTEGER,
  `note` TEXT,
  FOREIGN KEY (`book_id`) REFERENCES `book` (`id`)
);

-- Debiting act (legacy)
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

-- Supplier table
CREATE TABLE IF NOT EXISTS `supplier` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `name` VARCHAR(250),
  `contact_person` VARCHAR(250),
  `phone` VARCHAR(50),
  `email` VARCHAR(250),
  `address` VARCHAR(250),
  `comment` TEXT,
  `is_active` INTEGER DEFAULT 1
);

-- Contracts
CREATE TABLE IF NOT EXISTS `supplier_contract` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `contract_number` VARCHAR(100) UNIQUE NOT NULL,
  `signed_date` DATE,
  `supplier_id` INTEGER NOT NULL,
  `start_date` DATE,
  `end_date` DATE,
  `terms` TEXT,
  `comment` TEXT,
  FOREIGN KEY (`supplier_id`) REFERENCES `supplier` (`id`)
);

-- Invoice header
CREATE TABLE IF NOT EXISTS `invoice` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `invoice_number` VARCHAR(100) UNIQUE NOT NULL,
  `date` DATE,
  `supplier_id` INTEGER NOT NULL,
  `contract_id` INTEGER,
  `employee_id` INTEGER,
  `comment` TEXT,
  FOREIGN KEY (`supplier_id`) REFERENCES `supplier` (`id`),
  FOREIGN KEY (`contract_id`) REFERENCES `supplier_contract` (`id`),
  FOREIGN KEY (`employee_id`) REFERENCES `employee` (`id`)
);

-- Invoice items
CREATE TABLE IF NOT EXISTS `invoice_item` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `invoice_id` INTEGER NOT NULL,
  `book_id` INTEGER NOT NULL,
  `quantity` INTEGER NOT NULL,
  `price` REAL DEFAULT 0,
  FOREIGN KEY (`invoice_id`) REFERENCES `invoice` (`id`),
  FOREIGN KEY (`book_id`) REFERENCES `book` (`id`)
);

-- Acceptance act
CREATE TABLE IF NOT EXISTS `acceptance_act` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `act_number` VARCHAR(100) UNIQUE NOT NULL,
  `date` DATE,
  `supplier_id` INTEGER NOT NULL,
  `contract_id` INTEGER,
  `employee_id` INTEGER,
  `comment` TEXT,
  `confirmed` INTEGER DEFAULT 0,
  FOREIGN KEY (`supplier_id`) REFERENCES `supplier` (`id`),
  FOREIGN KEY (`contract_id`) REFERENCES `supplier_contract` (`id`),
  FOREIGN KEY (`employee_id`) REFERENCES `employee` (`id`)
);

-- Acceptance items
CREATE TABLE IF NOT EXISTS `acceptance_item` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `act_id` INTEGER NOT NULL,
  `book_id` INTEGER NOT NULL,
  `quantity` INTEGER NOT NULL,
  `price` REAL DEFAULT 0,
  FOREIGN KEY (`act_id`) REFERENCES `acceptance_act` (`id`),
  FOREIGN KEY (`book_id`) REFERENCES `book` (`id`)
);

-- Writeoff act
CREATE TABLE IF NOT EXISTS `writeoff_act` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `act_number` VARCHAR(100) UNIQUE NOT NULL,
  `date` DATE,
  `basis` TEXT,
  `employee_id` INTEGER,
  `comment` TEXT,
  `confirmed` INTEGER DEFAULT 0,
  FOREIGN KEY (`employee_id`) REFERENCES `employee` (`id`)
);

-- Writeoff items
CREATE TABLE IF NOT EXISTS `writeoff_item` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `act_id` INTEGER NOT NULL,
  `book_copy_id` INTEGER NOT NULL,
  `reason` VARCHAR(40) NOT NULL,
  FOREIGN KEY (`act_id`) REFERENCES `writeoff_act` (`id`),
  FOREIGN KEY (`book_copy_id`) REFERENCES `book_copy` (`id`)
);

-- Reader table
CREATE TABLE IF NOT EXISTS `reader` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `ticket_number` VARCHAR(50) UNIQUE,
  `first_name` VARCHAR(50),
  `last_name` VARCHAR(50),
  `patronymic` VARCHAR(50),
  `date_birth` TIMESTAMP,
  `address` VARCHAR(250),
  `email` VARCHAR(250),
  `phone` VARCHAR(50),
  `registered_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `status` VARCHAR(30) DEFAULT 'active',
  `pd_consent` INTEGER DEFAULT 0,
  `pd_consent_at` TIMESTAMP,
  `penalty_points` INT DEFAULT 0
);

-- Reader actions history
CREATE TABLE IF NOT EXISTS `reader_action_log` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `reader_id` INTEGER NOT NULL,
  `action_type` VARCHAR(40) NOT NULL,
  `comment` TEXT,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`reader_id`) REFERENCES `reader` (`id`)
);

-- Penalty history
CREATE TABLE IF NOT EXISTS `penalty_operation` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `reader_id` INTEGER NOT NULL,
  `delta_points` INTEGER NOT NULL,
  `reason` VARCHAR(50) NOT NULL,
  `comment` TEXT,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `employee_id` INTEGER,
  FOREIGN KEY (`reader_id`) REFERENCES `reader` (`id`),
  FOREIGN KEY (`employee_id`) REFERENCES `employee` (`id`)
);

-- Given book (issuance)
CREATE TABLE IF NOT EXISTS `given_book` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `quantity` INTEGER DEFAULT 1,
  `given_date` TIMESTAMP,
  `return_date` TIMESTAMP,
  `return_date_fact` TIMESTAMP,
  `return_comment` TEXT,
  `reader_id` INTEGER NOT NULL,
  `employee_id` INTEGER NOT NULL,
  `book_id` INTEGER NOT NULL,
  `book_copy_id` INTEGER,
  FOREIGN KEY (`reader_id`) REFERENCES `reader` (`id`),
  FOREIGN KEY (`employee_id`) REFERENCES `employee` (`id`),
  FOREIGN KEY (`book_id`) REFERENCES `book` (`id`),
  FOREIGN KEY (`book_copy_id`) REFERENCES `book_copy` (`id`)
);

-- Compatibility old tables
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

CREATE TABLE IF NOT EXISTS `system_settings` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `standart_rental_period` INTEGER NOT NULL,
  `max_books_per_reader` INTEGER NOT NULL,
  `late_return_penalty` INTEGER NOT NULL
);
