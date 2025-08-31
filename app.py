from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
import pdfkit
import MySQLdb.cursors
import os
import io

app = Flask(__name__)
app.secret_key = 'e8c434e0d786e28bd042a7072ac15bf3d9db84a69d5913d3e5b1d23e353f77ef'

# MySQL config
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_PORT'] = 3306
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '1951'
app.config['MYSQL_DB'] = 'student'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)
path_to_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
config = pdfkit.configuration(wkhtmltopdf=path_to_wkhtmltopdf)


@app.route('/')
def home():
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        admission_no = request.form['admission_no']
        password = request.form['password']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM student WHERE admission_no = %s", (admission_no,))
        student = cursor.fetchone()
        cursor.close()

        if student and check_password_hash(student['password'], password):
            session['user'] = student['admission_no']
            flash('Login successful!', 'success')
            return redirect(url_for('student_portal', id=student['admission_no']))
        else:
            flash('Invalid admission number or password.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/index')
def index():
    return render_template('dashboard.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM student")
    students = cur.fetchall()
    cur.execute("SELECT * FROM subject")
    subjects = cur.fetchall()
    cur.execute("SELECT * FROM exam")
    exams = cur.fetchall()
    cur.close()
    return render_template('admin.html', students=students, subjects=subjects, exams=exams)

@app.route('/add_student', methods=['POST'])
def add_student():
    data = request.form
    hashed_password = generate_password_hash(data['password'])
    cur = mysql.connection.cursor()
    try:
        cur.execute("""
            INSERT INTO student (FirstName, LastName, admission_no, gender, class, password)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            data['first_name'], data['last_name'], data['admission_no'],
            data['gender'], data['class'], hashed_password
        ))
        mysql.connection.commit()
        flash("Student added successfully", "success")
    except Exception as e:
        print("Error adding student:", e)
        flash("Failed to add student. Admission number might already exist.", "danger")
    finally:
        cur.close()

    return redirect(url_for('admin'))

@app.route('/add_subject', methods=['POST'])
def add_subject():
    name = request.form['subject_name']
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO subject (subject_name) VALUES (%s)", (name,))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('admin'))

@app.route('/add_exam', methods=['POST'])
def add_exam():
    name = request.form['name']
    term = request.form['term']
    year = request.form['year']
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO exam (name, term, year) VALUES (%s, %s, %s)", (name, term, year))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('admin'))

@app.route('/edit_student/<int:student_id>', methods=['GET', 'POST'])
def edit_student(student_id):
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        data = request.form
        cur.execute("""
            UPDATE student SET FirstName=%s, LastName=%s, admission_no=%s,
            gender=%s, class=%s WHERE id=%s
        """, (data['first_name'], data['last_name'], data['admission_no'],
              data['gender'], data['class'], student_id))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('admin'))
    cur.execute("SELECT * FROM student WHERE id = %s", (student_id,))
    student = cur.fetchone()
    cur.close()
    return render_template('edit_student.html', student=student)

@app.route('/delete_student/<int:student_id>')
def delete_student(student_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM student WHERE id = %s", (student_id,))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('admin'))

@app.route('/edit_subject/<int:subject_id>', methods=['GET', 'POST'])
def edit_subject(subject_id):
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        name = request.form['subject_name']
        cur.execute("UPDATE subject SET subject_name = %s WHERE id = %s", (name, subject_id))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('admin'))
    cur.execute("SELECT * FROM subject WHERE id = %s", (subject_id,))
    subject = cur.fetchone()
    cur.close()
    return render_template('edit_subject.html', subject=subject)

@app.route('/delete_subject/<int:subject_id>')
def delete_subject(subject_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM subject WHERE id = %s", (subject_id,))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('admin'))

@app.route('/edit_exam/<int:exam_id>', methods=['GET', 'POST'])
def edit_exam(exam_id):
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        name = request.form['name']
        term = request.form['term']
        year = request.form['year']
        cur.execute("UPDATE exam SET name=%s, term=%s, year=%s WHERE id=%s",
                    (name, term, year, exam_id))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('admin'))
    cur.execute("SELECT * FROM exam WHERE id = %s", (exam_id,))
    exam = cur.fetchone()
    cur.close()
    return render_template('edit_exam.html', exam=exam)

@app.route('/delete_exam/<int:exam_id>')
def delete_exam(exam_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM exam WHERE id = %s", (exam_id,))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('admin'))

@app.route('/student_portal')
def student_portal():
    admission_no = request.args.get('id')
    if not admission_no:
        flash("Student ID is required.", "danger")
        return redirect(url_for('login'))

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT id FROM student WHERE admission_no = %s", (admission_no,))
    student = cur.fetchone()

    if not student:
        flash("Student not found.", "danger")
        return redirect(url_for('login'))

    student_id = student['id']

    cur.execute("SELECT * FROM fees WHERE student_id = %s", (student_id,))
    fees = cur.fetchall()

    cur.execute("""
        SELECT r.subject_id, s.subject_name, r.exam_id, r.marks_obtained
        FROM result r
        JOIN subject s ON r.subject_id = s.id
        WHERE r.student_id = %s
    """, (student_id,))
    results = cur.fetchall()

    cur.close()
    return render_template('student_portal.html', fees=fees, results=results)

@app.route('/download/<datatype>/<admission_no>')
def download_pdf(datatype, admission_no):
    cur = mysql.connection.cursor()
    cur.execute("SELECT id FROM student WHERE admission_no = %s", (admission_no,))
    student = cur.fetchone()
    if not student:
        flash("Student not found for download.", "danger")
        return redirect(url_for('login'))

    student_id = student['id']

    if datatype == "fees":
        cur.execute("SELECT * FROM fees WHERE student_id = %s", (student_id,))
    elif datatype == "results":
        cur.execute("""
            SELECT r.subject_id, s.subject_name, r.exam_id, r.marks_obtained
            FROM result r
            JOIN subject s ON r.subject_id = s.id
            WHERE r.student_id = %s
        """, (student_id,))
    else:
        flash("Invalid data type requested.", "danger")
        return redirect(url_for('student_portal', id=admission_no))

    records = cur.fetchall()
    cur.close()

    html = render_template('pdf_template.html', records=records, datatype=datatype)
    pdf = pdfkit.from_string(html, False, configuration=config)

    return send_file(
        io.BytesIO(pdf),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"{datatype}_statement_{admission_no}.pdf"
    )

@app.route('/add_fees', methods=['POST'])
def add_fees():
    student_id = request.form['student_id']
    term = request.form['term']
    year = request.form['year']
    total_amount = request.form['total_amount']

    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO fees (student_id, term, year, total_amount)
        VALUES (%s, %s, %s, %s)
    """, (student_id, term, year, total_amount))
    mysql.connection.commit()
    cur.close()
    flash("Fees record added successfully.", "success")
    return redirect(url_for('admin'))

@app.route('/add_result', methods=['POST'])
def add_result():
    student_id = request.form['student_id']
    subject_id = request.form['subject_id']
    exam_id = request.form['exam_id']
    marks_obtained = request.form['marks_obtained']

    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO result (student_id, subject_id, exam_id, marks_obtained)
        VALUES (%s, %s, %s, %s)
    """, (student_id, subject_id, exam_id, marks_obtained))
    mysql.connection.commit()
    cur.close()
    flash("Result added successfully.", "success")
    return redirect(url_for('admin'))



if __name__ == '__main__':
    app.run(debug=True)