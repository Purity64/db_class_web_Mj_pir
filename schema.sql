-- ============================================================
--  schema.sql — ร้านค้าออนไลน์ (นิสิตออกแบบและเขียนเอง)
--  กติกา: 1 ออเดอร์มีหลายสินค้า (M:N: order × product ผ่าน order_line),
--         รีวิว = M:N (customer × product), การชำระเงิน 1:M จาก shop_order
-- ============================================================
CREATE DATABASE IF NOT EXISTS project69
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE project69;

-- DROP ก่อนสร้างใหม่ (เรียงตาม FK) — รัน schema ซ้ำได้
DROP TABLE IF EXISTS payment;
DROP TABLE IF EXISTS code_line;
DROP TABLE IF EXISTS review;
DROP TABLE IF EXISTS product_detail;
DROP TABLE IF EXISTS order_line;
DROP TABLE IF EXISTS shop_order;
DROP TABLE IF EXISTS code;
DROP TABLE IF EXISTS product;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    user_id		INT 			AUTO_INCREMENT PRIMARY key,
    name		varchar(100)	not null,
    email		varchar(100)	unique ,
    password	varchar(255)	not null,
    role  		varchar(255)	default 'user',
    
    constraint 	chk_role		check	(role in('user','admin'))
);

CREATE TABLE product (
    product_id 	INT AUTO_INCREMENT PRIMARY key,
    -- TODO: name, category, price, stock
    name 		varchar(255) not null,
    detail		text null,
    category	varchar(100),
    price		decimal(10,2) not null,
    img_url		varchar(2048),

    discount 	decimal(10,2) null default null,
    created_at	timestamp 	default CURRENT_TIMESTAMP(),
    updated_at	timestamp 	default CURRENT_TIMESTAMP()		on	update	current_timestamp()
);

CREATE TABLE shop_order (   
	-- TODO: cust_id (FK), order_date, status ENUM('pending','shipped')
    -- ★ ไม่ต้องมีคอลัมน์ยอดรวม — คำนวณจาก order_line (ดู search_orders ใน db.py)
    order_id 			INT AUTO_INCREMENT PRIMARY key,

    user_id				int not null,-- fk
    status 				enum('cart','waitpay','success','cancel') not null default 'cart',

    created_at			timestamp 	default CURRENT_TIMESTAMP(),
    updated_at			timestamp 	default CURRENT_TIMESTAMP()		on	update	current_timestamp(),
    end_at      TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL 5 MINUTE),
    constraint	fk_user foreign key (user_id) references users(user_id)
);

CREATE TABLE order_line ( 
    -- M:N: shop_order × product
    -- TODO: order_id (FK), product_id (FK), qty, unit_price ; PRIMARY KEY (order_id, product_id)
    order_line_id 	int auto_increment primary key,
    order_id		int not null,		-- fk
    product_id 		int not null,	-- fk
    unit_price 		decimal(10,2) not null,
    quantity		int not null,
    
    constraint	fk_order 	foreign key(order_id) 	references shop_order(order_id),
    constraint	fk_product	foreign key(product_id)	references product(product_id)
);

CREATE table product_detail(
    product_detail_id	int auto_increment primary key,
    product_id 			int	not null, -- fk
    username 			varchar(255)	not null,
    password			varchar(255)	not null,

    order_line_id 		int null,-- fk null ได้ 
    created_at			timestamp 	default CURRENT_TIMESTAMP(),
    updated_at			timestamp 	default CURRENT_TIMESTAMP()		on	update	current_timestamp(),
    book_end_at         timestamp   null,
    use boolean not null default 0,	-- 0=ของยังไม่ออก 1=ของออกแล้ว
    
    constraint	fk_product_detail_product 		foreign key (product_id) references product(product_id),
    constraint 	fk_order_line	foreign key (order_line_id) references order_line(order_line_id)
);

CREATE TABLE review (             -- M:N: customer × product
    -- TODO: cust_id (FK), product_id (FK), rating, comment, review_date ; PRIMARY KEY (cust_id, product_id)
	review_id	int auto_increment primary key,
    user_id 	INT not null, 
    product_id 	INT not null,
    rating		int	not null,
    comment		text,

    create_at	timestamp 	default CURRENT_TIMESTAMP(),
    constraint 	chk_rating 	check 	(rating	between 1 and 5)
);

CREATE TABLE code (
    code_id INT AUTO_INCREMENT PRIMARY KEY,
    code_name VARCHAR(255) NOT NULL,
    discount DECIMAL(10,2) NOT NULL,
    discount_method ENUM('money', 'percent'),
    status BOOLEAN DEFAULT TRUE,
    max_uses INT NOT NULL DEFAULT 0,        -- 0 = ไม่จำกัดจำนวนครั้ง

    create_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    end_at TIMESTAMP NULL
);

