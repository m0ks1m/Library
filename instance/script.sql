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
  `contact_person` VARCHAR(250),
  `phone` VARCHAR(50),
  `email` VARCHAR(250),
  `city` VARCHAR(100),
  `street` VARCHAR(150),
  `house` VARCHAR(30),
  `apartment` VARCHAR(30),
  `comment` VARCHAR(250),
  `is_active` INTEGER DEFAULT 1,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
  `city` VARCHAR(100),
  `street` VARCHAR(150),
  `house` VARCHAR(30),
  `apartment` VARCHAR(30),
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


CREATE TABLE IF NOT EXISTS `supplier_contract` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `contract_number` VARCHAR(50) NOT NULL,
  `signed_at` DATE NOT NULL,
  `supplier_id` INTEGER NOT NULL,
  `start_date` DATE,
  `end_date` DATE,
  `amount_or_terms` VARCHAR(250),
  `comment` VARCHAR(250),
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`supplier_id`) REFERENCES `supplier` (`id`)
);

CREATE TABLE IF NOT EXISTS `supply_invoice` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `invoice_number` VARCHAR(50) NOT NULL,
  `invoice_date` DATE NOT NULL,
  `supplier_id` INTEGER NOT NULL,
  `contract_id` INTEGER,
  `responsible_person` VARCHAR(120),
  `comment` VARCHAR(250),
  `status` VARCHAR(20) DEFAULT 'DRAFT',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`supplier_id`) REFERENCES `supplier` (`id`),
  FOREIGN KEY (`contract_id`) REFERENCES `supplier_contract` (`id`)
);

CREATE TABLE IF NOT EXISTS `supply_invoice_item` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `invoice_id` INTEGER NOT NULL,
  `book_id` INTEGER NOT NULL,
  `quantity` INTEGER NOT NULL,
  `unit_price` REAL DEFAULT 0,
  FOREIGN KEY (`invoice_id`) REFERENCES `supply_invoice` (`id`),
  FOREIGN KEY (`book_id`) REFERENCES `book` (`id`)
);

CREATE TABLE IF NOT EXISTS `acceptance_act` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `act_number` VARCHAR(50) NOT NULL,
  `act_date` DATE NOT NULL,
  `supplier_id` INTEGER NOT NULL,
  `contract_id` INTEGER,
  `responsible_person` VARCHAR(120),
  `comment` VARCHAR(250),
  `status` VARCHAR(20) DEFAULT 'DRAFT',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`supplier_id`) REFERENCES `supplier` (`id`),
  FOREIGN KEY (`contract_id`) REFERENCES `supplier_contract` (`id`)
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
  `copy_uid` VARCHAR(30) UNIQUE,
  `book_id` INTEGER NOT NULL,
  `acceptance_act_id` INTEGER,
  `status` VARCHAR(20) DEFAULT 'available',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`book_id`) REFERENCES `book` (`id`),
  FOREIGN KEY (`acceptance_act_id`) REFERENCES `acceptance_act` (`id`)
);

CREATE TABLE IF NOT EXISTS `writeoff_act` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `act_number` VARCHAR(50) NOT NULL,
  `act_date` DATE NOT NULL,
  `basis` VARCHAR(250),
  `responsible_person` VARCHAR(120),
  `comment` VARCHAR(250),
  `status` VARCHAR(20) DEFAULT 'DRAFT',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `writeoff_act_item` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `act_id` INTEGER NOT NULL,
  `book_copy_id` INTEGER NOT NULL,
  `reason` VARCHAR(40) NOT NULL,
  FOREIGN KEY (`act_id`) REFERENCES `writeoff_act` (`id`),
  FOREIGN KEY (`book_copy_id`) REFERENCES `book_copy` (`id`)
);
