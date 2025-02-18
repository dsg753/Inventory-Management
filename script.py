from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3

app = Flask(__name__)
app.secret_key = "inventory_secret_key"

# Database setup
def initialize_db():
    conn = sqlite3.connect("inventory.db", timeout=10)
    cursor = conn.cursor()
    
    cursor.execute("DROP TABLE IF EXISTS machinery")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS objects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT NOT NULL,
            description TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS machinery (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inventory_number TEXT NOT NULL,
            serial_number TEXT NOT NULL,
            name TEXT NOT NULL,
            daily_rent TEXT,
            value TEXT,
            acquisition_date TEXT,
            type TEXT NOT NULL,
            condition TEXT NOT NULL,
            last_maintenance TEXT,
            is_rented INTEGER DEFAULT 0,
            location_id INTEGER REFERENCES objects(id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rentals (
            rental_id INTEGER PRIMARY KEY AUTOINCREMENT,
            machinery_id INTEGER,
            renter_name TEXT NOT NULL,
            rent_date TEXT NOT NULL,
            return_date TEXT,
            FOREIGN KEY (machinery_id) REFERENCES machinery (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            construction_site TEXT NOT NULL,
            technical_manager TEXT NOT NULL,
            phone_number TEXT
        )
    """)
    
    conn.commit()
    conn.close()

initialize_db()

@app.route("/")
def index():
    return render_template("dashboard.html")

@app.route("/machines")
def machines():
    conn = sqlite3.connect("inventory.db", timeout=10)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, inventory_number, serial_number, name, daily_rent, value, acquisition_date, type, condition, last_maintenance, is_rented 
        FROM machinery
    """)
    machinery_list = cursor.fetchall()
    conn.close()
    return render_template("machines.html", machinery_list=machinery_list)

@app.route("/dashboard")
def dashboard():
    conn = sqlite3.connect("inventory.db", timeout=10)
    cursor = conn.cursor()

    # Fetch total number of machines
    cursor.execute("SELECT COUNT(*) FROM machinery")
    total_machines = cursor.fetchone()[0]

    # Fetch number of rented machines
    cursor.execute("SELECT COUNT(*) FROM machinery WHERE is_rented = 1")
    rented_count = cursor.fetchone()[0]

    conn.close()

    return render_template("dashboard.html", total_machines=total_machines, rented_count=rented_count)


@app.route('/machines/add', methods=['GET', 'POST'])
def add_machinery():
    if request.method == 'POST':
        inventory_number = request.form['inventory_number']
        serial_number = request.form['serial_number']
        name = request.form['name']
        type = request.form['type']
        condition = request.form['condition']
        daily_rent = request.form['daily_rent']
        value = request.form['value']
        acquisition_date = request.form['acquisition_date']
        last_maintenance = request.form['last_maintenance']

        conn = sqlite3.connect("inventory.db", timeout=10)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO machinery (inventory_number, serial_number, name, type, condition, daily_rent, value, acquisition_date, last_maintenance, is_rented)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        ''', (inventory_number, serial_number, name, type, condition, daily_rent, value, acquisition_date, last_maintenance))
        conn.commit()
        conn.close()

        flash("Machinery added successfully!", "success")
        return redirect(url_for('machines'))

    return render_template("add_machinery.html")

@app.route("/rented_out")
def rented_machines():
    conn = sqlite3.connect("inventory.db", timeout=10)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT rentals.rental_id, machinery.name, rentals.renter_name, rentals.rent_date, rentals.return_date, objects.name as construction_site
        FROM rentals
        JOIN machinery ON rentals.machinery_id = machinery.id
        LEFT JOIN objects ON machinery.location_id = objects.id
    """)
    rented_list = cursor.fetchall()
    conn.close()
    return render_template("rented_out.html", rented_machines=rented_list)

@app.route("/machines/rent", methods=["GET", "POST"])
def add_machine_for_rent():
    conn = sqlite3.connect("inventory.db", timeout=10)
    cursor = conn.cursor()
    
    if request.method == "POST":
        machine_id = request.form["machine_id"]
        renter_name = request.form["renter_name"]
        rent_date = request.form["rent_date"]

        cursor.execute("INSERT INTO rentals (machinery_id, renter_name, rent_date) VALUES (?, ?, ?)", 
                       (machine_id, renter_name, rent_date))
        cursor.execute("UPDATE machinery SET is_rented = 1 WHERE id = ?", (machine_id,))
        
        conn.commit()
        conn.close()
        flash("Machine rented successfully!", "success")
        return redirect(url_for("rented_machines"))

    cursor.execute("SELECT id, name FROM machinery WHERE is_rented = 0")
    available_machines = cursor.fetchall()

    cursor.execute("SELECT id, name FROM objects")
    suppliers = cursor.fetchall()

    conn.close()

    return render_template("add_machine_for_rent.html", available_machines=available_machines, suppliers=suppliers)

@app.route('/obekti')
def obekti():
    conn = sqlite3.connect("inventory.db", timeout=10)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, name, address, description
        FROM objects
    ''')
    objects = cursor.fetchall()
    conn.close()
    return render_template("obekti.html", objects=objects)

@app.route("/suppliers", methods=["GET"])
def suppliers():
    conn = sqlite3.connect("inventory.db", timeout=10)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM suppliers")
    suppliers_list = cursor.fetchall()
    conn.close()
    return render_template("suppliers.html", suppliers=suppliers_list)

@app.route("/suppliers/add", methods=["POST"])
def add_supplier():
    name = request.form["name"]
    construction_site = request.form["construction_site"]
    technical_manager = request.form["technical_manager"]
    phone_number = request.form["phone_number"]
    
    conn = sqlite3.connect("inventory.db", timeout=10)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO suppliers (name, construction_site, technical_manager, phone_number) VALUES (?, ?, ?, ?)",
        (name, construction_site, technical_manager, phone_number)
    )
    conn.commit()
    conn.close()
    
    flash("Supplier added successfully!", "success")
    return redirect(url_for("suppliers"))

@app.route("/return_machine/<int:rental_id>")
def return_machine(rental_id):
    conn = sqlite3.connect("inventory.db", timeout=10)
    cursor = conn.cursor()
    
    # Update the return date for the rental
    cursor.execute("UPDATE rentals SET return_date = date('now') WHERE rental_id = ?", (rental_id,))
    
    # Set the machine as not rented
    cursor.execute("""
        UPDATE machinery
        SET is_rented = 0
        WHERE id = (SELECT machinery_id FROM rentals WHERE rental_id = ?)
    """, (rental_id,))
    
    conn.commit()
    conn.close()
    
    flash("Machine returned successfully!", "success")
    return redirect(url_for("rented_machines"))

if __name__ == "__main__":
    app.run(debug=True)
