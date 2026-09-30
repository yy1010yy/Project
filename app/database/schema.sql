CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    email TEXT NOT NULL CHECK(email REGEXP '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    username TEXT NOT NULL,
    hashed_password TEXT NOT NULL,
    user_role TEXT NOT NULL CHECK(role IN ('guest', 'receptionist', 'housekeeper','manager')),
    must_change_password INTEGER NOT NULL CHECK(must_change_password IN (0, 1)) DEFAULT 0,
    is_active INTEGER NOT NULL CHECK(is_active IN (0, 1)) DEFAULT 1
);

CREATE UNIQUE INDEX email on users(email);
CREATE INDEX username ON users(username);

CREATE TABLE IF NOT EXISTS rooms(
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    room_number INTEGER UNIQUE NOT NULL,
    room_physical_status TEXT NOT NULL DEFAULT 'clean' CHECK(room_physical_status IN ('clean', 'dirty', 'maintenance', 'out of service')),
    room_type TEXT NOT NULL CHECK(room_type IN ('standard', 'deluxe', 'family', 'business suite')),
    room_price DECIMAL NOT NULL
);

CREATE TABLE IF NOT EXISTS bookings(
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    guest_id INTEGER NOT NULL,
    room_id INTEGER NOT NULL,
    check_in_date DATE NOT NULL, -- format: YYYY-MM-DD
    -- DATE still works as TEXT when processed by sqlite under the hood (use DATE to add clarity only)
    check_out_date DATE NOT NULL, -- format: YYYY-MM-DD
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, -- current utc timestamp
    booking_status TEXT NOT NULL CHECK(booking_status IN ('pending', 'confirmed', 'checked in', 'checked out', 'cancelled')),
    FOREIGN KEY (guest_id) references guests(id),
    FOREIGN KEY (room_id) references rooms(id),
    CONSTRAINT check_dates CHECK(check_out_date > check_in_date)
)

CREATE TABLE IF NOT EXISTS guests(
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    user_id INTEGER NOT NULL,
    FOREIGN KEY (user_id) references users(id)
);


CREATE TABLE IF NOT EXISTS staff(
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    user_id INTEGER NOT NULL,
    employee_id TEXT UNIQUE NOT NULL,
    FOREIGN KEY (user_id) references users(id)
);


CREATE TABLE IF NOT EXISTS employee_id_counter(
    employee_role TEXT PRIMARY KEY NOT NULL CHECK(employee_role IN ('receptionist', 'housekeeper', 'manager')),
    id_counter INTEGER NOT NULL
);


INSERT INTO employee_id_counter (employee_role, id_counter)
VALUES
    ("manager", 1),
    ("receptionist", 1),
    ("housekeeper", 1);
