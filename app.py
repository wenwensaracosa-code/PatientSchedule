import os
import datetime
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for, session, 
    send_from_directory, g
)
import db

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'edoc_secret_key_appointment_system_2026')
app.url_map.strict_slashes = False

@app.teardown_appcontext
def teardown_db(exception):
    db.close_db(exception)

# Static file routes to preserve CSS / IMG structure
@app.route('/css/<path:filename>')
def static_css(filename):
    return send_from_directory(os.path.join(app.root_path, 'css'), filename)

@app.route('/img/<path:filename>')
def static_img(filename):
    return send_from_directory(os.path.join(app.root_path, 'img'), filename)

@app.before_request
def handle_legacy_php_redirects():
    path = request.path
    if path in ['/api', '/api/', '/api/index.php']:
        return redirect('/', code=301)
    if path.endswith('.php') or path.endswith('.html'):
        clean = path[:-4] if path.endswith('.php') else path[:-5]
        clean = clean.rstrip('/')
        if clean in ['', '/index']:
            target = '/'
        elif clean.endswith('/index'):
            target = clean[:-5]
        else:
            target = clean
        if request.method == 'GET':
            qs = request.query_string.decode('utf-8')
            url = target + ('?' + qs if qs else '')
            return redirect(url, code=301)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

def get_today():
    return datetime.date.today().strftime('%Y-%m-%d')

def get_next_week_date():
    return (datetime.date.today() + datetime.timedelta(days=7)).strftime('%Y-%m-%d')

def get_next_week_day():
    return (datetime.date.today() + datetime.timedelta(days=7)).strftime('%A')

