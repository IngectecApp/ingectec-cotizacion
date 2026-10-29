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
    correcciones = {r"\bBALVULA\b": "VÁLVULA", r"\bBALVULAS\b": "VÁLVULAS", r"\bTAVLERO\b": "TABLERO", r"\bTAVLEROS\b": "TABLEROS", r"\bBOLTIOS\b": "VOLTIOS", r"\bBOLTAJE\b": "VOLTAJE", r"\bTUBERIA\b": "TUBERÍA", r"\bGAVINETE\b": "GABINETE", r"\bINTERUPTOR\b": "INTERRUPTOR", r"\bCONECCION\b": "CONEXIÓN", r"\bINSTALACION\b": "INSTALACIÓN", r"\bMANTENIMIENTO\b": "MANTENIMIENTO"}
    for mal, bien in correcciones.items(): s = re.sub(mal, bien, s, flags=re.IGNORECASE)
    return s.encode("latin-1", "replace").decode("latin-1")

class PDF(FPDF):
    def rounded_rect(self, x, y, w, h, r, style='F'):
        if style == 'F':
            self.rect(x + r, y, w - 2 * r, h, style='F'); self.rect(x, y + r, w, h - 2 * r, style='F')
            self.ellipse(x, y, 2 * r, 2 * r, style='F'); self.ellipse(x + w - 2 * r, y, 2 * r, 2 * r, style='F')
            self.ellipse(x, y + h - 2 * r, 2 * r, 2 * r, style='F'); self.ellipse(x + w - 2 * r, y + h - 2 * r, 2 * r, 2 * r, style='F')

    def header(self):
        try: base_dir = os.path.dirname(os.path.abspath(__file__))
        except: base_dir = os.getcwd()
        rutas_logos = [
            os.path.join(base_dir, "assets", "logopl.jpg"), os.path.join(base_dir, "logopl.jpg"),
            os.path.join(base_dir, "assets", "logopl.png"), os.path.join(base_dir, "logopl.png"),
            os.path.join(base_dir, "assets", "logo pl.png"), os.path.join(base_dir, "logo pl.png"),
            os.path.join(base_dir, "assets", "logo.png"), os.path.join(base_dir, "logo.png"),
            "assets/logo pl.png", "assets/logopl.png", "assets/logo.png", "assets/logo1.png",
            "/opt/render/project/src/logopl.png", "/opt/render/project/src/logopl.jpg",
            "/opt/render/project/src/assets/logopl.png", "/opt/render/project/src/assets/logopl.jpg"
        ]
        for ruta in rutas_logos:
            if os.path.exists(ruta):
                try: self.image(ruta, x=10, y=8, w=190); break 
                except: pass
        self.set_y(40) 
        
    def footer(self):
        self.set_y(-28)
        if hasattr(self, 'asesor_nombre') and self.asesor_nombre:
            self.set_font('helvetica', '', 7); self.set_text_color(210, 210, 210); self.set_x(30)
            self.cell(0, 3, f"Cod. Asesor: {self.asesor_nombre}", border=0, align='L')
        self.set_y(-25); self.set_font('helvetica', '', 8); self.set_text_color(150, 150, 150); self.set_draw_color(200, 200, 200)
        self.line(30, self.get_y(), 180, self.get_y()); self.ln(2)
        self.cell(0, 4, "INGECTEC S.A.S: CALLE 2 N # 4-53 BELALCAZAR CELULAR: 317 504 64 04 - 3172736356", border=0, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.cell(0, 4, "comercial@ingectec.com - gerencia@ingectec.com", border=0, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.cell(0, 4, "WWW.INGECTEC.COM", border=0, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_y(-10); self.cell(0, 4, f'Página {self.page_no()}', border=0, align='R')

def main(page: ft.Page):
    page.title = "⚡ INGECTEC L34L - PREMIUM"
    for ruta in ["assets/logo pl.png", "assets/logopl.png", "assets/logo.png", "assets/logo1.png", "logopl.png", "logo.png"]:
        if os.path.exists(ruta):
            try: page.window.icon = ruta; break 
            except: pass

    page.theme_mode = ft.ThemeMode.DARK; page.bgcolor = "#1e293b"; page.padding = 15
    sesion = {"usuario": None, "rol": None}; lista_items = []; estado = {"nro_edicion": None, "creador_edicion": None, "permitidos_edicion": []}

    def liberar_sesion_actual():
        if sesion.get("usuario"):
            try: db_x = conectar_db(); c_x = db_x.cursor(); c_x.execute("UPDATE usuarios SET sesion_activa=0 WHERE usuario=%s", (sesion["usuario"],)); db_x.commit(); db_x.close()
            except: pass

    page.window.prevent_close = True
    def on_window_event(e):
        if e.data == "close": liberar_sesion_actual(); page.window.destroy()
    page.window.on_event = on_window_event
    page.on_disconnect = lambda e: liberar_sesion_actual()

    def mostrar_alerta(titulo, mensaje):
        dlg = ft.AlertDialog(title=ft.Text(titulo, weight="bold", color="#fbbf24"), content=ft.Text(str(mensaje)), open=True)
        dlg.actions = [ft.TextButton("OK", on_click=lambda e: (setattr(dlg, 'open', False), page.update()))]
        page.overlay.append(dlg); page.update()

    def mostrar_snack(mensaje, color_fondo="#10b981", color_texto="white"):
        page.overlay.append(ft.SnackBar(content=ft.Text(mensaje, color=color_texto), bgcolor=color_fondo, open=True)); page.update()

    def cerrar_dialogo(dlg): dlg.open = False; page.update()

    input_usr = ft.TextField(label="Usuario (Ej. OMERA, YRESTREPO)", width=300)
    input_pwd = ft.TextField(label="Contraseña", password=True, can_reveal_password=True, width=300)

    def procesar_login(e):
        u = input_usr.value.upper().strip(); p = input_pwd.value.strip()
        db = conectar_db()
        if db:
            c = db.cursor(); c.execute("SELECT password, rol, bloqueado, intentos, sesion_activa FROM usuarios WHERE usuario=%s", (u,))
            user_row = c.fetchone()
            if user_row:
                db_pwd, rol, bloqueado, intentos, sesion_activa = user_row
                if bloqueado == 1: mostrar_alerta("Bloqueado 🔒", "Usuario bloqueado."); db.close(); return
                if sesion_activa == 1: mostrar_alerta("Sesión en Uso 🚫", f"El usuario {u} ya tiene una sesión abierta."); db.close(); return
                if db_pwd == p:
                    c.execute("UPDATE usuarios SET intentos=0, bloqueado=0, sesion_activa=1 WHERE usuario=%s", (u,))
                    db.close(); sesion["usuario"] = u; sesion["rol"] = rol; iniciar_app_principal()
                else:
                    intentos += 1
                    if intentos >= 3: c.execute("UPDATE usuarios SET intentos=%s, bloqueado=1 WHERE usuario=%s", (intentos, u)); mostrar_alerta("Bloqueado 🚫", "Excedió intentos.")
                    else: c.execute("UPDATE usuarios SET intentos=%s WHERE usuario=%s", (intentos, u)); mostrar_snack("❌ Clave incorrecta", "#ef4444")
                    db.close(); page.update()
            else: db.close(); mostrar_snack("❌ Usuario no existe", "#ef4444"); page.update()

    pantalla_login = ft.Container(content=ft.Column([ft.Icon("bolt", size=70, color="#f59e0b"), ft.Text("INGECTEC - Acceso Seguro", size=20, weight="bold", color="white"), input_usr, input_pwd, ft.ElevatedButton("INICIAR SESIÓN", bgcolor="#f59e0b", color="black", width=300, height=45, on_click=procesar_login)], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15), alignment=ft.alignment.center, expand=True)

    def mostrar_login():
        liberar_sesion_actual(); sesion["usuario"] = None; sesion["rol"] = None; lista_items.clear(); estado["nro_edicion"] = None; estado["creador_edicion"] = None; estado["permitidos_edicion"] = []
        input_usr.value = ""; input_pwd.value = ""; page.scroll = None; page.controls.clear(); page.add(pantalla_login); page.update()

    def iniciar_app_principal():
        page.scroll = ft.ScrollMode.AUTO; page.controls.clear()
        
        input_cliente = ft.TextField(label="Buscar nombre de cliente...")
        input_nit = ft.TextField(label="NIT / C.C.")
        input_ciudad = ft.TextField(label="Ciudad (Origen Cotización)", value="Yumbo")
        input_atencion = ft.TextField(label="Atención a: (Ej. ING. MICHAEL MESIAS)")
        input_ref = ft.TextField(label="REFERENCIA")
        input_tiempo_entrega = ft.TextField(label="Tiempo de entrega", value="4 Días hábiles")
        input_validez = ft.TextField(label="Validez cotización", value="20 Días")
        input_pago = ft.TextField(label="Forma de pago", value="30 Días")
        input_garantia = ft.TextField(label="Garantía", value="6 meses en mano de obra")
        input_notas = ft.TextField(label="Notas adicionales", value="Toda la actividad será coordinada por el ingeniero Edward Álvarez y/o John Paniagua", multiline=True)
        input_pct_a = ft.TextField(label="Admin %", value="10"); input_pct_i = ft.TextField(label="Imprev %", value="2")
        input_pct_u = ft.TextField(label="Util %", value="8"); input_pct_iva_u = ft.TextField(label="IVA s/U %", value="19")
        
        lista_busqueda_cli = ft.ListView(height=150, visible=False, spacing=2)
        dropdown_modo_cot = ft.Dropdown(label="Tipo Cotización", options=[ft.dropdown.Option("AIU"), ft.dropdown.Option("IVA")], value="AIU")
        container_texto_aiu = ft.Container(content=ft.Text("⚙ Config. AIU:", weight="bold", color="#fbbf24"), col={"sm": 12, "md": 2, "lg": 2}, alignment=ft.alignment.center_left)
        cont_a = ft.Container(content=input_pct_a, col={"sm": 3, "md": 2, "lg": 2}); cont_i = ft.Container(content=input_pct_i, col={"sm": 3, "md": 2, "lg": 2})
        cont_u = ft.Container(content=input_pct_u, col={"sm": 3, "md": 2, "lg": 2}); cont_iva_u = ft.Container(content=input_pct_iva_u, col={"sm": 3, "md": 2, "lg": 2})

        def guardar_borrador(e=None):
            try:
                borrador = {"lista_items": lista_items, "estado": estado, "cabecera": {"cliente": input_cliente.value, "nit": input_nit.value, "ciudad": input_ciudad.value, "atencion": input_atencion.value, "ref": input_ref.value, "tiempo_entrega": input_tiempo_entrega.value, "validez": input_validez.value, "pago": input_pago.value, "garantia": input_garantia.value, "notas": input_notas.value, "modo": dropdown_modo_cot.value, "pct_a": input_pct_a.value, "pct_i": input_pct_i.value, "pct_u": input_pct_u.value, "pct_iva_u": input_pct_iva_u.value}}
                if sesion["usuario"]: page.client_storage.set(f"draft_{sesion['usuario']}", json.dumps(borrador))
            except: pass

        for i in [input_nit, input_ciudad, input_atencion, input_ref, input_tiempo_entrega, input_validez, input_pago, input_garantia, input_notas, input_pct_a, input_pct_i, input_pct_u, input_pct_iva_u]: i.on_change = guardar_borrador

        def verificar_permiso_edicion(mostrar_aviso=True):
            if estado.get("nro_edicion") and estado.get("creador_edicion"):
                if estado["creador_edicion"] not in ["SISTEMA", sesion["usuario"]]:
                    permitidos = estado.get("permitidos_edicion", [])
                    if sesion["usuario"] not in permitidos:
                        if mostrar_aviso: mostrar_alerta("Protegido 🛡️", f"Cotización exclusiva de {estado['creador_edicion']}.")
                        return False
            return True

        def cambiar_modo_cot(e):
            es_aiu = dropdown_modo_cot.value == "AIU"
            container_texto_aiu.visible = es_aiu; cont_a.visible = es_aiu; cont_i.visible = es_aiu; cont_u.visible = es_aiu; cont_iva_u.visible = es_aiu
            page.update(); guardar_borrador()
            
        dropdown_modo_cot.on_change = cambiar_modo_cot

        def buscar_cliente_realtime(e):
            txt = (input_cliente.value or "").upper().strip(); lista_busqueda_cli.controls.clear()
            if len(txt) > 0:
                db = conectar_db()
                if db:
                    c = db.cursor(); c.execute("SELECT n, i FROM cli WHERE UPPER(n) LIKE %s LIMIT 10", ('%'+txt+'%',))
                    for r in c.fetchall():
                        def sel(evt, nom=r[0], nit=r[1]): input_cliente.value = nom; input_nit.value = nit or ""; lista_busqueda_cli.visible = False; page.update(); guardar_borrador()
                        lista_busqueda_cli.controls.append(ft.ListTile(title=ft.Text(r[0], color="#fbbf24", size=13), on_click=sel))
                    db.close(); lista_busqueda_cli.visible = len(lista_busqueda_cli.controls) > 0
            else: lista_busqueda_cli.visible = False
            page.update(); guardar_borrador()
            
        input_cliente.on_change = buscar_cliente_realtime

        db_num = conectar_db(); nro_actual = "100"
        if db_num:
            c = db_num.cursor(); c.execute("SELECT num FROM n_cot WHERE id=1"); res = c.fetchone()
            if res: nro_actual = f"{datetime.now().strftime('%m')}-{res[0]:03d}"
            db_num.close()

        def obtener_items_procesados(lista):
            disp = []; curr_p = -1; np, ns = 0, 0
            for i, it in enumerate(lista):
                precio_final = float(it['precio'])
                if it.get('tipo', 'P') == 'P':
                    np += 1; ns = 0; curr_p = len(disp)
                    disp.append({"raw_idx": i, "desc": it['desc'], "cant": float(it['cant']), "und": it.get('und', ''), "precio": precio_final, "total": precio_final * float(it['cant']), "impuesto": it.get('impuesto', ''), "tipo": 'P', "num": str(np), "has_subs": False})
                else:
                    ns += 1; total_sub = precio_final * float(it['cant'])
                    disp.append({"raw_idx": i, "desc": it['desc'], "cant": float(it['cant']), "und": it.get('und', ''), "precio": precio_final, "total": total_sub, "impuesto": it.get('impuesto', ''), "tipo": 'S', "num": f"{np}.{ns}"})
                    if curr_p != -1:
                        disp[curr_p]['has_subs'] = True; disp[curr_p]['total'] += total_sub
                        if disp[curr_p]['cant'] == 0: disp[curr_p]['cant'] = 1 
                        disp[curr_p]['precio'] = disp[curr_p]['total'] / disp[curr_p]['cant']
            return disp

        columna_tabla_items = ft.Column()
        def actualizar_tabla_visual():
            columna_tabla_items.controls.clear()
            for item in obtener_items_procesados(lista_items):
                is_p = item['tipo'] == 'P'; has_s = item.get('has_subs', False); is_title = is_p and has_s
                
                if is_title:
                    tot_s = f"${item['total']:,.2f}" if item['total'] > 0 else ""; c_s = ""; imp_l = ""; txt_col = "#fbbf24"; txt_wgt = "bold"
                elif is_p:
                    tot_s = f"${item['total']:,.2f}" if item['total'] > 0 else ""; c_s = "" if item['cant'] == 0 else f"{item['cant']:g} {item['und']}"; imp_l = f" ({item['impuesto']})" if item['total'] > 0 else ""; txt_col = "white"; txt_wgt = "normal"
                else:
                    tot_s = f"${item['total']:,.2f}" if item['total'] > 0 else ""; c_s = f"{item['cant']:g} {item['und']}" if item['cant'] > 0 else ""; imp_l = ""; txt_col = "white"; txt_wgt = "normal"
                
                if is_p: txt_col = "#fbbf24"; txt_wgt = "bold"
                
                def evt_edit(idx_r):
                    def on_c(e):
                        if not verificar_permiso_edicion(): return
                        estado_modal = {"idx": idx_r}
                        ec = ft.TextField(label="Cant", value=str(lista_items[idx_r]['cant'])); ep = ft.TextField(label="Costo Base", value=f"{lista_items[idx_r].get('precio_base', lista_items[idx_r]['precio']):.2f}"); eu = ft.TextField(label="Utilidad %", value=str(lista_items[idx_r].get('utilidad', 0)))
                        
                        def move_up(ev):
                            curr = estado_modal["idx"]
                            if curr > 0: lista_items[curr], lista_items[curr-1] = lista_items[curr-1], lista_items[curr]; estado_modal["idx"] = curr - 1; actualizar_tabla_visual()
                        
                        def move_down(ev):
                            curr = estado_modal["idx"]
                            if curr < len(lista_items) - 1: lista_items[curr], lista_items[curr+1] = lista_items[curr+1], lista_items[curr]; estado_modal["idx"] = curr + 1; actualizar_tabla_visual()
                        
                        btn_up = ft.IconButton("arrow_upward", on_click=move_up, tooltip="Subir posición", icon_color="#3b82f6"); btn_down = ft.IconButton("arrow_downward", on_click=move_down, tooltip="Bajar posición", icon_color="#3b82f6")
                        row_arrows = ft.Row([ft.Text("Mover de posición:", size=12, color="#94a3b8"), btn_up, btn_down], alignment=ft.MainAxisAlignment.CENTER)

                        dlg_e = ft.AlertDialog(title=ft.Text(f"Editar: {lista_items[idx_r]['desc']}"), content=ft.Column([ec, ep, eu, row_arrows], tight=True), open=True)
                        
                        def s(ev):
                            try: 
                                curr = estado_modal["idx"]
                                lista_items[curr]['cant'] = float(ec.value or 0); p_base = float(ep.value or 0); u_pct = float(eu.value or 0); lista_items[curr]['precio_base'] = p_base; lista_items[curr]['utilidad'] = u_pct; p_final = p_base * (1 + u_pct / 100.0); lista_items[curr]['precio'] = p_final; lista_items[curr]['total'] = lista_items[curr]['cant'] * p_final
                                actualizar_tabla_visual(); cerrar_dialogo(dlg_e)
                            except: pass
                        def rm(ev): curr = estado_modal["idx"]; lista_items.pop(curr); actualizar_tabla_visual(); cerrar_dialogo(dlg_e)
                            
                        dlg_e.actions = [ft.ElevatedButton("Guardar", bgcolor="#10b981", on_click=s), ft.ElevatedButton("Eliminar", bgcolor="#ef4444", on_click=rm), ft.TextButton("Cancelar", on_click=lambda ev: cerrar_dialogo(dlg_e))]
                        page.overlay.append(dlg_e); page.update()
                    return on_c

                columna_tabla_items.controls.append(ft.Container(content=ft.ResponsiveRow([ft.Text(f"{item['num']}. {item['desc']}{imp_l}", col={"sm": 6}, color=txt_col, weight=txt_wgt, size=12), ft.Text(c_s, col={"sm": 3}, text_align="center", color=txt_col, weight=txt_wgt), ft.Text(tot_s, col={"sm": 3}, text_align="right", color=txt_col, weight=txt_wgt)]), on_click=evt_edit(item['raw_idx']), padding=5, border_radius=5, ink=True))
            page.update(); guardar_borrador()

        def abrir_modal_item(e):
            if not verificar_permiso_edicion(): return
            res_inv = ft.ListView(expand=True, spacing=10, height=150)
            tipo_it = ft.RadioGroup(content=ft.Row([ft.Radio(value="P", label="Ítem Principal (Título)"), ft.Radio(value="S", label="Sub-ítem (Hijo)")]), value="P")
            m_cot = dropdown_modo_cot.value; pct_def = "19" if m_cot=="IVA" else "10"

            i_desc = ft.TextField(label="Descripción"); i_cant = ft.TextField(label="Cantidad", value="1", col={"sm": 3}); i_und_c = ft.TextField(label="Iniciales", visible=False, col={"sm": 2}); i_pre = ft.TextField(label="Costo Base", value="0.00", col={"sm": 3}); i_utilidad = ft.TextField(label="Utilidad %", value="0", col={"sm": 3})
            
            def cb_und(evt):
                if i_und.value == "✍️ ESCRIBIR...": i_cant.col={"sm": 2}; i_und.col={"sm": 3}; i_und_c.visible=True; i_pre.col={"sm": 2}; i_utilidad.col={"sm": 2}; i_und_c.focus()
                else: i_cant.col={"sm": 3}; i_und.col={"sm": 3}; i_und_c.visible=False; i_pre.col={"sm": 3}; i_utilidad.col={"sm": 3}
                page.update()
                
            def cb_imp(evt):
                if i_imp_t.value == "IVA": i_imp_p.value = "19"
                elif i_imp_t.value == "AIU": i_imp_p.value = "10"
                else: i_imp_p.value = "0"
                page.update()

            i_und = ft.Dropdown(label="Und", options=[ft.dropdown.Option(u) for u in ["ML", "UNID", "MTS", "GLB", "ROLLO", "DIA", "PAQ", "✍️ ESCRIBIR..."]], value="UNID", col={"sm": 3}, on_change=cb_und)
            i_imp_t = ft.Dropdown(label="Impuesto", options=[ft.dropdown.Option(m_cot), ft.dropdown.Option("EXENTO")], value=m_cot, col={"sm": 6}, on_change=cb_imp)
            i_imp_p = ft.TextField(label="% Imp", value=pct_def, col={"sm": 6})

            def b_inv(evt):
                res_inv.controls.clear(); db = conectar_db()
                if db:
                    c=db.cursor(); txt=(b_busq.value or "").upper()
                    try: c.execute("SELECT d, p, proveedor FROM inv WHERE UPPER(d) LIKE %s LIMIT 30", ('%'+txt+'%',))
                    except: c.execute("SELECT d, p, '' FROM inv WHERE UPPER(d) LIKE %s LIMIT 30", ('%'+txt+'%',))
                    for r in c.fetchall():
                        d=r[0]; p=r[1] or 0; prov=r[2] if len(r)>2 and r[2] else ""
                        def sel(ev, desc=d, prec=p): 
                            i_desc.value=desc; i_pre.value=f"{float(prec):.2f}"; i_und.value = "ML" if ("TUBO" in desc.upper() or "CABLE" in desc.upper()) else ("GLB" if "INSTALACION" in desc.upper() else "UNID"); i_und_c.visible=False; i_cant.col={"sm":3}; i_und.col={"sm":3}; i_pre.col={"sm":3}; i_utilidad.col={"sm":3}; i_utilidad.value="0"
                            if float(prec) == 0: tipo_it.value = "P"; i_cant.value = "0"
                            else: tipo_it.value = "S"; i_cant.value = "1"
                            page.update()
                            
                        subt = f"${float(p):,.2f}" + (f" ({prov})" if prov else "")
                        res_inv.controls.append(ft.ListTile(title=ft.Text(d, color="#fbbf24", size=14), subtitle=ft.Text(subt, color="#94a3b8"), on_click=sel))
                    db.close()
                page.update()

            def g_item(evt):
                if not i_desc.value: return
                try:
                    c = float(i_cant.value or 0); p_base = float(i_pre.value or 0)
                    try: u_pct = float(i_utilidad.value or 0)
                    except: u_pct = 0.0
                    
                    if tipo_it.value == "P": c = 0
                    p_final = p_base * (1 + u_pct / 100.0); imp = "EXENTO" if i_imp_t.value=="EXENTO" else f"{i_imp_t.value} {i_imp_p.value}%"; uf = str(i_und_c.value).upper().strip() if i_und.value=="✍️ ESCRIBIR..." else i_und.value; uf = uf or "UNID"
                    
                    lista_items.append({"desc": sanitizar_texto(i_desc.value), "cant": c, "precio_base": p_base, "utilidad": u_pct, "precio": p_final, "total": c*p_final, "impuesto": imp, "und": uf, "tipo": tipo_it.value})
                    actualizar_tabla_visual()
                    
                    i_desc.value=""; i_cant.value="1"; i_pre.value="0.00"; i_utilidad.value="0"; i_und.value="UNID"; i_und_c.value=""; i_und_c.visible=False; i_imp_t.value=m_cot; i_imp_p.value=pct_def; b_busq.value=""; b_inv(None)
                    mostrar_snack("✅ Agregado")
                except: pass

            b_busq = ft.TextField(label="Buscar en bodega...", on_change=b_inv)
            dlg_i = ft.AlertDialog(title=ft.Text("➕ Añadir"), content=ft.Container(width=750, content=ft.Column([tipo_it, b_busq, res_inv, i_desc, ft.ResponsiveRow([i_cant, i_und, i_und_c, i_pre, i_utilidad]), ft.ResponsiveRow([i_imp_t, i_imp_p])], tight=True)), open=True)
            dlg_i.actions = [ft.ElevatedButton("Guardar", bgcolor="#10b981", on_click=g_item), ft.TextButton("Cerrar", on_click=lambda e: cerrar_dialogo(dlg_i))]
            page.overlay.append(dlg_i); page.update(); b_inv(None)

        def abrir_modal_bodega(e):
            # (Código omitido para brevedad visual, aquí iría el modal de bodega completo)
            pass

        def abrir_modal_clientes(e):
            # (Código omitido para brevedad visual)
            pass

        def abrir_modal_usuarios(e):
            # (Código omitido para brevedad visual)
            pass

        def abrir_modal_historial(e):
            # (Código omitido para brevedad visual)
            pass

        def abrir_modal_sistema(e):
            # (Código omitido para brevedad visual)
            pass

        def limpiar_todo(e):
            lista_items.clear(); estado["nro_edicion"] = None; estado["creador_edicion"] = None; estado["permitidos_edicion"] = []
            input_cliente.value = ""; input_nit.value = ""; input_atencion.value = ""; input_ref.value = ""; input_ciudad.value = "Yumbo"; input_tiempo_entrega.value = "4 Días hábiles"; input_validez.value = "20 Días"; input_pago.value = "30 Días"; input_garantia.value = "6 meses en mano de obra"; input_notas.value = "Toda la actividad será coordinada por el ingeniero Edward Álvarez y/o John Paniagua"; dropdown_modo_cot.value = "AIU"; input_pct_a.value = "10"; input_pct_i.value = "2"; input_pct_u.value = "8"; input_pct_iva_u.value = "19"
            lista_busqueda_cli.visible = False
            cambiar_modo_cot(None)
            try: page.client_storage.remove(f"draft_{sesion['usuario']}")
            except: pass

        def generar_pdf_web(e):
            try:
                if not lista_items or not input_cliente.value: return mostrar_alerta("Aviso", "Faltan datos.")
                puede_guardar = verificar_permiso_edicion(mostrar_aviso=False)

                c_nom = sanitizar_texto(input_cliente.value or "").upper().strip(); c_nit = sanitizar_texto(input_nit.value or "").strip(); c_ciu_origen = sanitizar_texto(input_ciudad.value or "Yumbo").strip(); c_atn = sanitizar_texto(input_atencion.value or "").strip(); c_ref = sanitizar_texto(input_ref.value or "").strip(); c_t_entrega = sanitizar_texto(input_tiempo_entrega.value or "").strip(); c_validez = sanitizar_texto(input_validez.value or "").strip(); c_pago = sanitizar_texto(input_pago.value or "").strip(); c_garantia = sanitizar_texto(input_garantia.value or "").strip(); c_notas = sanitizar_texto(input_notas.value or "").strip(); c_modo = dropdown_modo_cot.value or "AIU"
                # (Recolección de datos y cálculos AIU/IVA)
                
                # (Generación del PDF con fpdf2 - Secciones header, cuerpo y footer)
                
                # ...
                p.output(f"assets/{nom_arc}")
                try: os.remove("assets/qr_temp.png")
                except: pass
                
                if not puede_guardar:
                    mostrar_snack("⚠ Modo Lectura: PDF de consulta generado. Original sin alterar.", "#f59e0b", "black")
                
                def descargar_pdf_abrir(ev):
                    if page.web:
                        page.launch_url(f"/{nom_arc}")
                    else:
                        ruta_abs = os.path.abspath(f"assets/{nom_arc}")
                        try:
                            if platform.system() == "Windows":
                                os.startfile(ruta_abs)
                            elif platform.system() == "Darwin":
                                subprocess.call(["open", ruta_abs])
                            else:
                                subprocess.call(["xdg-open", ruta_abs])
                        except Exception as ex:
                            mostrar_alerta("Error", f"No se pudo abrir el archivo localmente: {ex}")

                dlg_d = ft.AlertDialog(title=ft.Text("✅ Generado", color="#10b981"), content=ft.Text(f"Archivo: {nom_arc}"), open=True)
                dlg_d.actions = [ft.ElevatedButton("📥 ABRIR PDF", bgcolor="#2563eb", color="white", on_click=descargar_pdf_abrir), ft.TextButton("Cerrar", on_click=lambda ev: cerrar_dialogo(dlg_d))]
                page.overlay.append(dlg_d); page.update()
            except Exception as eFallo: mostrar_alerta("Error al generar PDF", f"Hubo un fallo: {str(eFallo)}")

        # (Código del UI omitido)
        # ...

    mostrar_login()

if hasattr(ft, 'app'):
    ft.app(target=main, host="0.0.0.0", port=PORT, view=ft.AppView.WEB_BROWSER, assets_dir="assets")
else:
    ft.app(target=main, host="0.0.0.0", port=PORT, view=ft.AppView.WEB_BROWSER, assets_dir="assets")