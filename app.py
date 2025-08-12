from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
import pyodbc
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io
import os
db_url = os.environ.get("DATABASE_URL")

import os
import psycopg2

# Get the connection string from Render environment variable
db_url = os.environ.get("DATABASE_URL")

# Connect to PostgreSQL
conn = psycopg2.connect(db_url)
cursor = conn.cursor()

# Optional: Test the connection
cursor.execute("SELECT version();")
print("Connected to:", cursor.fetchone())














app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

conn_str = (
    "Driver={ODBC Driver 17 for SQL Server};"
    "Server=localhost;"
    "Database=VehicleAccessPermit;"
    "Trusted_Connection=yes;"
)

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    domain_id = request.form['domain_id']
    password = request.form['password']

    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM RegisteredEmployees WHERE DomainId = ? AND Password = ?", (domain_id, password))
        reg_user = cursor.fetchone()
        if reg_user:
            session['DomainId'] = domain_id
            flash("Login Successful - Registered Employee")
            return redirect(url_for('enter_details'))

        cursor.execute("SELECT * FROM HOD WHERE DomainId = ? AND Password = ?", (domain_id, password))
        hod_user = cursor.fetchone()
        if hod_user:
            session['DomainId'] = domain_id
            flash("Login Successful - HOD")
            return redirect(url_for('hod'))

        cursor.execute("SELECT * FROM Security WHERE DomainId = ? AND Password = ?", (domain_id, password))
        sec_user = cursor.fetchone()
        if sec_user:
            session['DomainId'] = domain_id
            flash("Login Successful - Security")
            return redirect(url_for('security'))
        
        cursor.execute("SELECT * FROM Admin WHERE DomainId = ? AND Password = ?", (domain_id, password))
        admin_user = cursor.fetchone()
        if admin_user:
            session['DomainId'] = domain_id
            flash("Login Successful - Admin")
            return redirect(url_for('admin'))

        flash("Invalid Details")
        return redirect(url_for('home'))

    except Exception as e:
        flash(f"Login Error: {str(e)}")
        return redirect(url_for('home'))
    
@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.")
    return redirect(url_for('home'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        domain_id = request.form['domain_id']
        domain_name = request.form['domain_name']
        email = request.form['email']
        password = request.form['password']
        mobile_number = request.form['mobile_number']

        try:
            conn = pyodbc.connect(conn_str)
            cursor = conn.cursor()

            cursor.execute("SELECT domainid FROM RelianceEmployees WHERE domainid = ?", (domain_id,))
            reliance_result = cursor.fetchone()

            if not reliance_result:
                flash("DomainId Does Not Exist")
                return redirect(url_for('register'))

            cursor.execute("SELECT * FROM RegisteredEmployees WHERE DomainID = ?", (domain_id,))
            registered_result = cursor.fetchone()

            if registered_result:
                cursor.execute("""
                    UPDATE RegisteredEmployees
                    SET DomainName = ?, Email = ?, Password = ?, MobileNumber = ?
                    WHERE DomainID = ?
                """, (domain_name, email, password, mobile_number, domain_id))
                conn.commit()
                flash('Registration Updated Successfully.')
            else:
                cursor.execute("""
                    INSERT INTO RegisteredEmployees (DomainID, DomainName, Email, Password, MobileNumber)
                    VALUES (?, ?, ?, ?, ?)
                """, (domain_id, domain_name, email, password, mobile_number))
                conn.commit()
                flash('Registration Successful! You can now login.')

            return redirect(url_for('home'))

        except Exception as e:
            flash(f'Registration Error: {str(e)}')
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/enter_details')
def enter_details():
    if 'DomainId' not in session:
        flash("Please login first.")
        return redirect(url_for('home'))
    return render_template('enter_details.html')

@app.route('/hod')
def hod():
    if 'DomainId' not in session:
        flash("Please login first.")
        return redirect(url_for('home'))
    return render_template('hod.html')

@app.route('/security')
def security():
    if 'DomainId' not in session:
        flash("Please login first.")
        return redirect(url_for('home'))
    return render_template('security.html')

@app.route('/get_employee_details')
def get_employee_details():
    domain_id = session.get('DomainId')
    if not domain_id:
        return jsonify({"error": "Not logged in"}), 401

    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    cursor.execute("SELECT DomainName, Email, Password, MobileNumber FROM RegisteredEmployees WHERE DomainID = ?", domain_id)
    row = cursor.fetchone()

    if row:
        return jsonify({
            "DomainName": row[0],
            "Email": row[1],
            "Password": row[2],
            "MobileNumber": row[3]
        })
    else:
        return jsonify({"error": "User not found"}), 404

@app.route('/details')
def details():
    return render_template('details.html')

@app.route('/check_pass_status')
def check_pass_status():
    domain_id = session.get('DomainId')
    if not domain_id:
        flash("Session expired. Please log in again.")
        return redirect(url_for('home'))

    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM VehicleAccessRequests WHERE RequestedBy = ?", (domain_id,))
    rows = cursor.fetchall()

    return render_template('pass.html', requests=rows)

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from flask import send_file, flash, redirect, url_for
import io
import pyodbc

@app.route('/download_pdf/<int:request_id>')
def download_pdf(request_id):
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM VehicleAccessRequests WHERE RequestId = ?", (request_id,))
        row = cursor.fetchone()

        if not row:
            flash("No such request found.")
            return redirect(url_for('check_pass_status'))

        columns = [desc[0] for desc in cursor.description]
        request_data = dict(zip(columns, row))

        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)

        # Document Header
        p.setFont("Helvetica-Bold", 16)
        p.drawCentredString(300, 800, "Vehicle Access Pass Summary")
        p.setFont("Helvetica", 10)
        p.line(40, 795, 550, 795)

        # Add request details neatly
        y = 770
        for key, value in request_data.items():
            p.drawString(50, y, f"{key}:")
            p.drawString(200, y, str(value))
            y -= 20
            if y < 50:
                p.showPage()
                y = 800
                p.setFont("Helvetica", 10)

        # Footer
        p.setFont("Helvetica-Oblique", 9)
        p.drawString(400, 30, "Generated by Vehicle Access Portal")

        p.showPage()
        p.save()
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"VehicleAccessRequest_{request_id}.pdf",
            mimetype='application/pdf'
        )

    except Exception as e:
        flash(f"Error generating PDF: {str(e)}")
        return redirect(url_for('check_pass_status'))


