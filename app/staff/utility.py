ROLE_PREFIXES = {
    "receptionist": "REC",
    "manager": "MNR",
    "housekeeper": "HSK"
    }



def assign_employee_id(db, role):
    """ Assign the next employee id for a staff """

    prefix = ROLE_PREFIXES.get(role)

    if not prefix:
        raise ValueError("Invalid staff role.")

    row = db.execute("SELECT id_counter FROM employee_id_counter WHERE employee_role = ?", (role,)).fetchone()

    if not row:
        raise ValueError("Employee ID counter not found.")

    number = row["id_counter"]

    db.execute("UPDATE employee_id_counter SET id_counter = id_counter + 1 WHERE employee_role = ?", (role,))

    # minimum 3 digits 
    return f"{prefix}-{number:03d}"