CREATE TABLE code_line (
    code_line_id INT AUTO_INCREMENT PRIMARY KEY,
    code_id  INT NOT NULL,		-- fk
    user_id  INT NOT NULL,		-- fk
    order_id INT NULL,			-- fk (ออเดอร์ที่ใช้โค้ดนี้)

    create_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),

    constraint fk_codeline_code 	foreign key(code_id) 	references code(code_id),
    constraint fk_codeline_user 	foreign key(user_id) 	references users(user_id),
    constraint fk_codeline_order	foreign key(order_id)	references shop_order(order_id)
);

CREATE TABLE payment (            -- 1:M จาก shop_order
    -- TODO: order_id (FK), method, amount, paid_date 
    payment_id 	INT AUTO_INCREMENT PRIMARY key,
    order_id 	int not null,		--	fk 
    amount_pay	decimal	(10,2) not null,
    code_id	int null,			--	fk 
    create_at 	timestamp 	default CURRENT_TIMESTAMP(),
    
    constraint 	 fk_payment_order	foreign key(order_id)	references	shop_order(order_id),
    constraint 	fk_code				foreign key(code_id)	references 	code(code_id)
);


-- TODO: INSERT ข้อมูลตัวอย่างทุกตาราง

INSERT 	INTO users (name, email, password, role) 
values	('Somchai', 'somchai@example.com', '1234', 'user'),
		('Somsri', 'somsri@example.com', '1234', 'user'),
		('Admin', 'admin@example.com', '1234', 'admin');

INSERT 	INTO product (name, detail, category, price, img_url, discount)
VALUES  ('Game Account A', 'บัญชีเกมระดับเริ่มต้น', 'Game', 500.00, NULL, 0.00),
        ('Game Account B', 'บัญชีเกมระดับกลาง', 'Game', 1000.00, NULL, 100.00),
        ('Software License', 'บัญชีซอฟต์แวร์ทดลอง', 'Software', 300.00, NULL, NULL);

INSERT 	INTO shop_order (user_id, status)
VALUES  (1, 'success'),
        (2, 'success'),
        (1, 'waitpay');

INSERT 	INTO order_line (order_id, product_id, unit_price, quantity)
VALUES  (1, 1, 500.00, 1),
        (2, 2, 1000.00, 1),
        (3, 3, 300.00, 1);

INSERT 	INTO product_detail (product_id, username, password, order_line_id)
VALUES  (1, 'demo_game_001', 'demo_pass_001', 1),
        (2, 'demo_game_002', 'demo_pass_002', 2),
        (3, 'demo_software_003', 'demo_pass_003', NULL);

-- สต็อก = จำนวน product_detail ที่ยังว่าง (order_line_id IS NULL)
-- เพิ่มเครดิตคงเหลือสำหรับ demo (สินค้า 1, 2 ถูกใช้ไปแล้ว 1 ชุด)
INSERT 	INTO product_detail (product_id, username, password, order_line_id)
VALUES  (1, 'game_a_02', 'pass_a_02', NULL),
        (1, 'game_a_03', 'pass_a_03', NULL),
        (1, 'game_a_04', 'pass_a_04', NULL),
        (1, 'game_a_05', 'pass_a_05', NULL),
        (2, 'game_b_02', 'pass_b_02', NULL),
        (2, 'game_b_03', 'pass_b_03', NULL),
        (2, 'game_b_04', 'pass_b_04', NULL),
        (2, 'game_b_05', 'pass_b_05', NULL),
        (3, 'soft_02', 'pass_s_02', NULL),
        (3, 'soft_03', 'pass_s_03', NULL),
        (3, 'soft_04', 'pass_s_04', NULL),
        (3, 'soft_05', 'pass_s_05', NULL);

INSERT 	INTO review (user_id, product_id, rating, comment)
VALUES  (1, 1, 5, 'สินค้าตรงตามรายละเอียด'),
        (2, 2, 4, 'ใช้งานได้ดี'),
        (1, 3, 3, 'ใช้งานได้ตามปกติ');

INSERT 	INTO code (code_name, discount, discount_method, status, end_at)
VALUES  ('SAVE50', 50.00, 'money', TRUE, '2026-12-31 23:59:59'),
        ('SALE10', 10.00, 'percent', TRUE, '2026-11-30 23:59:59'),
        ('OLD20', 20.00, 'percent', FALSE, NULL);

INSERT 	INTO payment (order_id, amount_pay, code_id)
VALUES  (1, 450.00, 1),
        (2, 900.00, 2);
