import os
import sqlite3
import pymysql
import pymysql.cursors
from flask import g

# Helper to load .env variables manually without external dependencies
def load_env(filepath=None):
    if filepath is None:
        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, val = line.split('=', 1)
                key = key.strip()
                val = val.strip().strip('"\'')
                if key not in os.environ:
                    os.environ[key] = val

load_env()

DB_TYPE = os.environ.get('DB_TYPE', 'mysql').lower()
DB_HOST = os.environ.get('DB_HOST', '127.0.0.1')
DB_PORT = int(os.environ.get('DB_PORT', 3306))
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'admin123')
DB_NAME = os.environ.get('DB_NAME', 'edoc')
SQLITE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'edoc.db')

def init_sqlite_db(conn):
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS admin (
        aemail TEXT PRIMARY KEY,
        apassword TEXT
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS doctor (
        docid INTEGER PRIMARY KEY AUTOINCREMENT,
        docemail TEXT,
        docname TEXT,
        docpassword TEXT,
        docnic TEXT,
        doctel TEXT,
        specialties INTEGER
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS patient (
        pid INTEGER PRIMARY KEY AUTOINCREMENT,
        pemail TEXT,
        pname TEXT,
        ppassword TEXT,
        paddress TEXT,
        pnic TEXT,
        pdob TEXT,
        ptel TEXT
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS schedule (
        scheduleid INTEGER PRIMARY KEY AUTOINCREMENT,
        docid TEXT,
        title TEXT,
        scheduledate TEXT,
        scheduletime TEXT,
        nop INTEGER
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS appointment (
        appoid INTEGER PRIMARY KEY AUTOINCREMENT,
        pid INTEGER,
        apponum INTEGER,
        scheduleid INTEGER,
        appodate TEXT
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS specialties (
        id INTEGER PRIMARY KEY,
        sname TEXT
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS webuser (
        email TEXT PRIMARY KEY,
        usertype TEXT
    )
    ''')
    
    # Check if admin exists, if not seed defaults
    cur.execute("SELECT COUNT(*) FROM admin")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO admin (aemail, apassword) VALUES ('admin@edoc.com', '123')")
        cur.execute("INSERT INTO webuser (email, usertype) VALUES ('admin@edoc.com', 'a')")
        
        cur.execute("INSERT INTO doctor (docid, docemail, docname, docpassword, docnic, doctel, specialties) VALUES (1, 'doctor@edoc.com', 'Test Doctor', '123', '000000000', '0110000000', 1)")
        cur.execute("INSERT INTO webuser (email, usertype) VALUES ('doctor@edoc.com', 'd')")
        
        cur.execute("INSERT INTO patient (pid, pemail, pname, ppassword, paddress, pnic, pdob, ptel) VALUES (1, 'patient@edoc.com', 'Test Patient', '123', 'Sri Lanka', '0000000000', '2000-01-01', '0120000000')")
        cur.execute("INSERT INTO webuser (email, usertype) VALUES ('patient@edoc.com', 'p')")
        
        cur.execute("INSERT INTO schedule (scheduleid, docid, title, scheduledate, scheduletime, nop) VALUES (1, '1', 'Test Session', '2050-01-01', '18:00:00', 50)")
        cur.execute("INSERT INTO appointment (appoid, pid, apponum, scheduleid, appodate) VALUES (1, 1, 1, 1, '2022-06-03')")
        
        specialties_data = [
            (1, 'Accident and emergency medicine'), (2, 'Allergology'), (3, 'Anaesthetics'),
            (4, 'Biological hematology'), (5, 'Cardiology'), (6, 'Child psychiatry'),
            (7, 'Clinical biology'), (8, 'Clinical chemistry'), (9, 'Clinical neurophysiology'),
            (10, 'Clinical radiology'), (11, 'Dental, oral and maxillo-facial surgery'),
            (12, 'Dermato-venerology'), (13, 'Dermatology'), (14, 'Endocrinology'),
            (15, 'Gastro-enterologic surgery'), (16, 'Gastroenterology'), (17, 'General hematology'),
            (18, 'General Practice'), (19, 'General surgery'), (20, 'Geriatrics'),
            (21, 'Immunology'), (22, 'Infectious diseases'), (23, 'Internal medicine'),
            (24, 'Laboratory medicine'), (25, 'Maxillo-facial surgery'), (26, 'Microbiology'),
            (27, 'Nephrology'), (28, 'Neuro-psychiatry'), (29, 'Neurology'),
            (30, 'Neurosurgery'), (31, 'Nuclear medicine'), (32, 'Obstetrics and gynecology'),
            (33, 'Occupational medicine'), (34, 'Ophthalmology'), (35, 'Orthopaedics'),
            (36, 'Otorhinolaryngology'), (37, 'Paediatric surgery'), (38, 'Paediatrics'),
            (39, 'Pathology'), (40, 'Pharmacology'), (41, 'Physical medicine and rehabilitation'),
            (42, 'Plastic surgery'), (43, 'Podiatric Medicine'), (44, 'Podiatric Surgery'),
            (45, 'Psychiatry'), (46, 'Public health and Preventive Medicine'),
            (47, 'Radiology'), (48, 'Radiotherapy'), (49, 'Respiratory medicine'),
            (50, 'Rheumatology'), (51, 'Stomatology'), (52, 'Thoracic surgery'),
            (53, 'Tropical medicine'), (54, 'Urology'), (55, 'Vascular surgery'),
            (56, 'Venereology')
        ]
        cur.executemany("INSERT OR IGNORE INTO specialties (id, sname) VALUES (?, ?)", specialties_data)
        conn.commit()

def get_db():
    if 'db' not in g:
        if DB_TYPE == 'mysql':
            try:
                g.db = pymysql.connect(
                    host=DB_HOST,
                    port=DB_PORT,
                    user=DB_USER,
                    password=DB_PASSWORD,
                    database=DB_NAME,
                    cursorclass=pymysql.cursors.DictCursor,
                    autocommit=True
                )
                g.db_type = 'mysql'
                return g.db
            except Exception as e:
                # If MySQL fails, fallback to SQLite
                print(f"[DB Warning] Could not connect to MySQL ({e}). Falling back to SQLite.")
                conn = sqlite3.connect(SQLITE_PATH)
                conn.row_factory = sqlite3.Row
                init_sqlite_db(conn)
                g.db = conn
                g.db_type = 'sqlite'
                return g.db
        else:
            conn = sqlite3.connect(SQLITE_PATH)
            conn.row_factory = sqlite3.Row
            init_sqlite_db(conn)
            g.db = conn
            g.db_type = 'sqlite'
            return g.db
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        try:
            db.close()
        except Exception:
            pass

def query_db(query, args=(), one=False):
    db = get_db()
    db_type = getattr(g, 'db_type', 'mysql')
    if db_type == 'sqlite':
        query = query.replace('%s', '?')
        cur = db.cursor()
        cur.execute(query, args)
        rv = [dict(row) for row in cur.fetchall()]
        cur.close()
        return (rv[0] if rv else None) if one else rv
    else:
        with db.cursor() as cur:
            cur.execute(query, args)
            rv = cur.fetchall()
            return (rv[0] if rv else None) if one else rv

def execute_db(query, args=()):
    db = get_db()
    db_type = getattr(g, 'db_type', 'mysql')
    if db_type == 'sqlite':
        query = query.replace('%s', '?')
        cur = db.cursor()
        cur.execute(query, args)
        db.commit()
        last_id = cur.lastrowid
        cur.close()
        return last_id
    else:
        with db.cursor() as cur:
            cur.execute(query, args)
            db.commit()
            return cur.lastrowid