@app.route('/submit_vehicle_pass', methods=['POST'])
def submit_vehicle_pass():
    try:
        domain_id = session.get('DomainId')
        if not domain_id:
            flash("Session expired. Please log in again.")
            return redirect(url_for('home'))

        data = request.form

        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO VehicleAccessRequests (
                RequestedBy, VehicleType, TypeOfVehicle, AccessLocation, VehicleNo,
                EngineNo, ChassisNo, Model, OwnerUsername, Address, ContactNo,
                DriverName, DriverAddress, FromDate, ToDate, HODApproval, SecurityApproval
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending', 'Pending')
        """, (
            domain_id,
            data['vehicle_type'], data['type_of_vehicle'], data['access_location'], data['vehicle_no'],
            data['engine_no'], data['chassis_no'], data['model'], data['owner_username'],
            data['address'], data['contact_no'], data['driver_name'], data['driver_address'],
            data['from_date'], data['to_date']
        ))

        conn.commit()
        flash("Pass Request Generated")
        return redirect(url_for('enter_details'))

    except Exception as e:
        flash(f"Error submitting request: {str(e)}")
        return redirect(url_for('enter_details'))

@app.route('/delete_request/<int:request_id>', methods=['POST'])
def delete_request(request_id):
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM VehicleAccessRequests WHERE RequestId = ?", request_id)
        conn.commit()
        flash("Request Deleted")
        return redirect(request.referrer or url_for('hod_requests'))
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/approve_request/<int:request_id>', methods=['POST'])
def approve_request(request_id):
    try:
        status = request.form.get('status', 'Approved')
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("UPDATE VehicleAccessRequests SET HODApproval = ? WHERE RequestId = ?", (status, request_id))
        conn.commit()
        flash("Approved Pass")
        return redirect(request.referrer or url_for('hod_requests'))
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/hod_details')
def hod_details():
    domain_id = session.get('DomainId')
    if not domain_id:
        flash("Login required")
        return redirect(url_for('home'))

    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    cursor.execute("SELECT DomainID, DomainName, Department, Email, MobileNumber FROM HOD WHERE DomainID = ?", (domain_id,))
    row = cursor.fetchone()

    if row:
        hod_data = {
            "DomainID": row[0],
            "DomainName": row[1],
            "Department": row[2],
            "Email": row[3],
            "MobileNumber": row[4]
        }
        return render_template('hod_details.html', hod=hod_data)
    else:
        flash("No HOD details found")
        return render_template('hod_details.html', hod=None)

@app.route('/hod_requests')
def hod_requests():
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM VehicleAccessRequests WHERE HODApproval = 'Pending'")
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        requests = [dict(zip(columns, row)) for row in rows]
        return render_template('hod_requests.html', requests=requests)
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/security_details')
def security_details():
    domain_id = session.get('DomainId')
    if not domain_id:
        flash("Login required")
        return redirect(url_for('home'))

    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    cursor.execute("SELECT DomainId, DomainName, Email, MobileNumber FROM Security WHERE DomainId = ?", (domain_id,))
    row = cursor.fetchone()

    if row:
        sec_data = {
            "DomainId": row[0],
            "DomainName": row[1],
            "Email": row[2],
            "MobileNumber": row[3]
        }
        return render_template('security_details.html', security=sec_data)
    else:
        flash("No Security details found")
        return render_template('security_details.html', security=None)

@app.route('/security_requests')
def security_requests():
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM VehicleAccessRequests
            WHERE HODApproval = 'Approved' AND (SecurityApproval IS NULL OR SecurityApproval = 'Pending')
        """)
        rows = cursor.fetchall()
        requests = [dict(zip([desc[0] for desc in cursor.description], row)) for row in rows]
        return render_template('security_requests.html', requests=requests)
    except Exception as e:
        return f"\u274c Error loading security requests: {str(e)}", 500

@app.route('/security_approve/<int:request_id>', methods=['POST'])
def security_approve(request_id):
    try:
        status = request.form.get('status', 'Approved')
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("UPDATE VehicleAccessRequests SET SecurityApproval = ? WHERE RequestID = ?", (status, request_id))
        conn.commit()
        flash("Pass Approved by Security")
        return redirect(url_for('security_requests'))
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/delete_security_request/<int:request_id>', methods=['POST'])
def delete_security_request(request_id):
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM VehicleAccessRequests WHERE RequestId = ?", request_id)
        conn.commit()
        flash("Deleted Approved Request Successfully")
        return redirect(url_for('security_requests'))
    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)
