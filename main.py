import flet as ft
import sqlite3
import os
import shutil
import re
import qrcode
import textwrap
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from datetime import datetime

PORT = int(os.environ.get("PORT", 8080))
if not os.path.exists("assets"): os.makedirs("assets")

# --- CLASE PDF ORIGINAL DE INGECTEC ---
class PDF(FPDF):
    def rounded_rect(self, x, y, w, h, r, style='F'):
        if style == 'F':
            self.rect(x + r, y, w - 2 * r, h, style='F')
            self.rect(x, y + r, w, h - 2 * r, style='F')
            self.ellipse(x, y, 2 * r, 2 * r, style='F')
            self.ellipse(x + w - 2 * r, y, 2 * r, 2 * r, style='F')
            self.ellipse(x, y + h - 2 * r, 2 * r, 2 * r, style='F')
            self.ellipse(x + w - 2 * r, y + h - 2 * r, 2 * r, 2 * r, style='F')

    def header(self):
        rutas_posibles = ["logo pl.png", "logopl.png", "logo.png", "logo1.png"]
        for ruta in rutas_posibles:
            if os.path.exists(ruta):
                try: 
                    self.image(ruta, x=10, y=8, w=190)
                    break 
                except: pass
        self.set_y(40) 
        
    def footer(self):
        self.set_y(-28)
        if hasattr(self, 'asesor_nombre') and self.asesor_nombre:
            self.set_font('helvetica', '', 7)
            self.set_text_color(210, 210, 210)
            self.set_x(30)
            self.cell(0, 3, f"Cod. Asesor: {self.asesor_nombre}", border=0, align='L')
            
        self.set_y(-25)
        self.set_font('helvetica', '', 8)
        self.set_text_color(150, 150, 150)
        self.set_draw_color(200, 200, 200)
        self.line(30, self.get_y(), 180, self.get_y())
        self.ln(2)
        self.cell(0, 4, "INGECTEC S.A.S: CALLE 2 N # 4-53 BELALCAZAR CELULAR: 317 504 64 04 - 3172736356", border=0, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.cell(0, 4, "comercial@ingectec.com - gerencia@ingectec.com", border=0, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.cell(0, 4, "WWW.INGECTEC.COM", border=0, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_y(-10)
        self.cell(0, 4, f'Página {self.page_no()}', border=0, align='R')

def conectar_db():
    try: return sqlite3.connect('ingectec.db', timeout=10)
    except: return None

def main(page: ft.Page):
    page.title = "INGECTEC V300 - PREMIUM"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#1e293b"
    page.padding = 15

    sesion = {"usuario": None, "rol": None}
    lista_items = []
    estado = {"nro_edicion": None}
    MI_WHATSAPP = "573175046404"

    def cerrar_dialogo(dlg):
        dlg.open = False; page.update()

    def mostrar_alerta(titulo, mensaje):
        dialogo = ft.AlertDialog(title=ft.Text(titulo, weight="bold", color="#fbbf24"), content=ft.Text(str(mensaje)), actions=[ft.TextButton("OK", on_click=lambda e: cerrar_dialogo(dialogo))])
        page.dialog = dialogo; dialogo.open = True; page.update()

    # --- PILOTO AUTOMÁTICO: BD Y TABLAS ---
    db_setup = conectar_db()
    if db_setup:
        db_setup.execute("CREATE TABLE IF NOT EXISTS usuarios (usuario TEXT PRIMARY KEY, password TEXT, rol TEXT)")
        
        try: db_setup.execute("ALTER TABLE usuarios ADD COLUMN intentos INTEGER DEFAULT 0")
        except: pass
        try: db_setup.execute("ALTER TABLE usuarios ADD COLUMN bloqueado INTEGER DEFAULT 0")
        except: pass

        db_setup.execute("INSERT OR IGNORE INTO usuarios (usuario, password, rol, intentos, bloqueado) VALUES ('OSCAR', '1234', 'ADMIN', 0, 0)")
        db_setup.execute("INSERT OR IGNORE INTO usuarios (usuario, password, rol, intentos, bloqueado) VALUES ('YEISON', '1234', 'ASESOR', 0, 0)")
        db_setup.execute("INSERT OR IGNORE INTO usuarios (usuario, password, rol, intentos, bloqueado) VALUES ('PAULO', '1234', 'ADMIN', 0, 0)")
        
        try:
            c_rol = db_setup.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='fix_rol_yeison'")
            if c_rol.fetchone()[0] == 0:
                db_setup.execute("UPDATE usuarios SET rol='ASESOR' WHERE usuario='YEISON'")
                db_setup.execute("CREATE TABLE fix_rol_yeison (id INTEGER PRIMARY KEY)")
        except: pass

        db_setup.execute("CREATE TABLE IF NOT EXISTS n_cot (id INTEGER PRIMARY KEY, num INTEGER)")
        db_setup.execute("INSERT OR IGNORE INTO n_cot (id, num) VALUES (1, 100)")
        
        try: db_setup.execute("ALTER TABLE historial ADD COLUMN creador TEXT DEFAULT 'SISTEMA'")
        except: pass
        try: db_setup.execute("ALTER TABLE historial ADD COLUMN origen TEXT DEFAULT 'WEB'")
        except: pass

        try: db_setup.execute("ALTER TABLE h_det ADD COLUMN tipo TEXT DEFAULT 'P'")
        except: pass

        db_setup.execute("CREATE TABLE IF NOT EXISTS cli (n TEXT PRIMARY KEY, i TEXT)")
        try: db_setup.execute("ALTER TABLE cli ADD COLUMN dir TEXT")
        except: pass
        try: db_setup.execute("ALTER TABLE cli ADD COLUMN email TEXT")
        except: pass
        try: db_setup.execute("ALTER TABLE cli ADD COLUMN ciu TEXT")
        except: pass
        try: db_setup.execute("ALTER TABLE cli ADD COLUMN tel TEXT")
        except: pass

        cursor_r = db_setup.cursor()
        items_perdidos = [("BREAKER 2X40", 101861), ("TUBO EMT DE 1\" (INCLUYE ASCESORIOS DE INSTALACION)", 35547)]Para lograr que la cotización en tu sistema se comporte como describes y refleje la jerarquía del archivo `Captura de pantalla 2026-09-22 173943.png`[cite: 1], debes estructurar la lógica interna y la interfaz de usuario con los siguientes parámetros:

**1. Lógica de Valores y Validación (Ítem vs. Sub-ítem)**
Debes configurar el sistema para que diferencie entre un "Ítem Principal" (Título) y un "Sub-ítem" (Característica). 
*   **Ítem Principal (Ej. 1. SUMINISTRO DE ANDAMIO CERTIFICADO[cite: 1]):** Es el único habilitado para recibir datos en las columnas `V. UNIT` y `VALOR`[cite: 1].
*   **Sub-ítem (Ej. 1.1, 1.2, 1.3[cite: 1]):** La validación interna debe forzar estos valores a nulo o bloquear la entrada de datos. En la vista del documento, las celdas de precio deben quedar completamente en blanco, funcionando únicamente como texto descriptivo de los materiales o partes del andamio.

**2. Retención de Foco en la Interfaz (Mantener Seleccionado)**
Para evitar que el sistema te deseleccione el ítem principal cada vez que agregas una característica (como el breaker o las tomas que muestras en la imagen[cite: 1]), debes ajustar el estado de la interfaz:
*   Al crear un ítem principal y hacer clic en "Añadir sub-ítem", el sistema debe guardar el ID de ese ítem en una variable de estado temporal (ej. `ÍtemActivo`).
*   Mientras ese estado esté activo, todos los sub-ítems que vayas guardando se asignarán automáticamente a ese título (generando la secuencia 1.1, 1.2, 1.3 de forma continua).
*   El foco de selección no debe limpiarse hasta que tú selecciones explícitamente una acción que diga "Finalizar características" o "Añadir nuevo Título Principal".

**3. Cálculos de Totales**
Al tener la validación configurada de esta manera, la sumatoria para el SUBTOTAL, el IVA y el TOTAL en la parte inferior[cite: 1] solo tomará en cuenta los valores ingresados frente a los títulos principales, evitando duplicidades o errores matemáticos generados por las características descriptivas.