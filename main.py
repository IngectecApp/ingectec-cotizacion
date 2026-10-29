import flet as ft
import psycopg2
import os
import shutil
import re
import json
import qrcode
import textwrap
import platform
import subprocess
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from datetime import datetime

PORT = int(os.environ.get("PORT", 8080))
if not os.path.exists("assets"): os.makedirs("assets")

DB_URL = os.environ.get("DATABASE_URL", "postgresql://ingectec_bd_user:HY7iwKhvaILCeuUKd7Pgknsh6Nsv4aUE@dpg-dapicrvf3r2c73ep15ag-a.oregon-postgres.render.com/ingectec_bd")

def conectar_db():
    try:
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True 
        return conn
    except: return None

def init_db():
    conn = conectar_db()
    if conn:
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS usuarios (usuario TEXT PRIMARY KEY, password TEXT, rol TEXT, intentos INTEGER DEFAULT 0, bloqueado INTEGER DEFAULT 0)")
        try: c.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS sesion_activa INTEGER DEFAULT 0")
        except: pass
        try: c.execute("UPDATE usuarios SET sesion_activa = 0")
        except: pass
        c.execute("DELETE FROM usuarios WHERE usuario IN ('OSCAR', 'YEISON', 'PAULO', 'JOHN', 'JHON')")
        c.execute("INSERT INTO usuarios (usuario, password, rol, intentos, bloqueado) VALUES ('OMERA', '1234', 'ADMIN', 0, 0) ON CONFLICT DO NOTHING")
        c.execute("INSERT INTO usuarios (usuario, password, rol, intentos, bloqueado) VALUES ('YRESTREPO', '1234', 'ADMIN', 0, 0) ON CONFLICT DO NOTHING")
        c.execute("INSERT INTO usuarios (usuario, password, rol, intentos, bloqueado) VALUES ('JCARDONA', '1234', 'ADMIN', 0, 0) ON CONFLICT DO NOTHING")
        c.execute("INSERT INTO usuarios (usuario, password, rol, intentos, bloqueado) VALUES ('PLEAL', '1234', 'ADMIN', 0, 0) ON CONFLICT DO NOTHING")
        c.execute("CREATE TABLE IF NOT EXISTS n_cot (id SERIAL PRIMARY KEY, num INTEGER)")
        c.execute("INSERT INTO n_cot (id, num) VALUES (1, 100) ON CONFLICT DO NOTHING")
        c.execute("CREATE TABLE IF NOT EXISTS cli (n TEXT PRIMARY KEY, i TEXT, dir TEXT, email TEXT, ciu TEXT, tel TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS inv (d TEXT PRIMARY KEY, p NUMERIC, stock NUMERIC)")
        for col, tipo in [("proveedor", "TEXT"), ("fecha_act", "TEXT")]:
            try: c.execute(f"ALTER TABLE inv ADD COLUMN IF NOT EXISTS {col} {tipo}")
            except: pass
        c.execute("CREATE TABLE IF NOT EXISTS proveedores (nombre TEXT PRIMARY KEY, telefono TEXT)")
        c.execute("SELECT count(*) FROM proveedores")
        if c.fetchone()[0] == 0:
            for p_n, p_t in [("MECATRONIC", ""), ("RG REDES", ""), ("SMT INTERNACIONAL", ""), ("DON ELECTRICO", "")]:
                c.execute("INSERT INTO proveedores (nombre, telefono) VALUES (%s, %s) ON CONFLICT DO NOTHING", (p_n, p_t))
        c.execute("CREATE TABLE IF NOT EXISTS historial (nro TEXT PRIMARY KEY, cliente TEXT, fecha TEXT, archivo TEXT, total NUMERIC, origen TEXT, creador TEXT)")
        try: c.execute("ALTER TABLE historial ADD COLUMN IF NOT EXISTS permitidos TEXT DEFAULT ''")
        except: pass
        c.execute("""CREATE TABLE IF NOT EXISTS h_cab (nro TEXT PRIMARY KEY, cli TEXT, nit TEXT, atn TEXT, ref TEXT, ciu_origen TEXT, t_entrega TEXT, validez TEXT, pago TEXT, garantia TEXT, notas TEXT, modo TEXT, pct_a NUMERIC, pct_i NUMERIC, pct_u NUMERIC, pct_iva_u NUMERIC)""")
        for col, tipo in [("atn", "TEXT"), ("ref", "TEXT"), ("ciu_origen", "TEXT"), ("t_entrega", "TEXT"), ("validez", "TEXT"), ("pago", "TEXT"), ("garantia", "TEXT"), ("notas", "TEXT"), ("modo", "TEXT"), ("pct_a", "NUMERIC"), ("pct_i", "NUMERIC"), ("pct_u", "NUMERIC"), ("pct_iva_u", "NUMERIC"), ("pct_ganancia", "NUMERIC DEFAULT 0")]:
            try: c.execute(f"ALTER TABLE h_cab ADD COLUMN IF NOT EXISTS {col} {tipo}")
            except: pass
        c.execute('CREATE TABLE IF NOT EXISTS h_det (id SERIAL PRIMARY KEY, nro TEXT, "desc" TEXT, cant NUMERIC, und TEXT, unit NUMERIC, sub NUMERIC, imp TEXT, tipo TEXT)')
        conn.close()

init_db()

def sanitizar_texto(texto):
    if not texto: return ""
    s = str(texto)
    for orig, nuevo in {"•": "-", "·": "-", "–": "-", "—": "-", "“": '"', "”": '"', "‘": "'", "’": "'", "…": "...", "€": "EUR"}.items(): 
        s = s.replace(orig, nuevo)
    correcciones = {r"\bBALVULA\b": "VÁLVULA", r"\bBALVULAS\b": "VÁLVULAS", r"\bTAVLERO\b": "TABLERO", r"\bTAVLEROS\b": "TABLEROS", r"\bBOLTIOS\b": "VOLTIOS", r"\bBOLTAJE\b": "VOLTAJE", r"\bTUBERIA\b": "TUBERÍA", r"\bGAVINETE\b": "GABINETE", r"\bINTERUPTOR\b": "INTERRUPTOR", r"\bCONECCION\