def format_row(row):
    if not row:
        return row
    d = dict(row)
    for k, v in d.items():
        if hasattr(v, 'strftime'):
            d[k] = v.strftime('%Y-%m-%d' if isinstance(v, datetime.date) and not isinstance(v, datetime.datetime) else '%Y-%m-%d %H:%M:%S')
        elif isinstance(v, datetime.timedelta):
            # Format timedelta as HH:MM
            total_seconds = int(v.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            d[k] = f"{hours:02d}:{minutes:02d}:00"
    return d

def format_rows(rows):
    return [format_row(r) for r in rows]

# Route protection decorator
def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user' not in session or not session['user']:
                return redirect(url_for('login'))
            if role and session.get('usertype') != role:
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ========================================================
# Public & Authentication Routes
# ========================================================

@app.route('/')
@app.route('/index')
@app.route('/index.html')
@app.route('/index.php')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
@app.route('/login.php', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form.get('useremail', '').strip()
        password = request.form.get('userpassword', '').strip()
        
        webuser = db.query_db("SELECT * FROM webuser WHERE email = %s", (email,), one=True)
        if webuser:
            utype = webuser['usertype']
            if utype == 'p':
                patient = db.query_db("SELECT * FROM patient WHERE pemail = %s AND ppassword = %s", (email, password), one=True)
                if patient:
                    session['user'] = email
                    session['usertype'] = 'p'
                    session['username'] = patient['pname']
                    session['userid'] = patient['pid']
                    return redirect(url_for('patient_dashboard'))
                else:
                    error = 'Wrong credentials: Invalid email or password'
            elif utype == 'a':
                admin = db.query_db("SELECT * FROM admin WHERE aemail = %s AND apassword = %s", (email, password), one=True)
                if admin:
                    session['user'] = email
                    session['usertype'] = 'a'
                    session['username'] = 'Administrator'
                    session['userid'] = email
                    return redirect(url_for('admin_dashboard'))
                else:
                    error = 'Wrong credentials: Invalid email or password'
            elif utype == 'd':
                doctor = db.query_db("SELECT * FROM doctor WHERE docemail = %s AND docpassword = %s", (email, password), one=True)
                if doctor:
                    session['user'] = email
                    session['usertype'] = 'd'
                    session['username'] = doctor['docname']
                    session['userid'] = doctor['docid']
                    return redirect(url_for('doctor_dashboard'))
                else:
                    error = 'Wrong credentials: Invalid email or password'
        else:
            error = 'No account was found for this email address.'

    return render_template('login.html', error=error)

@app.route('/signup', methods=['GET', 'POST'])
@app.route('/signup.php', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        session['personal'] = {
            'fname': request.form.get('fname', '').strip(),
            'lname': request.form.get('lname', '').strip(),
            'address': request.form.get('address', '').strip(),
            'nic': request.form.get('nic', '').strip(),
            'dob': request.form.get('dob', '').strip()
        }
        return redirect(url_for('create_account'))
    return render_template('signup.html', personal=session.get('personal'))

@app.route('/create-account', methods=['GET', 'POST'])
@app.route('/create-account.php', methods=['GET', 'POST'])
def create_account():
    error = None
    if request.method == 'POST':
        personal = session.get('personal', {})
        fname = personal.get('fname', '')
        lname = personal.get('lname', '')
        name = f"{fname} {lname}".strip()
        address = personal.get('address', '')
        nic = personal.get('nic', '')
        dob = personal.get('dob', '')
        email = request.form.get('newemail', '').strip()
        tele = request.form.get('tele', '').strip()
        newpassword = request.form.get('newpassword', '').strip()
        cpassword = request.form.get('cpassword', '').strip()

        if newpassword != cpassword:
            error = 'Password confirmation error. Please re-enter your passwords.'
        else:
            existing = db.query_db("SELECT * FROM webuser WHERE email = %s", (email,), one=True)
            if existing:
                error = 'Already have an account for this Email address.'
            else:
                db.execute_db(
                    "INSERT INTO patient (pemail, pname, ppassword, paddress, pnic, pdob, ptel) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (email, name, newpassword, address, nic, dob, tele)
                )
                db.execute_db("INSERT INTO webuser (email, usertype) VALUES (%s, 'p')", (email,))
                
                patient = db.query_db("SELECT pid FROM patient WHERE pemail = %s", (email,), one=True)
                session['user'] = email
                session['usertype'] = 'p'
                session['username'] = name
                session['userid'] = patient['pid'] if patient else 1
                session.pop('personal', None)
                return redirect(url_for('patient_dashboard'))

    return render_template('create_account.html', error=error)

@app.route('/logout')
@app.route('/logout.php')
def logout():
    session.clear()
    return redirect(url_for('login', action='logout'))

# ========================================================
# Admin Routes
# ========================================================

@app.route('/admin')
@app.route('/admin/')
@app.route('/admin/index')
@app.route('/admin/index.php')
@login_required('a')
def admin_dashboard():
    today = get_today()
    next_week = get_next_week_date()
    
    doc_count = db.query_db("SELECT COUNT(*) AS count FROM doctor", one=True)['count']
    pat_count = db.query_db("SELECT COUNT(*) AS count FROM patient", one=True)['count']
    app_count = db.query_db("SELECT COUNT(*) AS count FROM appointment WHERE appodate >= %s", (today,), one=True)['count']
    sch_count = db.query_db("SELECT COUNT(*) AS count FROM schedule WHERE scheduledate = %s", (today,), one=True)['count']
    
    doc_datalist = db.query_db("SELECT docname, docemail FROM doctor")
    
    upcoming_appointments = db.query_db("""
        SELECT appointment.appoid, schedule.scheduleid, schedule.title, doctor.docname,
               patient.pname, schedule.scheduledate, schedule.scheduletime,
               appointment.apponum, appointment.appodate
        FROM schedule
        INNER JOIN appointment ON schedule.scheduleid = appointment.scheduleid
        INNER JOIN patient ON patient.pid = appointment.pid
        INNER JOIN doctor ON schedule.docid = doctor.docid
        WHERE schedule.scheduledate >= %s AND schedule.scheduledate <= %s
        ORDER BY schedule.scheduledate ASC
    """, (today, next_week))
    
    upcoming_sessions = db.query_db("""
        SELECT schedule.scheduleid, schedule.title, doctor.docname,
               schedule.scheduledate, schedule.scheduletime, schedule.nop
        FROM schedule
        INNER JOIN doctor ON schedule.docid = doctor.docid
        WHERE schedule.scheduledate >= %s AND schedule.scheduledate <= %s
        ORDER BY schedule.scheduledate ASC
    """, (today, next_week))

    return render_template(
        'admin/index.html',
        today=today,
        next_week_day=get_next_week_day(),
        doctor_count=doc_count,
        patient_count=pat_count,
        appointment_count=app_count,
        schedule_count=sch_count,
        doc_datalist=doc_datalist,
        upcoming_appointments=format_rows(upcoming_appointments),
        upcoming_sessions=format_rows(upcoming_sessions)
    )

@app.route('/admin/doctors', methods=['GET', 'POST'])
@app.route('/admin/doctors.php', methods=['GET', 'POST'])
@login_required('a')
def admin_doctors():
    today = get_today()
    search = request.form.get('search') or request.args.get('search')
    action = request.args.get('action')
    doc_id = request.args.get('id')
    error_code = request.args.get('error', '0')
    name = request.args.get('name', '')
    
    if search:
        query = """
            SELECT doctor.docid, doctor.docname, doctor.docemail, specialties.sname, doctor.docnic, doctor.doctel, doctor.specialties
            FROM doctor
            LEFT JOIN specialties ON doctor.specialties = specialties.id
            WHERE doctor.docname LIKE %s OR doctor.docemail LIKE %s
            ORDER BY doctor.docid DESC
        """
        doctors = db.query_db(query, (f"%{search}%", f"%{search}%"))
    else:
        query = """
            SELECT doctor.docid, doctor.docname, doctor.docemail, specialties.sname, doctor.docnic, doctor.doctel, doctor.specialties
            FROM doctor
            LEFT JOIN specialties ON doctor.specialties = specialties.id
            ORDER BY doctor.docid DESC
        """
        doctors = db.query_db(query)
        
    doc_datalist = db.query_db("SELECT docname, docemail FROM doctor")
    specialties = db.query_db("SELECT * FROM specialties ORDER BY sname ASC")
    
    current_doc = None
    if doc_id:
        current_doc = db.query_db("""
            SELECT doctor.*, specialties.sname
            FROM doctor
            LEFT JOIN specialties ON doctor.specialties = specialties.id
            WHERE doctor.docid = %s
        """, (doc_id,), one=True)

    return render_template(
        'admin/doctors.html',
        today=today,
        search=search,
        doctors=format_rows(doctors),
        doc_datalist=doc_datalist,
        specialties=specialties,
        action=action,
        current_doc=format_row(current_doc),
        id=doc_id,
        error_code=error_code,
        name=name
    )

@app.route('/admin/add-new', methods=['POST'])
@app.route('/admin/add-new.php', methods=['POST'])
@login_required('a')
def admin_add_new():
    name = request.form.get('name', '').strip()
    nic = request.form.get('nic', '').strip()
    spec = request.form.get('spec', '').strip()
    email = request.form.get('email', '').strip()
    tele = request.form.get('Tele', '').strip()
    password = request.form.get('password', '').strip()
    cpassword = request.form.get('cpassword', '').strip()
    
    if password != cpassword:
        return redirect(url_for('admin_doctors', action='add', error='2'))
        
    existing = db.query_db("SELECT * FROM webuser WHERE email = %s", (email,), one=True)
    if existing:
        return redirect(url_for('admin_doctors', action='add', error='1'))
        
    db.execute_db(
        "INSERT INTO doctor (docemail, docname, docpassword, docnic, doctel, specialties) VALUES (%s, %s, %s, %s, %s, %s)",
        (email, name, password, nic, tele, spec)
    )
    db.execute_db("INSERT INTO webuser (email, usertype) VALUES (%s, 'd')", (email,))
    return redirect(url_for('admin_doctors', action='add', error='4'))

@app.route('/admin/edit-doc', methods=['POST'])
@app.route('/admin/edit-doc.php', methods=['POST'])
@login_required('a')
def admin_edit_doc():
    doc_id = request.form.get('id00', '').strip()
    name = request.form.get('name', '').strip()
    nic = request.form.get('nic', '').strip()
    oldemail = request.form.get('oldemail', '').strip()
    spec = request.form.get('spec', '').strip()
    email = request.form.get('email', '').strip()
    tele = request.form.get('Tele', '').strip()
    password = request.form.get('password', '').strip()
    cpassword = request.form.get('cpassword', '').strip()
    
    if password != cpassword:
        return redirect(url_for('admin_doctors', action='edit', id=doc_id, error='2'))
        
    conflict = db.query_db("SELECT docid FROM doctor WHERE docemail = %s AND docid != %s", (email, doc_id), one=True)
    if conflict:
        return redirect(url_for('admin_doctors', action='edit', id=doc_id, error='1'))
        
    db.execute_db(
        "UPDATE doctor SET docemail=%s, docname=%s, docpassword=%s, docnic=%s, doctel=%s, specialties=%s WHERE docid=%s",
        (email, name, password, nic, tele, spec, doc_id)
    )
    db.execute_db("UPDATE webuser SET email=%s WHERE email=%s", (email, oldemail))
    return redirect(url_for('admin_doctors', action='edit', id=doc_id, error='4'))

@app.route('/admin/delete-doctor')
@app.route('/admin/delete-doctor.php')
@login_required('a')
def admin_delete_doctor():
    doc_id = request.args.get('id')
    if doc_id:
        doc = db.query_db("SELECT docemail FROM doctor WHERE docid = %s", (doc_id,), one=True)
        if doc:
            db.execute_db("DELETE FROM webuser WHERE email = %s", (doc['docemail'],))
            db.execute_db("DELETE FROM doctor WHERE docid = %s", (doc_id,))
    return redirect(url_for('admin_doctors'))

@app.route('/admin/schedule', methods=['GET', 'POST'])
@app.route('/admin/schedule.php', methods=['GET', 'POST'])
@login_required('a')
def admin_schedule():
    today = get_today()
    sheduledate = request.form.get('sheduledate') or request.args.get('sheduledate')
    docid = request.form.get('docid') or request.args.get('docid')
    action = request.args.get('action')
    session_id = request.args.get('id')
    titleget = request.args.get('title', '')
    name = request.args.get('name', '')
    
    query = """
        SELECT schedule.scheduleid, schedule.title, doctor.docname,
               schedule.scheduledate, schedule.scheduletime, schedule.nop
        FROM schedule
        INNER JOIN doctor ON schedule.docid = doctor.docid
    """
    params = []
    conditions = []
    if sheduledate:
        conditions.append("schedule.scheduledate = %s")
        params.append(sheduledate)
    if docid:
        conditions.append("doctor.docid = %s")
        params.append(docid)
        
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY schedule.scheduledate DESC"
    
    schedules = db.query_db(query, tuple(params))
    doctors = db.query_db("SELECT * FROM doctor ORDER BY docname ASC")
    
    current_session = None
    registered_patients = []
    if session_id:
        current_session = db.query_db("""
            SELECT schedule.*, doctor.docname
            FROM schedule
            INNER JOIN doctor ON schedule.docid = doctor.docid
            WHERE schedule.scheduleid = %s
        """, (session_id,), one=True)
        
        registered_patients = db.query_db("""
            SELECT patient.pid, patient.pname, appointment.apponum, patient.ptel
            FROM appointment
            INNER JOIN patient ON patient.pid = appointment.pid
            WHERE appointment.scheduleid = %s
        """, (session_id,))

    return render_template(
        'admin/schedule.html',
        today=today,
        sheduledate=sheduledate,
        docid=docid,
        schedules=format_rows(schedules),
        doctors=doctors,
        action=action,
        id=session_id,
        titleget=titleget,
        name=name,
        current_session=format_row(current_session),
        registered_patients=registered_patients
    )

@app.route('/admin/add-session', methods=['POST'])
@app.route('/admin/add-session.php', methods=['POST'])
@login_required('a')
def admin_add_session():
    title = request.form.get('title', '').strip()
    docid = request.form.get('docid', '').strip()
    nop = request.form.get('nop', '').strip()
    date = request.form.get('date', '').strip()
    time = request.form.get('time', '').strip()
    
    db.execute_db(
        "INSERT INTO schedule (docid, title, scheduledate, scheduletime, nop) VALUES (%s, %s, %s, %s, %s)",
        (docid, title, date, time, nop)
    )
    return redirect(url_for('admin_schedule', action='session-added', title=title))

@app.route('/admin/delete-session')
@app.route('/admin/delete-session.php')
@login_required('a')
def admin_delete_session():
    session_id = request.args.get('id')
    if session_id:
        db.execute_db("DELETE FROM appointment WHERE scheduleid = %s", (session_id,))
        db.execute_db("DELETE FROM schedule WHERE scheduleid = %s", (session_id,))
    return redirect(url_for('admin_schedule'))

@app.route('/admin/appointment', methods=['GET', 'POST'])
@app.route('/admin/appointment.php', methods=['GET', 'POST'])
@login_required('a')
def admin_appointment():
    today = get_today()
    sheduledate = request.form.get('sheduledate') or request.args.get('sheduledate')
    docid = request.form.get('docid') or request.args.get('docid')
    action = request.args.get('action')
    appoid = request.args.get('id')
    name = request.args.get('name', '')
    apponum = request.args.get('apponum', '')
    
    query = """
        SELECT appointment.appoid, schedule.scheduleid, schedule.title, doctor.docname,
               patient.pname, schedule.scheduledate, schedule.scheduletime,
               appointment.apponum, appointment.appodate
        FROM schedule
        INNER JOIN appointment ON schedule.scheduleid = appointment.scheduleid
        INNER JOIN patient ON patient.pid = appointment.pid
        INNER JOIN doctor ON schedule.docid = doctor.docid
    """
    params = []
    conditions = []
    if sheduledate:
        conditions.append("schedule.scheduledate = %s")
        params.append(sheduledate)
    if docid:
        conditions.append("doctor.docid = %s")
        params.append(docid)
        
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY schedule.scheduledate DESC"
    
    appointments = db.query_db(query, tuple(params))
    doctors = db.query_db("SELECT * FROM doctor ORDER BY docname ASC")

    return render_template(
        'admin/appointment.html',
        today=today,
        sheduledate=sheduledate,
        docid=docid,
        appointments=format_rows(appointments),
        doctors=doctors,
        action=action,
        id=appoid,
        name=name,
        apponum=apponum
    )

@app.route('/admin/delete-appointment')
@app.route('/admin/delete-appointment.php')
@login_required('a')
def admin_delete_appointment():
    appoid = request.args.get('id')
    if appoid:
        db.execute_db("DELETE FROM appointment WHERE appoid = %s", (appoid,))
    return redirect(url_for('admin_appointment'))

@app.route('/admin/patient', methods=['GET', 'POST'])
@app.route('/admin/patient.php', methods=['GET', 'POST'])
@login_required('a')
def admin_patient():
    today = get_today()
    search = request.form.get('search') or request.args.get('search')
    action = request.args.get('action')
    patient_id = request.args.get('id')
    
    if search:
        patients = db.query_db(
            "SELECT * FROM patient WHERE pemail LIKE %s OR pname LIKE %s ORDER BY pid DESC",
            (f"%{search}%", f"%{search}%")
        )
    else:
        patients = db.query_db("SELECT * FROM patient ORDER BY pid DESC")
        
    patient_datalist = db.query_db("SELECT pname, pemail FROM patient")
    
    current_patient = None
    if patient_id:
        current_patient = db.query_db("SELECT * FROM patient WHERE pid = %s", (patient_id,), one=True)

    return render_template(
        'admin/patient.html',
        today=today,
        search=search,
        patients=format_rows(patients),
        patient_datalist=patient_datalist,
        action=action,
        current_patient=format_row(current_patient)
    )

# ========================================================
# Doctor Routes
# ========================================================

@app.route('/doctor')
@app.route('/doctor/')
@app.route('/doctor/index')
@app.route('/doctor/index.php')
@login_required('d')
def doctor_dashboard():
    today = get_today()
    next_week = get_next_week_date()
    useremail = session.get('user')
    
    doc = db.query_db("SELECT * FROM doctor WHERE docemail = %s", (useremail,), one=True)
    if not doc:
        return redirect(url_for('logout'))
        
    doc_id = doc['docid']
    username = doc['docname']
    
    doc_count = db.query_db("SELECT COUNT(*) AS count FROM doctor", one=True)['count']
    pat_count = db.query_db("SELECT COUNT(*) AS count FROM patient", one=True)['count']
    app_count = db.query_db("""
        SELECT COUNT(*) AS count 
        FROM appointment 
        INNER JOIN schedule ON appointment.scheduleid = schedule.scheduleid 
        WHERE schedule.docid = %s AND appointment.appodate >= %s
    """, (str(doc_id), today), one=True)['count']
    sch_count = db.query_db("SELECT COUNT(*) AS count FROM schedule WHERE docid = %s AND scheduledate = %s", (str(doc_id), today), one=True)['count']
    
    upcoming_sessions = db.query_db("""
        SELECT schedule.scheduleid, schedule.title, doctor.docname,
               schedule.scheduledate, schedule.scheduletime, schedule.nop
        FROM schedule
        INNER JOIN doctor ON schedule.docid = doctor.docid
        WHERE schedule.docid = %s AND schedule.scheduledate >= %s AND schedule.scheduledate <= %s
        ORDER BY schedule.scheduledate DESC
    """, (str(doc_id), today, next_week))

    return render_template(
        'doctor/index.html',
        today=today,
        username=username,
        useremail=useremail,
        doctor_count=doc_count,
        patient_count=pat_count,
        appointment_count=app_count,
        schedule_count=sch_count,
        upcoming_sessions=format_rows(upcoming_sessions)
    )

@app.route('/doctor/appointment', methods=['GET', 'POST'])
@app.route('/doctor/appointment.php', methods=['GET', 'POST'])
@login_required('d')
def doctor_appointment():
    today = get_today()
    useremail = session.get('user')
    doc = db.query_db("SELECT * FROM doctor WHERE docemail = %s", (useremail,), one=True)
    doc_id = str(doc['docid'])
    
    sheduledate = request.form.get('sheduledate') or request.args.get('sheduledate')
    action = request.args.get('action')
    appoid = request.args.get('id')
    name = request.args.get('name', '')
    apponum = request.args.get('apponum', '')
    
    query = """
        SELECT appointment.appoid, schedule.scheduleid, schedule.title,
               patient.pname, schedule.scheduledate, schedule.scheduletime,
               appointment.apponum, appointment.appodate
        FROM schedule
        INNER JOIN appointment ON schedule.scheduleid = appointment.scheduleid
        INNER JOIN patient ON patient.pid = appointment.pid
        WHERE schedule.docid = %s
    """
    params = [doc_id]
    if sheduledate:
        query += " AND schedule.scheduledate = %s"
        params.append(sheduledate)
    query += " ORDER BY schedule.scheduledate DESC"
    
    appointments = db.query_db(query, tuple(params))

    return render_template(
        'doctor/appointment.html',
        today=today,
        username=doc['docname'],
        useremail=useremail,
        sheduledate=sheduledate,
        appointments=format_rows(appointments),
        action=action,
        id=appoid,
        name=name,
        apponum=apponum
    )

@app.route('/doctor/delete-appointment')
@app.route('/doctor/delete-appointment.php')
@login_required('d')
def doctor_delete_appointment():
    appoid = request.args.get('id')
    useremail = session.get('user')
    doc = db.query_db("SELECT docid FROM doctor WHERE docemail = %s", (useremail,), one=True)
    if appoid and doc:
        db.execute_db("""
            DELETE FROM appointment 
            WHERE appoid = %s AND scheduleid IN (SELECT scheduleid FROM schedule WHERE docid = %s)
        """, (appoid, str(doc['docid'])))
    return redirect(url_for('doctor_appointment'))

@app.route('/doctor/schedule', methods=['GET', 'POST'])
@app.route('/doctor/schedule.php', methods=['GET', 'POST'])
@login_required('d')
def doctor_schedule():
    today = get_today()
    useremail = session.get('user')
    doc = db.query_db("SELECT * FROM doctor WHERE docemail = %s", (useremail,), one=True)
    doc_id = str(doc['docid'])
    
    sheduledate = request.form.get('sheduledate') or request.args.get('sheduledate')
    action = request.args.get('action')
    session_id = request.args.get('id')
    name = request.args.get('name', '')
    
    query = """
        SELECT schedule.scheduleid, schedule.title, schedule.scheduledate, schedule.scheduletime, schedule.nop
        FROM schedule
        WHERE schedule.docid = %s
    """
    params = [doc_id]
    if sheduledate:
        query += " AND schedule.scheduledate = %s"
        params.append(sheduledate)
    query += " ORDER BY schedule.scheduledate DESC"
    
    schedules = db.query_db(query, tuple(params))
    
    current_session = None
    registered_patients = []
    if session_id:
        current_session = db.query_db("SELECT * FROM schedule WHERE scheduleid = %s AND docid = %s", (session_id, doc_id), one=True)
        if current_session:
            registered_patients = db.query_db("""
                SELECT patient.pid, patient.pname, appointment.apponum, patient.ptel
                FROM appointment
                INNER JOIN patient ON patient.pid = appointment.pid
                WHERE appointment.scheduleid = %s
            """, (session_id,))

    return render_template(
        'doctor/schedule.html',
        today=today,
        username=doc['docname'],
        useremail=useremail,
        sheduledate=sheduledate,
        schedules=format_rows(schedules),
        action=action,
        id=session_id,
        name=name,
        current_session=format_row(current_session),
        registered_patients=registered_patients
    )

@app.route('/doctor/delete-session')
@app.route('/doctor/delete-session.php')
@login_required('d')
def doctor_delete_session():
    session_id = request.args.get('id')
    useremail = session.get('user')
    doc = db.query_db("SELECT docid FROM doctor WHERE docemail = %s", (useremail,), one=True)
    if session_id and doc:
        db.execute_db("DELETE FROM appointment WHERE scheduleid = %s", (session_id,))
        db.execute_db("DELETE FROM schedule WHERE scheduleid = %s AND docid = %s", (session_id, str(doc['docid'])))
    return redirect(url_for('doctor_schedule'))

@app.route('/doctor/patient', methods=['GET', 'POST'])
@app.route('/doctor/patient.php', methods=['GET', 'POST'])
@login_required('d')
def doctor_patient():
    today = get_today()
    useremail = session.get('user')
    doc = db.query_db("SELECT * FROM doctor WHERE docemail = %s", (useremail,), one=True)
    doc_id = str(doc['docid'])
    
    search = request.form.get('search') or request.args.get('search')
    showonly = request.form.get('showonly', 'my')
    action = request.args.get('action')
    patient_id = request.args.get('id')
    
    filter_type_text = "My" if showonly == 'my' else "All"
    
    if showonly == 'my':
        base_query = """
            SELECT DISTINCT patient.*
            FROM appointment
            INNER JOIN patient ON patient.pid = appointment.pid
            INNER JOIN schedule ON schedule.scheduleid = appointment.scheduleid
            WHERE schedule.docid = %s
        """
        params = [doc_id]
        if search:
            base_query += " AND (patient.pname LIKE %s OR patient.pemail LIKE %s)"
            params.extend([f"%{search}%", f"%{search}%"])
    else:
        base_query = "SELECT * FROM patient WHERE 1=1"
        params = []
        if search:
            base_query += " AND (pname LIKE %s OR pemail LIKE %s)"
            params.extend([f"%{search}%", f"%{search}%"])
            
    base_query += " ORDER BY pid DESC"
    patients = db.query_db(base_query, tuple(params))
    patient_datalist = db.query_db("SELECT pname, pemail FROM patient")
    
    current_patient = None
    if patient_id:
        current_patient = db.query_db("SELECT * FROM patient WHERE pid = %s", (patient_id,), one=True)

    return render_template(
        'doctor/patient.html',
        today=today,
        username=doc['docname'],
        useremail=useremail,
        search=search,
        showonly=showonly,
        filter_type_text=filter_type_text,
        patients=format_rows(patients),
        patient_datalist=patient_datalist,
        action=action,
        current_patient=format_row(current_patient)
    )

@app.route('/doctor/settings')
@app.route('/doctor/settings.php')
@login_required('d')
def doctor_settings():
    today = get_today()
    useremail = session.get('user')
    action = request.args.get('action')
    error_code = request.args.get('error', '0')
    name = request.args.get('name', '')
    
    doc = db.query_db("""
        SELECT doctor.*, specialties.sname
        FROM doctor
        LEFT JOIN specialties ON doctor.specialties = specialties.id
        WHERE doctor.docemail = %s
    """, (useremail,), one=True)
    
    specialties = db.query_db("SELECT * FROM specialties ORDER BY sname ASC")

    return render_template(
        'doctor/settings.html',
        today=today,
        username=doc['docname'],
        useremail=useremail,
        current_doc=format_row(doc),
        specialties=specialties,
        action=action,
        error_code=error_code,
        name=name,
        id=doc['docid']
    )

@app.route('/doctor/edit-doc', methods=['POST'])
@app.route('/doctor/edit-doc.php', methods=['POST'])
@login_required('d')
def doctor_edit_doc():
    doc_id = request.form.get('id00', '').strip()
    name = request.form.get('name', '').strip()
    nic = request.form.get('nic', '').strip()
    oldemail = request.form.get('oldemail', '').strip()
    spec = request.form.get('spec', '').strip()
    email = request.form.get('email', '').strip()
    tele = request.form.get('Tele', '').strip()
    password = request.form.get('password', '').strip()
    cpassword = request.form.get('cpassword', '').strip()
    
    if password != cpassword:
        return redirect(url_for('doctor_settings', action='edit', id=doc_id, error='2'))
        
    conflict = db.query_db("SELECT docid FROM doctor WHERE docemail = %s AND docid != %s", (email, doc_id), one=True)
    if conflict:
        return redirect(url_for('doctor_settings', action='edit', id=doc_id, error='1'))
        
    db.execute_db(
        "UPDATE doctor SET docemail=%s, docname=%s, docpassword=%s, docnic=%s, doctel=%s, specialties=%s WHERE docid=%s",
        (email, name, password, nic, tele, spec, doc_id)
    )
    db.execute_db("UPDATE webuser SET email=%s WHERE email=%s", (email, oldemail))
    session['user'] = email
    session['username'] = name
    return redirect(url_for('doctor_settings', action='edit', id=doc_id, error='4'))

@app.route('/doctor/delete-account')
@app.route('/doctor/delete-account.php')
@login_required('d')
def doctor_delete_account():
    useremail = session.get('user')
    doc = db.query_db("SELECT docid FROM doctor WHERE docemail = %s", (useremail,), one=True)
    if doc:
        db.execute_db("DELETE FROM appointment WHERE scheduleid IN (SELECT scheduleid FROM schedule WHERE docid = %s)", (str(doc['docid']),))
        db.execute_db("DELETE FROM schedule WHERE docid = %s", (str(doc['docid']),))
        db.execute_db("DELETE FROM webuser WHERE email = %s", (useremail,))
        db.execute_db("DELETE FROM doctor WHERE docid = %s", (doc['docid'],))
    return redirect(url_for('logout'))

# ========================================================
# Patient Routes
# ========================================================

@app.route('/patient')
@app.route('/patient/')
@app.route('/patient/index')
@app.route('/patient/index.php')
@login_required('p')
def patient_dashboard():
    today = get_today()
    useremail = session.get('user')
    patient = db.query_db("SELECT * FROM patient WHERE pemail = %s", (useremail,), one=True)
    if not patient:
        return redirect(url_for('logout'))
        
    pid = patient['pid']
    username = patient['pname']
    
    doc_count = db.query_db("SELECT COUNT(*) AS count FROM doctor", one=True)['count']
    pat_count = db.query_db("SELECT COUNT(*) AS count FROM patient", one=True)['count']
    app_count = db.query_db("SELECT COUNT(*) AS count FROM appointment WHERE appodate >= %s", (today,), one=True)['count']
    sch_count = db.query_db("SELECT COUNT(*) AS count FROM schedule WHERE scheduledate = %s", (today,), one=True)['count']
    
    doc_datalist = db.query_db("SELECT docname, docemail FROM doctor")
    
    upcoming_appointments = db.query_db("""
        SELECT appointment.appoid, schedule.scheduleid, schedule.title, doctor.docname,
               schedule.scheduledate, schedule.scheduletime, appointment.apponum, appointment.appodate
        FROM schedule
        INNER JOIN appointment ON schedule.scheduleid = appointment.scheduleid
        INNER JOIN doctor ON schedule.docid = doctor.docid
        WHERE appointment.pid = %s AND schedule.scheduledate >= %s
        ORDER BY schedule.scheduledate ASC
    """, (pid, today))

    return render_template(
        'patient/index.html',
        today=today,
        username=username,
        useremail=useremail,
        doctor_count=doc_count,
        patient_count=pat_count,
        appointment_count=app_count,
        schedule_count=sch_count,
        doc_datalist=doc_datalist,
        upcoming_appointments=format_rows(upcoming_appointments)
    )

@app.route('/patient/doctors', methods=['GET', 'POST'])
@app.route('/patient/doctors.php', methods=['GET', 'POST'])
@login_required('p')
def patient_doctors():
    today = get_today()
    useremail = session.get('user')
    patient = db.query_db("SELECT * FROM patient WHERE pemail = %s", (useremail,), one=True)
    
    search = request.form.get('search') or request.args.get('search')
    action = request.args.get('action')
    doc_id = request.args.get('id')
    name = request.args.get('name', '')
    
    if search:
        query = """
            SELECT doctor.docid, doctor.docname, doctor.docemail, specialties.sname, doctor.docnic, doctor.doctel
            FROM doctor
            LEFT JOIN specialties ON doctor.specialties = specialties.id
            WHERE doctor.docname LIKE %s OR specialties.sname LIKE %s
            ORDER BY doctor.docid DESC
        """
        doctors = db.query_db(query, (f"%{search}%", f"%{search}%"))
    else:
        query = """
            SELECT doctor.docid, doctor.docname, doctor.docemail, specialties.sname, doctor.docnic, doctor.doctel
            FROM doctor
            LEFT JOIN specialties ON doctor.specialties = specialties.id
            ORDER BY doctor.docid DESC
        """
        doctors = db.query_db(query)
        
    doc_datalist = db.query_db("SELECT docname, docemail FROM doctor")
    
    current_doc = None
    if doc_id:
        current_doc = db.query_db("""
            SELECT doctor.*, specialties.sname
            FROM doctor
            LEFT JOIN specialties ON doctor.specialties = specialties.id
            WHERE doctor.docid = %s
        """, (doc_id,), one=True)

    return render_template(
        'patient/doctors.html',
        today=today,
        username=patient['pname'],
        useremail=useremail,
        search=search,
        doctors=format_rows(doctors),
        doc_datalist=doc_datalist,
        action=action,
        current_doc=format_row(current_doc),
        id=doc_id,
        name=name
    )

@app.route('/patient/schedule', methods=['GET', 'POST'])
@app.route('/patient/schedule.php', methods=['GET', 'POST'])
@login_required('p')
def patient_schedule():
    today = get_today()
    useremail = session.get('user')
    patient = db.query_db("SELECT * FROM patient WHERE pemail = %s", (useremail,), one=True)
    
    search = request.form.get('search') or request.args.get('search')
    
    query = """
        SELECT schedule.scheduleid, schedule.title, doctor.docname,
               schedule.scheduledate, schedule.scheduletime, schedule.nop
        FROM schedule
        INNER JOIN doctor ON schedule.docid = doctor.docid
        WHERE schedule.scheduledate >= %s
    """
    params = [today]
    if search:
        query += " AND (doctor.docname LIKE %s OR schedule.title LIKE %s OR schedule.scheduledate = %s)"
        params.extend([f"%{search}%", f"%{search}%", search])
    query += " ORDER BY schedule.scheduledate ASC"
    
    schedules = db.query_db(query, tuple(params))
    
    # Datalist for search
    docs = db.query_db("SELECT DISTINCT docname FROM doctor")
    titles = db.query_db("SELECT DISTINCT title FROM schedule")
    doctor_titles = [d['docname'] for d in docs] + [t['title'] for t in titles]

    return render_template(
        'patient/schedule.html',
        today=today,
        username=patient['pname'],
        useremail=useremail,
        search=search,
        search_type="Search Result" if search else "All",
        schedules=format_rows(schedules),
        doctor_titles=doctor_titles
    )

@app.route('/patient/booking')
@app.route('/patient/booking.php')
@login_required('p')
def patient_booking():
    today = get_today()
    useremail = session.get('user')
    patient = db.query_db("SELECT * FROM patient WHERE pemail = %s", (useremail,), one=True)
    schedule_id = request.args.get('id')
    
    if not schedule_id:
        return redirect(url_for('patient_schedule'))
        
    current_session = db.query_db("""
        SELECT schedule.*, doctor.docname, doctor.docemail
        FROM schedule
        INNER JOIN doctor ON schedule.docid = doctor.docid
        WHERE schedule.scheduleid = %s
    """, (schedule_id,), one=True)
    
    if not current_session:
        return redirect(url_for('patient_schedule'))
        
    count_res = db.query_db("SELECT COUNT(*) AS count FROM appointment WHERE scheduleid = %s", (schedule_id,), one=True)
    apponum = (count_res['count'] if count_res else 0) + 1
    
    docs = db.query_db("SELECT DISTINCT docname FROM doctor")
    titles = db.query_db("SELECT DISTINCT title FROM schedule")
    doctor_titles = [d['docname'] for d in docs] + [t['title'] for t in titles]

    return render_template(
        'patient/booking.html',
        today=today,
        username=patient['pname'],
        useremail=useremail,
        current_session=format_row(current_session),
        apponum=apponum,
        doctor_titles=doctor_titles
    )

@app.route('/patient/booking-complete', methods=['POST'])
@app.route('/patient/booking-complete.php', methods=['POST'])
@login_required('p')
def patient_booking_complete():
    useremail = session.get('user')
    patient = db.query_db("SELECT pid FROM patient WHERE pemail = %s", (useremail,), one=True)
    pid = patient['pid']
    
    apponum = request.form.get('apponum')
    scheduleid = request.form.get('scheduleid')
    date = request.form.get('date', get_today())
    
    db.execute_db(
        "INSERT INTO appointment (pid, apponum, scheduleid, appodate) VALUES (%s, %s, %s, %s)",
        (pid, apponum, scheduleid, date)
    )
    return redirect(url_for('patient_appointment', action='booking-added', id=apponum))

@app.route('/patient/appointment', methods=['GET', 'POST'])
@app.route('/patient/appointment.php', methods=['GET', 'POST'])
@login_required('p')
def patient_appointment():
    today = get_today()
    useremail = session.get('user')
    patient = db.query_db("SELECT * FROM patient WHERE pemail = %s", (useremail,), one=True)
    pid = patient['pid']
    
    sheduledate = request.form.get('sheduledate') or request.args.get('sheduledate')
    action = request.args.get('action')
    appoid = request.args.get('id')
    title = request.args.get('title', '')
    docname = request.args.get('doc', '')
    
    query = """
        SELECT appointment.appoid, schedule.scheduleid, schedule.title, doctor.docname,
               patient.pname, schedule.scheduledate, schedule.scheduletime,
               appointment.apponum, appointment.appodate
        FROM schedule
        INNER JOIN appointment ON schedule.scheduleid = appointment.scheduleid
        INNER JOIN patient ON patient.pid = appointment.pid
        INNER JOIN doctor ON schedule.docid = doctor.docid
        WHERE patient.pid = %s
    """
    params = [pid]
    if sheduledate:
        query += " AND schedule.scheduledate = %s"
        params.append(sheduledate)
    query += " ORDER BY appointment.appodate ASC"
    
    appointments = db.query_db(query, tuple(params))

    return render_template(
        'patient/appointment.html',
        today=today,
        username=patient['pname'],
        useremail=useremail,
        sheduledate=sheduledate,
        appointments=format_rows(appointments),
        action=action,
        id=appoid,
        title=title,
        docname=docname
    )

@app.route('/patient/delete-appointment')
@app.route('/patient/delete-appointment.php')
@login_required('p')
def patient_delete_appointment():
    appoid = request.args.get('id')
    useremail = session.get('user')
    patient = db.query_db("SELECT pid FROM patient WHERE pemail = %s", (useremail,), one=True)
    if appoid and patient:
        db.execute_db("DELETE FROM appointment WHERE appoid = %s AND pid = %s", (appoid, patient['pid']))
    return redirect(url_for('patient_appointment'))

@app.route('/patient/settings')
@app.route('/patient/settings.php')
@login_required('p')
def patient_settings():
    today = get_today()
    useremail = session.get('user')
    action = request.args.get('action')
    error_code = request.args.get('error', '0')
    name = request.args.get('name', '')
    
    patient = db.query_db("SELECT * FROM patient WHERE pemail = %s", (useremail,), one=True)

    return render_template(
        'patient/settings.html',
        today=today,
        username=patient['pname'],
        useremail=useremail,
        current_patient=format_row(patient),
        action=action,
        error_code=error_code,
        name=name,
        id=patient['pid']
    )

@app.route('/patient/edit-user', methods=['POST'])
@app.route('/patient/edit-user.php', methods=['POST'])
@login_required('p')
def patient_edit_user():
    pid = request.form.get('id00', '').strip()
    name = request.form.get('name', '').strip()
    nic = request.form.get('nic', '').strip()
    oldemail = request.form.get('oldemail', '').strip()
    address = request.form.get('address', '').strip()
    email = request.form.get('email', '').strip()
    tele = request.form.get('Tele', '').strip()
    password = request.form.get('password', '').strip()
    cpassword = request.form.get('cpassword', '').strip()
    
    if password != cpassword:
        return redirect(url_for('patient_settings', action='edit', id=pid, error='2'))
        
    conflict = db.query_db("SELECT pid FROM patient WHERE pemail = %s AND pid != %s", (email, pid), one=True)
    if conflict:
        return redirect(url_for('patient_settings', action='edit', id=pid, error='1'))
        
    db.execute_db(
        "UPDATE patient SET pemail=%s, pname=%s, ppassword=%s, pnic=%s, ptel=%s, paddress=%s WHERE pid=%s",
        (email, name, password, nic, tele, address, pid)
    )
    db.execute_db("UPDATE webuser SET email=%s WHERE email=%s", (email, oldemail))
    session['user'] = email
    session['username'] = name
    return redirect(url_for('patient_settings', action='edit', id=pid, error='4'))

@app.route('/patient/delete-account')
@app.route('/patient/delete-account.php')
@login_required('p')
def patient_delete_account():
    useremail = session.get('user')
    patient = db.query_db("SELECT pid FROM patient WHERE pemail = %s", (useremail,), one=True)
    if patient:
        pid = patient['pid']
        db.execute_db("DELETE FROM appointment WHERE pid = %s", (pid,))
        db.execute_db("DELETE FROM webuser WHERE email = %s", (useremail,))
        db.execute_db("DELETE FROM patient WHERE pid = %s", (pid,))
    return redirect(url_for('logout'))

# ========================================================
# Run Application
# ========================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() in ['1', 'true']
    print(f"Starting eDoc Flask app on http://127.0.0.1:{port} ...")
    app.run(host='127.0.0.1', port=port, debug=debug)
