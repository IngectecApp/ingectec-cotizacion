import flet as ft
import psycopg2
import os
import shutil
import re
import json
import qrcode
import textwrap
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from datetime import datetime

PORT = int(os.environ.get("PORT", 8080))
if not os.path.exists("assets"): os.makedirs("assets")

# --- CONEXIÓN SEGURA A POSTGRESQL CON AUTOCOMMIT ---
DB_URL = os.environ.get("DATABASE_URL", "postgresql://ingectec_bd_user:HY7iwKhvaILCeuUKd7Pgknsh6Nsv4aUE@dpg-dapicrvf3r2c73ep15ag-a.oregon-postgres.render.com/ingectec_bd")

def conectar_db():
    try:
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True 
        return conn
    except: return None

# --- INICIALIZADOR AUTOMÁTICO DE TABLAS ---
def init_db():
    conn = conectar_db()
    if conn:
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS usuarios (usuario TEXT PRIMARY KEY, password TEXT, rol TEXT, intentos INTEGER DEFAULT 0, bloqueado INTEGER DEFAULT 0)")
        
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

        c.execute("""CREATE TABLE IF NOT EXISTS h_cab (
            nro TEXT PRIMARY KEY, cli TEXT, nit TEXT, atn TEXT, ref TEXT, ciu_origen TEXT, t_entrega TEXT, validez TEXT, pago TEXT, garantia TEXT, notas TEXT, modo TEXT, pct_a NUMERIC, pct_i NUMERIC, pct_u NUMERIC, pct_iva_u NUMERIC
        )""")
        
        for col, tipo in [("atn", "TEXT"), ("ref", "TEXT"), ("ciu_origen", "TEXT"), ("t_entrega", "TEXT"), ("validez", "TEXT"), ("pago", "TEXT"), ("garantia", "TEXT"), ("notas", "TEXT"), ("modo", "TEXT"), ("pct_a", "NUMERIC"), ("pct_i", "NUMERIC"), ("pct_u", "NUMERIC"), ("pct_iva_u", "NUMERIC")]:
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
    return s.encode("latin-1", "replace").decode("latin-1")

class PDF(FPDF):
    def rounded_rect(self, x, y, w, h, r, style='F'):
        if style == 'F':
            self.rect(x + r, y, w - 2 * r, h, style='F'); self.rect(x, y + r, w, h - 2 * r, style='F')
            self.ellipse(x, y, 2 * r, 2 * r, style='F'); self.ellipse(x + w - 2 * r, y, 2 * r, 2 * r, style='F')
            self.ellipse(x, y + h - 2 * r, 2 * r, 2 * r, style='F'); self.ellipse(x + w - 2 * r, y + h - 2 * r, 2 * r, 2 * r, style='F')

    def header(self):
        for ruta in ["logo pl.png", "logopl.png", "logo.png", "logo1.png"]:
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
    page.title = "INGECTEC V300 - PREMIUM"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#1e293b"
    page.padding = 15

    sesion = {"usuario": None, "rol": None}
    lista_items = []
    estado = {"nro_edicion": None, "creador_edicion": None, "permitidos_edicion": []}

    def cerrar_dialogo(dlg): dlg.open = False; page.update()
    def mostrar_alerta(titulo, mensaje):
        dlg = ft.AlertDialog(title=ft.Text(titulo, weight="bold", color="#fbbf24"), content=ft.Text(str(mensaje)), actions=[ft.TextButton("OK", on_click=lambda e: cerrar_dialogo(dlg))])
        page.dialog = dlg; dlg.open = True; page.update()

    input_usr = ft.TextField(label="Usuario (Ej. OMERA, YRESTREPO)", width=300)
    input_pwd = ft.TextField(label="Contraseña", password=True, can_reveal_password=True, width=300)

    def procesar_login(e):
        u = input_usr.value.upper().strip(); p = input_pwd.value.strip()
        db = conectar_db()
        if db:
            c = db.cursor(); c.execute("SELECT password, rol, bloqueado, intentos FROM usuarios WHERE usuario=%s", (u,))
            user_row = c.fetchone()
            if user_row:
                db_pwd, rol, bloqueado, intentos = user_row
                if bloqueado == 1: mostrar_alerta("Bloqueado 🔒", "Usuario bloqueado. Contacta a un Super Administrador (OMERA o PLEAL)."); db.close(); return
                if db_pwd == p:
                    c.execute("UPDATE usuarios SET intentos=0, bloqueado=0 WHERE usuario=%s", (u,))
                    db.close(); sesion["usuario"] = u; sesion["rol"] = rol; iniciar_app_principal()
                else:
                    intentos += 1
                    if intentos >= 3: c.execute("UPDATE usuarios SET intentos=%s, bloqueado=1 WHERE usuario=%s", (intentos, u)); mostrar_alerta("Bloqueado 🚫", "Excedió intentos. Tu usuario ha sido bloqueado por seguridad.")
                    else: c.execute("UPDATE usuarios SET intentos=%s WHERE usuario=%s", (intentos, u)); page.snack_bar = ft.SnackBar(ft.Text("❌ Clave incorrecta"), bgcolor="#ef4444"); page.snack_bar.open = True
                    db.close(); page.update()
            else: db.close(); page.snack_bar = ft.SnackBar(ft.Text("❌ Usuario no existe"), bgcolor="#ef4444"); page.snack_bar.open = True; page.update()

    pantalla_login = ft.Container(content=ft.Column([
        ft.Icon(ft.icons.BOLT, size=70, color="#f59e0b"), 
        ft.Text("INGECTEC - Acceso Seguro", size=20, weight="bold", color="white"), 
        input_usr, input_pwd, 
        ft.ElevatedButton("INICIAR SESIÓN", bgcolor="#f59e0b", color="black", width=300, height=45, on_click=procesar_login)
    ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15), alignment=ft.alignment.center, expand=True)

    def mostrar_login():
        sesion["usuario"] = None; sesion["rol"] = None; lista_items.clear()
        estado["nro_edicion"] = None; estado["creador_edicion"] = None; estado["permitidos_edicion"] = []
        input_usr.value = ""; input_pwd.value = ""
        page.scroll = None; page.controls.clear(); page.add(pantalla_login); page.update()

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
        container_texto_aiu = ft.Container(content=ft.Text("⚙️ Config. AIU:", weight="bold", color="#fbbf24"), col={"sm": 12, "md": 2, "lg": 2}, alignment=ft.alignment.center_left)
        cont_a = ft.Container(content=input_pct_a, col={"sm": 3, "md": 2, "lg": 2}); cont_i = ft.Container(content=input_pct_i, col={"sm": 3, "md": 2, "lg": 2})
        cont_u = ft.Container(content=input_pct_u, col={"sm": 3, "md": 2, "lg": 2}); cont_iva_u = ft.Container(content=input_pct_iva_u, col={"sm": 3, "md": 2, "lg": 2})

        def verificar_permiso_edicion(mostrar_aviso=True):
            if estado.get("nro_edicion") and estado.get("creador_edicion"):
                if estado["creador_edicion"] not in ["SISTEMA", sesion["usuario"]]:
                    permitidos = estado.get("permitidos_edicion", [])
                    if sesion["usuario"] not in permitidos:
                        if mostrar_aviso:
                            mostrar_alerta("Protegido 🛡️", f"Cotización exclusiva de {estado['creador_edicion']}. No tienes permiso de edición para este documento.")
                        return False
            return True

        def cambiar_modo_cot(e):
            v = dropdown_modo_cot.value == "AIU"
            container_texto_aiu.visible = v; cont_a.visible = v; cont_i.visible = v; cont_u.visible = v; cont_iva_u.visible = v; page.update()
        dropdown_modo_cot.on_change = cambiar_modo_cot

        def buscar_cliente_realtime(e):
            txt = (input_cliente.value or "").upper().strip(); lista_busqueda_cli.controls.clear()
            if len(txt) > 0:
                db = conectar_db()
                if db:
                    c = db.cursor(); c.execute("SELECT n, i FROM cli WHERE UPPER(n) LIKE %s LIMIT 10", ('%'+txt+'%',))
                    for r in c.fetchall():
                        def sel(evt, nom=r[0], nit=r[1]): input_cliente.value = nom; input_nit.value = nit or ""; lista_busqueda_cli.visible = False; page.update()
                        lista_busqueda_cli.controls.append(ft.ListTile(title=ft.Text(r[0], color="#fbbf24", size=13), on_click=sel))
                    db.close(); lista_busqueda_cli.visible = len(lista_busqueda_cli.controls) > 0
            else: lista_busqueda_cli.visible = False
            page.update()
        input_cliente.on_change = buscar_cliente_realtime

        db_num = conectar_db(); nro_actual = "100"
        if db_num:
            c = db_num.cursor(); c.execute("SELECT num FROM n_cot WHERE id=1"); res = c.fetchone()
            if res: nro_actual = f"{datetime.now().strftime('%m')}-{res[0]:03d}"
            db_num.close()

        def obtener_items_procesados(lista):
            disp = []; curr_p = -1; np, ns = 0, 0
            for i, it in enumerate(lista):
                if it.get('tipo', 'P') == 'P':
                    np += 1; ns = 0; curr_p = len(disp)
                    disp.append({
                        "raw_idx": i, "desc": it['desc'], "cant": float(it['cant']), "und": it.get('und', ''),
                        "precio": float(it['precio']), "total": float(it['total']), 
                        "impuesto": it.get('impuesto', ''), "tipo": 'P', "num": str(np), "has_subs": False
                    })
                else:
                    ns += 1
                    disp.append({
                        "raw_idx": i, "desc": it['desc'], "cant": float(it['cant']), "und": it.get('und', ''),
                        "precio": float(it['precio']), "total": float(it['total']), 
                        "impuesto": it.get('impuesto', ''), "tipo": 'S', "num": f"{np}.{ns}"
                    })
                    if curr_p != -1:
                        disp[curr_p]['has_subs'] = True
                        disp[curr_p]['total'] += float(it['total'])
                        if disp[curr_p]['cant'] == 0: disp[curr_p]['cant'] = 1
                        disp[curr_p]['precio'] = disp[curr_p]['total'] / disp[curr_p]['cant']
            return disp

        columna_tabla_items = ft.Column()
        def actualizar_tabla_visual():
            columna_tabla_items.controls.clear()
            
            for item in obtener_items_procesados(lista_items):
                is_p = item['tipo'] == 'P'
                has_s = item.get('has_subs', False)
                is_title = is_p and has_s
                
                if is_title:
                    tot_s = f"${int(item['total']):,}" if item['total'] > 0 else ""
                    c_s = ""
                    imp_l = ""
                    txt_col = "#fbbf24"
                    txt_wgt = "bold"
                elif is_p:
                    tot_s = f"${int(item['total']):,}" if item['total'] > 0 else ""
                    c_s = f"{item['cant']:g} {item['und']}" if item['cant'] > 0 else ""
                    imp_l = f" ({item['impuesto']})" if item['total'] > 0 else ""
                    txt_col = "white"
                    txt_wgt = "normal"
                else:
                    tot_s = ""
                    c_s = f"{item['cant']:g} {item['und']}" if item['cant'] > 0 else ""
                    imp_l = ""
                    txt_col = "white"
                    txt_wgt = "normal"
                
                def evt_edit(idx_r):
                    def on_c(e):
                        if not verificar_permiso_edicion(): return
                        ec = ft.TextField(label="Cant", value=str(lista_items[idx_r]['cant']))
                        ep = ft.TextField(label="Precio (Uso Interno)", value=str(int(lista_items[idx_r]['precio'])))
                        def s(ev):
                            try: lista_items[idx_r]['cant']=float(ec.value or 0); lista_items[idx_r]['precio']=float(ep.value or 0); lista_items[idx_r]['total']=lista_items[idx_r]['cant']*lista_items[idx_r]['precio']; actualizar_tabla_visual(); cerrar_dialogo(dlg)
                            except: pass
                        def rm(ev): lista_items.pop(idx_r); actualizar_tabla_visual(); cerrar_dialogo(dlg)
                        dlg = ft.AlertDialog(title=ft.Text(f"Editar: {lista_items[idx_r]['desc']}"), content=ft.Column([ec, ep], tight=True), actions=[ft.ElevatedButton("Guardar", bgcolor="#10b981", on_click=s), ft.ElevatedButton("Eliminar", bgcolor="#ef4444", on_click=rm), ft.TextButton("Cancelar", on_click=lambda ev: cerrar_dialogo(dlg))])
                        page.dialog = dlg; dlg.open=True; page.update()
                    return on_c

                columna_tabla_items.controls.append(
                    ft.Container(
                        content=ft.ResponsiveRow([
                            ft.Text(f"{item['num']}. {item['desc']}{imp_l}", col={"sm": 6}, color=txt_col, weight=txt_wgt, size=12), 
                            ft.Text(c_s, col={"sm": 3}, text_align="center", color=txt_col, weight=txt_wgt), 
                            ft.Text(tot_s, col={"sm": 3}, text_align="right", color=txt_col, weight=txt_wgt)
                        ]), 
                        on_click=evt_edit(item['raw_idx']), padding=5, border_radius=5, ink=True
                    )
                )
            page.update()

        def abrir_modal_item(e):
            if not verificar_permiso_edicion(): return
            res_inv = ft.ListView(expand=True, spacing=10, height=150)
            tipo_it = ft.RadioGroup(content=ft.Row([ft.Radio(value="P", label="Ítem Principal (Título)"), ft.Radio(value="S", label="Sub-ítem (Hijo)")]), value="P")
            m_cot = dropdown_modo_cot.value; pct_def = "19" if m_cot=="IVA" else "10"

            i_desc = ft.TextField(label="Descripción"); i_cant = ft.TextField(label="Cantidad", value="1", col={"sm": 3}); i_und_c = ft.TextField(label="Iniciales", visible=False, col={"sm": 3}); i_pre = ft.TextField(label="Precio Unit", value="0", col={"sm": 5})
            
            def cb_und(evt):
                if i_und.value == "✍️ ESCRIBIR...": i_cant.col={"sm": 2}; i_und.col={"sm": 3}; i_und_c.visible=True; i_pre.col={"sm": 4}; i_und_c.focus()
                else: i_cant.col={"sm": 3}; i_und.col={"sm": 4}; i_und_c.visible=False; i_pre.col={"sm": 5}
                page.update()
            def cb_imp(evt):
                if i_imp_t.value == "IVA": i_imp_p.value = "19"
                elif i_imp_t.value == "AIU": i_imp_p.value = "10"
                else: i_imp_p.value = "0"
                page.update()

            i_und = ft.Dropdown(label="Und", options=[ft.dropdown.Option(u) for u in ["ML", "UNID", "MTS", "GLB", "ROLLO", "DIA", "PAQ", "✍️ ESCRIBIR..."]], value="UNID", col={"sm": 4}, on_change=cb_und)
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
                            i_desc.value=desc; i_pre.value=str(int(float(prec)))
                            i_und.value = "ML" if ("TUBO" in desc.upper() or "CABLE" in desc.upper()) else ("GLB" if "INSTALACION" in desc.upper() else "UNID")
                            i_und_c.visible=False; i_cant.col={"sm":3}; i_und.col={"sm":4}; i_pre.col={"sm":5}; page.update()
                        subt = f"${int(float(p)):,}" + (f" (Prov: {prov})" if prov else "")
                        res_inv.controls.append(ft.ListTile(title=ft.Text(d, color="#fbbf24", size=14), subtitle=ft.Text(subt, color="#94a3b8"), on_click=sel))
                    db.close()
                page.update()

            def g_item(evt):
                if not i_desc.value: return
                try:
                    c=float(i_cant.value or 0); p=float(i_pre.value or 0); imp="EXENTO" if i_imp_t.value=="EXENTO" else f"{i_imp_t.value} {i_imp_p.value}%"
                    uf = str(i_und_c.value).upper().strip() if i_und.value=="✍️ ESCRIBIR..." else i_und.value; uf = uf or "UNID"
                    lista_items.append({"desc": i_desc.value, "cant": c, "precio": p, "total": c*p, "impuesto": imp, "und": uf, "tipo": tipo_it.value}); actualizar_tabla_visual()
                    i_desc.value=""; i_cant.value="1"; i_pre.value="0"; i_und.value="UNID"; i_und_c.value=""; i_und_c.visible=False; i_imp_t.value=m_cot; i_imp_p.value=pct_def; b_busq.value=""; b_inv(None)
                    page.snack_bar=ft.SnackBar(ft.Text("✅ Agregado"), bgcolor="#10b981"); page.snack_bar.open=True; page.update()
                except: pass

            b_busq = ft.TextField(label="Buscar en bodega...", on_change=b_inv)
            dlg = ft.AlertDialog(title=ft.Text("➕ Añadir"), content=ft.Container(width=750, content=ft.Column([tipo_it, b_busq, res_inv, i_desc, ft.ResponsiveRow([i_cant, i_und, i_und_c, i_pre]), ft.ResponsiveRow([i_imp_t, i_imp_p])], tight=True)), actions=[ft.ElevatedButton("Guardar", bgcolor="#10b981", on_click=g_item), ft.TextButton("Cerrar", on_click=lambda e: cerrar_dialogo(dlg))])
            page.dialog = dlg; dlg.open = True; b_inv(None)

        def abrir_modal_bodega(e):
            try:
                resultados_bod = ft.ListView(height=180)
                e_desc = ft.TextField(label="Nombre Producto")
                e_precio = ft.TextField(label="Precio Producto")
                e_mas = ft.TextField(multiline=True, min_lines=6, max_lines=10, label="Pega Excel (Col 1: Ítem | Col 2: Proveedor | Col 3: Precio)")
                
                c_item = ft.TextField(label="Buscar Ítem para cotizar...")
                lst_comp = ft.ListView(height=100, visible=False, spacing=2)
                c_p1 = ft.Dropdown(label="Proveedor 1", col={"sm": 6}); c_pr1 = ft.TextField(label="Precio 1", col={"sm": 6})
                c_p2 = ft.Dropdown(label="Proveedor 2", col={"sm": 6}); c_pr2 = ft.TextField(label="Precio 2", col={"sm": 6})
                c_p3 = ft.Dropdown(label="Proveedor 3", col={"sm": 6}); c_pr3 = ft.TextField(label="Precio 3", col={"sm": 6})

                e_pnom = ft.TextField(label="Nombre Proveedor*", col={"sm": 7}); e_ptel = ft.TextField(label="Teléfono", col={"sm": 5})
                # --- NUEVO: CAMPO DE TEXTO PARA CARGA MASIVA DE PROVEEDORES ---
                e_pmas = ft.TextField(multiline=True, min_lines=4, max_lines=8, label="Pega Excel (Col 1: Nombre Proveedor | Col 2: Teléfono)")
                lst_provs = ft.ListView(height=200)

                filtro_cat = ft.TextField(label="Filtrar catálogo completo...")
                lst_cat = ft.ListView(expand=True, spacing=5, height=300)

                def load_provs():
                    lst_provs.controls.clear(); ops = []
                    db = conectar_db()
                    if db:
                        c=db.cursor(); c.execute("SELECT nombre, telefono FROM proveedores ORDER BY nombre ASC")
                        for n, t in c.fetchall():
                            ops.append(ft.dropdown.Option(n))
                            def ed(ev, nom=n, tel=t): e_pnom.value=nom; e_ptel.value=tel; page.update()
                            def rm(ev, nom=n): 
                                dbd=conectar_db(); cd=dbd.cursor(); cd.execute("DELETE FROM proveedores WHERE nombre=%s", (nom,)); dbd.close(); load_provs()
                            lst_provs.controls.append(ft.ListTile(title=ft.Text(n, color="#fbbf24"), subtitle=ft.Text(f"Tel: {t}"), on_click=ed, trailing=ft.IconButton(ft.icons.DELETE, icon_color="#ef4444", on_click=rm)))
                        db.close()
                    c_p1.options=ops; c_p2.options=ops; c_p3.options=ops; page.update()

                def save_prov(ev):
                    if not e_pnom.value: return
                    db=conectar_db()
                    if db:
                        c=db.cursor(); c.execute("INSERT INTO proveedores (nombre, telefono) VALUES (%s,%s) ON CONFLICT(nombre) DO UPDATE SET telefono=EXCLUDED.telefono", (e_pnom.value.strip().upper(), e_ptel.value.strip()))
                        db.close(); e_pnom.value=""; e_ptel.value=""; load_provs(); page.snack_bar=ft.SnackBar(ft.Text("✅ Proveedor guardado"), bgcolor="#10b981"); page.snack_bar.open=True; page.update()

                # --- NUEVA FUNCIÓN PARA IMPORTAR PROVEEDORES DESDE EXCEL ---
                def p_mas_provs(evt):
                    if not e_pmas.value.strip(): return
                    db=conectar_db()
                    if db:
                        c=db.cursor(); ag=0
                        for l in e_pmas.value.strip().split('\n'):
                            p = l.split('\t')
                            if len(p)>=1 and p[0].strip():
                                n=sanitizar_texto(p[0].strip().upper())
                                t=sanitizar_texto(p[1].strip()) if len(p)>1 else ""
                                c.execute("INSERT INTO proveedores (nombre, telefono) VALUES (%s,%s) ON CONFLICT(nombre) DO UPDATE SET telefono=EXCLUDED.telefono", (n, t))
                                ag+=1
                        db.close(); e_pmas.value=""; load_provs(); page.snack_bar=ft.SnackBar(ft.Text(f"✅ {ag} proveedores guardados"), bgcolor="#10b981"); page.snack_bar.open=True; page.update()

                def b_bod(evt):
                    resultados_bod.controls.clear(); db = conectar_db()
                    if db:
                        c=db.cursor(); txt=(e_desc.value or "").upper()
                        try: c.execute("SELECT d, p, proveedor, fecha_act FROM inv WHERE UPPER(d) LIKE %s LIMIT 20", ('%'+txt+'%',))
                        except: c.execute("SELECT d, p, '' FROM inv WHERE UPPER(d) LIKE %s LIMIT 20", ('%'+txt+'%',))
                        
                        hoy_dt = datetime.now()
                        for r in c.fetchall():
                            d=r[0]; p=r[1]; prov=r[2] if len(r)>2 and r[2] else ""
                            fa_raw = r[3] if len(r)>3 and r[3] else None
                            fa = "Antigua"
                            if fa_raw:
                                try:
                                    if (hoy_dt - datetime.strptime(fa_raw, "%Y-%m-%d")).days <= 5: fa = fa_raw
                                except: pass
                            
                            def sel(ev, desc=d, prec=p): e_desc.value=desc; e_precio.value=str(int(float(prec))); page.update()
                            def rm(ev, desc=d): dbd=conectar_db(); cd=dbd.cursor(); cd.execute("DELETE FROM inv WHERE d=%s", (desc,)); dbd.close(); b_bod(None); load_cat(None)
                            subt = f"${int(float(p)):,}" + (f" (Prov: {prov})" if prov else "") + (f" - Act: {fa}")
                            resultados_bod.controls.append(ft.ListTile(title=ft.Text(d, size=13, color="#fbbf24", weight="bold"), subtitle=ft.Text(subt), on_click=sel, trailing=ft.IconButton(ft.icons.DELETE, icon_color="#ef4444", on_click=rm)))
                        db.close(); page.update()

                def s_bod(evt):
                    if not e_desc.value: return
                    db=conectar_db()
                    if db: 
                        fh = datetime.now().strftime("%Y-%m-%d")
                        c=db.cursor(); c.execute("INSERT INTO inv (d, p, stock, proveedor, fecha_act) VALUES (%s,%s,0,'',%s) ON CONFLICT(d) DO UPDATE SET p=EXCLUDED.p, fecha_act=EXCLUDED.fecha_act", (e_desc.value.upper(), float(e_precio.value or 0), fh)); db.close(); e_desc.value=""; e_precio.value=""; b_bod(None); load_cat(None); page.snack_bar=ft.SnackBar(ft.Text("✅ Guardado y fecha actualizada"), bgcolor="#2563eb"); page.snack_bar.open=True; page.update()

                def p_mas(evt):
                    if not e_mas.value.strip(): return
                    db=conectar_db()
                    if db:
                        c=db.cursor(); ag=0; fh = datetime.now().strftime("%Y-%m-%d")
                        evaluados = {}
                        for l in e_mas.value.strip().split('\n'):
                            pts = l.split('\t')
                            if len(pts)>=1 and pts[0].strip():
                                item = pts[0].strip().upper()
                                prov = sanitizar_texto(pts[1].strip().upper()) if len(pts)>=3 else ""
                                pr_str = "0"
                                if len(pts) >= 3: pr_str = pts[2]
                                elif len(pts) == 2: pr_str = pts[1]; prov = ""
                                try: pr = float(pr_str.replace("$","").replace(".","").replace(",","").replace(" ","").strip())
                                except: pr = 0.0
                                
                                if item not in evaluados: evaluados[item] = {"prov": prov, "prec": pr}
                                else:
                                    if pr < evaluados[item]["prec"]: evaluados[item] = {"prov": prov, "prec": pr}
                        
                        for itm, data in evaluados.items():
                            c.execute("INSERT INTO inv (d, p, stock, proveedor, fecha_act) VALUES (%s,%s,0,%s,%s) ON CONFLICT(d) DO UPDATE SET p=EXCLUDED.p, proveedor=EXCLUDED.proveedor, fecha_act=EXCLUDED.fecha_act", (itm, data["prec"], data["prov"], fh))
                            ag+=1
                        
                        db.commit(); db.close(); e_mas.value=""; b_bod(None); load_cat(None)
                        page.snack_bar=ft.SnackBar(ft.Text(f"✅ {ag} ítems evaluados y actualizados con éxito."), bgcolor="#10b981"); page.snack_bar.open=True; page.update()

                def b_comp(evt):
                    txt = (c_item.value or "").upper().strip(); lst_comp.controls.clear()
                    if len(txt) > 0:
                        db = conectar_db()
                        if db:
                            c=db.cursor(); c.execute("SELECT d FROM inv WHERE UPPER(d) LIKE %s LIMIT 10", ('%'+txt+'%',))
                            for r in c.fetchall():
                                def sel(e, desc=r[0]): c_item.value=desc; lst_comp.visible=False; page.update()
                                lst_comp.controls.append(ft.ListTile(title=ft.Text(r[0], color="#fbbf24"), on_click=sel))
                            db.close(); lst_comp.visible = len(lst_comp.controls)>0
                    else: lst_comp.visible = False
                    page.update()
                c_item.on_change = b_comp

                def run_comp(evt):
                    itm = c_item.value.strip().upper()
                    if not itm: return mostrar_alerta("Aviso", "Ingresa ítem.")
                    ofs = []
                    for pr, pc in [(c_p1.value, c_pr1.value), (c_p2.value, c_pr2.value), (c_p3.value, c_pr3.value)]:
                        if pr and pc:
                            try: ofs.append((pr, float(pc)))
                            except: pass
                    if not ofs: return mostrar_alerta("Aviso", "Ingresa al menos un proveedor con precio válido.")
                    gp, gpr = min(ofs, key=lambda x: x[1])
                    db = conectar_db()
                    if db:
                        fh = datetime.now().strftime("%Y-%m-%d")
                        c=db.cursor(); c.execute("INSERT INTO inv (d, p, stock, proveedor, fecha_act) VALUES (%s, %s, 0, %s, %s) ON CONFLICT(d) DO UPDATE SET p=EXCLUDED.p, proveedor=EXCLUDED.proveedor, fecha_act=EXCLUDED.fecha_act", (itm, gpr, gp, fh)); db.close()
                        c_item.value=""; c_p1.value=None; c_pr1.value=""; c_p2.value=None; c_pr2.value=""; c_p3.value=None; c_pr3.value=""; b_bod(None); load_cat(None)
                        page.snack_bar=ft.SnackBar(ft.Text(f"🏆 GANADOR: {gp} (${int(gpr):,}). Ítem actualizado."), bgcolor="#8b5cf6"); page.snack_bar.open=True; page.update()

                def load_cat(evt):
                    lst_cat.controls.clear(); txt = (filtro_cat.value or "").upper().strip(); db = conectar_db()
                    if db:
                        c = db.cursor()
                        try:
                            if txt: c.execute("SELECT d, p, proveedor, fecha_act FROM inv WHERE UPPER(d) LIKE %s ORDER BY fecha_act DESC NULLS LAST LIMIT 100", ('%'+txt+'%',))
                            else: c.execute("SELECT d, p, proveedor, fecha_act FROM inv ORDER BY fecha_act DESC NULLS LAST LIMIT 100")
                            
                            hoy_dt = datetime.now()
                            for r in c.fetchall():
                                d=r[0]; p=r[1]; prov=r[2] if len(r)>2 and r[2] else ""
                                fa_raw = r[3] if len(r)>3 and r[3] else None
                                fa = "Antigua"
                                
                                if fa_raw:
                                    try:
                                        if (hoy_dt - datetime.strptime(fa_raw, "%Y-%m-%d")).days <= 5: fa = fa_raw
                                    except: pass
                                
                                subt = f"Precio: ${int(float(p or 0)):,} | Prov: {prov or 'N/A'} | Act: {fa}"
                                lst_cat.controls.append(ft.ListTile(title=ft.Text(d, color="#fbbf24", weight="bold"), subtitle=ft.Text(subt, color="#94a3b8" if fa == "Antigua" else "#10b981")))
                        except Exception as ez: print(ez)
                        db.close(); page.update()

                filtro_cat.on_change = load_cat
                e_desc.on_change = b_bod
                
                dlg = ft.AlertDialog(
                    title=ft.Text("📦 Gestión de Bodega / Catálogo"), 
                    content=ft.Container(width=750, height=550, content=ft.Tabs(
                        selected_index=0, tabs=[
                            ft.Tab(text="🔍 Buscar", content=ft.Column([ft.Container(height=10), e_desc, e_precio, ft.ElevatedButton("Guardar Precio / Actualizar Fecha", bgcolor="#2563eb", on_click=s_bod), resultados_bod], tight=True)),
                            ft.Tab(text="📥 Masivo / Comparar", content=ft.Column([ft.Container(height=10), ft.Text("Si un ítem se repite con diferentes proveedores, el sistema elegirá el precio más bajo automáticamente.", color="#fbbf24", size=12), e_mas, ft.ElevatedButton("Importar y Analizar Ganadores", bgcolor="#10b981", on_click=p_mas)], tight=True)),
                            ft.Tab(text="⚖️ Comparador", content=ft.Column([ft.Container(height=10), ft.Text("Se elegirá el menor precio y se guardará en la BD principal con la Fecha de Hoy.", color="#10b981", size=12), c_item, lst_comp, ft.ResponsiveRow([c_p1, c_pr1]), ft.ResponsiveRow([c_p2, c_pr2]), ft.ResponsiveRow([c_p3, c_pr3]), ft.ElevatedButton("Analizar", bgcolor="#8b5cf6", color="white", on_click=run_comp)], tight=True, scroll=ft.ScrollMode.AUTO)),
                            ft.Tab(text="📜 Catálogo (Fechas)", content=ft.Column([ft.Container(height=10), ft.Text("Los ítems de más de 6 días se marcan como 'Antigua':", color="#fbbf24", size=12), filtro_cat, lst_cat], tight=True, scroll=ft.ScrollMode.AUTO)),
                            
                            # --- PESTAÑA PROVEEDORES MODIFICADA (CARGA MASIVA Y REPARADA) ---
                            ft.Tab(text="🏢 Provs.", content=ft.Column([
                                ft.Container(height=10), 
                                ft.Text("Ingreso Manual:", weight="bold", color="#fbbf24"),
                                ft.ResponsiveRow([e_pnom, e_ptel]), 
                                ft.ElevatedButton("Guardar Proveedor", bgcolor="#10b981", color="white", on_click=save_prov), 
                                ft.Divider(color="white24"),
                                ft.Text("Carga Masiva (Copiar y Pegar Excel):", weight="bold", color="#fbbf24"),
                                e_pmas,
                                ft.ElevatedButton("Importar Masivo", bgcolor="#2563eb", color="white", on_click=p_mas_provs),
                                ft.Divider(color="white24"),
                                lst_provs
                            ], tight=True, scroll=ft.ScrollMode.AUTO))
                        ], expand=1
                    )), actions=[ft.TextButton("Cerrar", on_click=lambda e: cerrar_dialogo(dlg))]
                )
                page.dialog = dlg; dlg.open = True; b_bod(None); load_provs(); load_cat(None)
            except Exception as bug:
                mostrar_alerta("Error abriendo Bodega", str(bug))

        def abrir_modal_clientes(e):
            r_cli = ft.ListView(expand=True, spacing=10, height=200)
            cn = ft.TextField(label="Nombre*", col={"sm":12}); ci = ft.TextField(label="NIT*", col={"sm":6}); ct = ft.TextField(label="Tel", col={"sm":6})
            cd = ft.TextField(label="Dir", col={"sm":6}); cc = ft.TextField(label="Ciudad", col={"sm":6}); ce = ft.TextField(label="Email", col={"sm":12})
            cm = ft.TextField(multiline=True, min_lines=8, max_lines=12, label="Pega Excel (Nom|NIT|Tel|Dir|Ciu|Mail)")

            def load_cli():
                r_cli.controls.clear(); db = conectar_db()
                if db:
                    c=db.cursor(); c.execute("SELECT n, i, ciu, tel FROM cli ORDER BY n ASC")
                    for n, i, ciu, tel in c.fetchall():
                        def ed(ev, nom=n): 
                            dbi=conectar_db(); ci=dbi.cursor(); ci.execute("SELECT n, i, dir, email, ciu, tel FROM cli WHERE n=%s", (nom,)); cd = ci.fetchone(); dbi.close()
                            if cd: cn.value, ci.value, cd.value, ce.value, cc.value, ct.value = cd; page.update()
                        def rm(ev, nom=n): dbd=conectar_db(); cd=dbd.cursor(); cd.execute("DELETE FROM cli WHERE n=%s", (nom,)); dbd.close(); load_cli()
                        r_cli.controls.append(ft.ListTile(title=ft.Text(n, color="#fbbf24"), subtitle=ft.Text(f"NIT:{i} | Ciu:{ciu} | Tel:{tel}"), on_click=ed, trailing=ft.IconButton(ft.icons.DELETE, icon_color="#ef4444", on_click=rm)))
                    db.close()
                page.update()

            def s_cli(ev):
                if not cn.value: return
                db=conectar_db()
                if db:
                    c=db.cursor(); c.execute("INSERT INTO cli (n, i, dir, email, ciu, tel) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT(n) DO UPDATE SET i=EXCLUDED.i, dir=EXCLUDED.dir, email=EXCLUDED.email, ciu=EXCLUDED.ciu, tel=EXCLUDED.tel", (cn.value.upper(), ci.value, cd.value, ce.value, cc.value, ct.value))
                    db.close(); cn.value=""; ci.value=""; cd.value=""; ce.value=""; cc.value=""; ct.value=""; load_cli(); page.snack_bar=ft.SnackBar(ft.Text("✅ Guardado"), bgcolor="#10b981"); page.snack_bar.open=True; page.update()

            def p_cli(ev):
                if not cm.value.strip(): return
                db=conectar_db()
                if db:
                    c=db.cursor(); ag=0
                    for l in cm.value.strip().split('\n'):
                        p = l.split('\t')
                        if len(p)>=1 and p[0].strip():
                            n=sanitizar_texto(p[0].strip().upper()); ni=sanitizar_texto(p[1].strip()) if len(p)>1 else ""; tl=sanitizar_texto(p[2].strip()) if len(p)>2 else ""; dr=sanitizar_texto(p[3].strip()) if len(p)>3 else ""; cu=sanitizar_texto(p[4].strip()) if len(p)>4 else ""; ml=sanitizar_texto(p[5].strip()) if len(p)>5 else ""
                            c.execute("INSERT INTO cli (n, i, tel, dir, ciu, email) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT(n) DO UPDATE SET i=EXCLUDED.i, tel=EXCLUDED.tel, dir=EXCLUDED.dir, ciu=EXCLUDED.ciu, email=EXCLUDED.email", (n, ni, tl, dr, cu, ml)); ag+=1
                    db.close(); cm.value=""; load_cli(); page.snack_bar=ft.SnackBar(ft.Text(f"✅ {ag} procesados"), bgcolor="#10b981"); page.snack_bar.open=True; page.update()

            dlg = ft.AlertDialog(
                title=ft.Text("👥 Gestión de Clientes"), 
                content=ft.Container(width=750, height=500, content=ft.Tabs(
                    selected_index=0, tabs=[
                        ft.Tab(text="Edición", content=ft.Column([ft.Container(height=10), ft.ResponsiveRow([cn, ci, ct, cd, cc, ce]), ft.ElevatedButton("Guardar", bgcolor="#10b981", on_click=s_cli), r_cli], tight=True, scroll=ft.ScrollMode.AUTO)),
                        ft.Tab(text="Carga Masiva", content=ft.Column([ft.Container(height=10), cm, ft.ElevatedButton("Importar", bgcolor="#10b981", on_click=p_cli)], tight=True))
                    ], expand=1
                )), actions=[ft.TextButton("Cerrar", on_click=lambda e: cerrar_dialogo(dlg))]
            ); page.dialog = dlg; dlg.open = True; load_cli()

        def abrir_modal_usuarios(e):
            pass_act = ft.TextField(label="Contraseña Actual", password=True, can_reveal_password=True)
            pass_new = ft.TextField(label="Nueva Contraseña", password=True, can_reveal_password=True)
            pass_conf = ft.TextField(label="Confirmar Nueva Contraseña", password=True, can_reveal_password=True)
            
            def guardar_clave(evt):
                if pass_new.value != pass_conf.value: return mostrar_alerta("Error", "Las contraseñas nuevas no coinciden.")
                db = conectar_db()
                if db:
                    c = db.cursor(); c.execute("SELECT password FROM usuarios WHERE usuario=%s", (sesion["usuario"],)); curr_pw = c.fetchone()[0]
                    if curr_pw != pass_act.value: db.close(); return mostrar_alerta("Error", "La contraseña actual es incorrecta.")
                    c.execute("UPDATE usuarios SET password=%s WHERE usuario=%s", (pass_new.value, sesion["usuario"])); db.close()
                    pass_act.value = ""; pass_new.value = ""; pass_conf.value = ""
                    page.snack_bar = ft.SnackBar(ft.Text("✅ Contraseña actualizada correctamente"), bgcolor="#10b981"); page.snack_bar.open = True; page.update()

            tab_clave = ft.Tab(text="🔑 Mi Clave", content=ft.Column([ft.Container(height=10), pass_act, pass_new, pass_conf, ft.ElevatedButton("Actualizar Contraseña", bgcolor="#f59e0b", color="black", on_click=guardar_clave)], tight=True))
            
            res_u = ft.ListView(expand=True, spacing=10, height=200); un = ft.TextField(label="Usuario*", col={"sm":4}); up = ft.TextField(label="Clave*", password=True, can_reveal_password=True, col={"sm":4}); ur = ft.Dropdown(label="Rol", options=[ft.dropdown.Option("ADMIN"), ft.dropdown.Option("ASESOR")], value="ASESOR", col={"sm":4})
            
            def load_u():
                res_u.controls.clear(); db=conectar_db()
                if db:
                    c=db.cursor(); c.execute("SELECT usuario, rol, bloqueado FROM usuarios ORDER BY usuario ASC")
                    for u, r, b in c.fetchall():
                        def ed(ev, u=u, r=r): un.value=u; ur.value=r; up.value=""; page.update()
                        def rm(ev, u=u): dbd=conectar_db(); cd=dbd.cursor(); cd.execute("DELETE FROM usuarios WHERE usuario=%s", (u,)); dbd.close(); load_u()
                        def dbq(ev, u=u): dbu=conectar_db(); cu=dbu.cursor(); cu.execute("UPDATE usuarios SET intentos=0, bloqueado=0 WHERE usuario=%s", (u,)); dbu.close(); load_u()
                        bts = [ft.IconButton(ft.icons.DELETE, icon_color="#ef4444", on_click=rm)]
                        if b==1: bts.insert(0, ft.IconButton(ft.icons.LOCK_OPEN, icon_color="#10b981", on_click=dbq))
                        res_u.controls.append(ft.ListTile(title=ft.Text(f"{u}{' (Bloqueado)' if b==1 else ''}", color="#ef4444" if b==1 else "#fbbf24"), subtitle=ft.Text(r), trailing=ft.Row(bts, tight=True), on_click=ed))
                    db.close(); page.update()
                    
            def sv_u(ev):
                if not un.value or not up.value: return
                db=conectar_db()
                if db:
                    c=db.cursor(); u = un.value.upper().strip(); c.execute("SELECT count(*) FROM usuarios WHERE usuario=%s", (u,))
                    if c.fetchone()[0]>0: c.execute("UPDATE usuarios SET password=%s, rol=%s, intentos=0, bloqueado=0 WHERE usuario=%s", (up.value.strip(), ur.value, u))
                    else: c.execute("INSERT INTO usuarios (usuario, password, rol, intentos, bloqueado) VALUES (%s,%s,%s,0,0)", (u, up.value.strip(), ur.value))
                    db.close(); un.value=""; up.value=""; ur.value="ASESOR"; load_u()

            tab_gest = ft.Tab(text="👥 Gestión", content=ft.Column([ft.Container(height=10), ft.ResponsiveRow([un, up, ur]), ft.ElevatedButton("Guardar", bgcolor="#8b5cf6", color="white", on_click=sv_u), res_u], tight=True))

            tabs_list = [tab_clave]
            
            if sesion["usuario"] in ["OMERA", "PLEAL"]:
                tabs_list.append(tab_gest)
            
            dlg = ft.AlertDialog(title=ft.Text("🔐 Usuarios y Seguridad"), content=ft.Container(width=700, height=400, content=ft.Tabs(selected_index=0, tabs=tabs_list)), actions=[ft.TextButton("Cerrar", on_click=lambda e: cerrar_dialogo(dlg))])
            page.dialog = dlg; dlg.open = True
            
            if sesion["usuario"] in ["OMERA", "PLEAL"]: load_u()
            else: page.update()

        def abrir_modal_historial(e):
            res_h = ft.ListView(expand=True, spacing=10, height=300); bus_h = ft.TextField(label="Buscar cliente...", width=400)
            def load_h(evt=None):
                res_h.controls.clear(); txt=(bus_h.value or "").upper().strip(); db=conectar_db()
                if db:
                    c=db.cursor()
                    if txt: c.execute("SELECT nro, cliente, fecha, total, creador, permitidos FROM historial WHERE UPPER(cliente) LIKE %s ORDER BY nro DESC LIMIT 50", ('%'+txt+'%',))
                    else: c.execute("SELECT nro, cliente, fecha, total, creador, permitidos FROM historial ORDER BY nro DESC LIMIT 30")
                    for nr, cl, fc, tt, cr, perm in c.fetchall():
                        permitidos_list = [p.strip() for p in (perm or "").split(",") if p.strip()]
                        
                        def c_cot(ev, nro=nr, creador=cr, perm_list=permitidos_list):
                            dbh=conectar_db(); ch=dbh.cursor()
                            ch.execute("SELECT cli, nit, atn, ref, ciu_origen, t_entrega, validez, pago, garantia, notas, modo, pct_a, pct_i, pct_u, pct_iva_u FROM h_cab WHERE nro=%s", (nro,))
                            cab = ch.fetchone()
                            if cab:
                                input_cliente.value=cab[0] or ""; input_nit.value=cab[1] or ""; input_atencion.value=cab[2] or ""; input_ref.value=cab[3] or ""; input_ciudad.value=cab[4] or "Yumbo"; input_tiempo_entrega.value=cab[5] or "4 Días hábiles"; input_validez.value=cab[6] or "20 Días"; input_pago.value=cab[7] or "30 Días"; input_garantia.value=cab[8] or "6 meses en mano de obra"; input_notas.value=cab[9] or ""
                                dropdown_modo_cot.value=cab[10] or "AIU"; input_pct_a.value=str(cab[11]) if cab[11] is not None else "10"; input_pct_i.value=str(cab[12]) if cab[12] is not None else "2"; input_pct_u.value=str(cab[13]) if cab[13] is not None else "8"; input_pct_iva_u.value=str(cab[14]) if cab[14] is not None else "19"
                                es_aiu = dropdown_modo_cot.value=="AIU"; container_texto_aiu.visible=es_aiu; cont_a.visible=es_aiu; cont_i.visible=es_aiu; cont_u.visible=es_aiu; cont_iva_u.visible=es_aiu
                            lista_items.clear()
                            ch.execute('SELECT "desc", cant, und, unit, sub, imp, tipo FROM h_det WHERE nro=%s', (nro,))
                            for d in ch.fetchall():
                                ds=d[0] or ""; ct=float(d[1] or 0); ud=str(d[2] or "UNID"); ut=float(d[3] or 0); sb=float(d[4] or (ct*ut)); im=str(d[5] or "EXENTO"); tp=str(d[6] or "P")
                                if "AIU" in ud or "IVA" in ud or "EXENTO" in ud: t=im; im=ud; ud=t if t not in ["EXENTO", ""] else "UNID"
                                lista_items.append({"desc": ds, "cant": ct, "und": ud, "precio": ut, "total": sb, "impuesto": im, "tipo": tp})
                            dbh.close()
                            estado["nro_edicion"]=nro; estado["creador_edicion"]=creador; estado["permitidos_edicion"] = perm_list
                            actualizar_tabla_visual(); cerrar_dialogo(dlg)
                            
                            if creador and creador not in ["SISTEMA", sesion["usuario"]] and sesion["usuario"] not in perm_list:
                                page.snack_bar=ft.SnackBar(ft.Text(f"👁️ Solo lectura (creado por {creador}). Podrás generar un PDF pero sin alterar la BD."), bgcolor="#3b82f6"); page.snack_bar.open=True; page.update()
                        
                        trail_btns = []
                        if cr == sesion["usuario"]:
                            def share_cot(ev, nro_val=nr, actual_perms=permitidos_list):
                                db_s = conectar_db(); ops = []
                                if db_s:
                                    c_s = db_s.cursor(); c_s.execute("SELECT usuario FROM usuarios WHERE usuario != %s", (sesion["usuario"],))
                                    for ur in c_s.fetchall(): ops.append(ft.dropdown.Option(ur[0]))
                                    db_s.close()
                                
                                usr_drop = ft.Dropdown(label="Seleccionar Usuario a dar permiso", options=ops)
                                def grant_perm(ev2):
                                    if usr_drop.value:
                                        if usr_drop.value not in actual_perms:
                                            new_perms_list = actual_perms + [usr_drop.value]
                                            new_perms_str = ",".join(new_perms_list)
                                            db2 = conectar_db()
                                            if db2:
                                                c2 = db2.cursor(); c2.execute("UPDATE historial SET permitidos=%s WHERE nro=%s", (new_perms_str, nro_val)); db2.close()
                                                cerrar_dialogo(dlg_share); load_h()
                                                page.snack_bar = ft.SnackBar(ft.Text(f"✅ Permiso concedido a {usr_drop.value}"), bgcolor="#10b981"); page.snack_bar.open=True; page.update()
                                        else: mostrar_alerta("Aviso", "El usuario ya tiene permisos.")
                                
                                dlg_share = ft.AlertDialog(title=ft.Text(f"🤝 Compartir Cotización {nro_val}"), content=ft.Column([ft.Text("Otorga permiso de edición a un compañero:"), usr_drop], tight=True), actions=[ft.ElevatedButton("Dar Permiso", bgcolor="#10b981", color="white", on_click=grant_perm), ft.TextButton("Cancelar", on_click=lambda ev: cerrar_dialogo(dlg_share))])
                                page.dialog = dlg_share; dlg_share.open = True; page.update()
                            
                            trail_btns.append(ft.IconButton(ft.icons.SHARE, icon_color="#3b82f6", tooltip="Compartir Permisos", on_click=share_cot))

                        res_h.controls.append(ft.ListTile(title=ft.Text(f"N° {nr} - {cl} (Por: {cr})", color="#fbbf24"), subtitle=ft.Text(f"{fc} | ${int(float(tt)):,}"), on_click=c_cot, trailing=ft.Row(trail_btns, tight=True) if trail_btns else None))
                db.close(); page.update()
            bus_h.on_change = load_h
            dlg = ft.AlertDialog(title=ft.Text("🔍 Historial"), content=ft.Container(width=700, content=ft.Column([bus_h, res_h], tight=True)), actions=[ft.TextButton("Cerrar", on_click=lambda e: cerrar_dialogo(dlg))])
            page.dialog = dlg; dlg.open = True; load_h()

        def abrir_modal_sistema(e):
            def generar_backup_json(evt):
                db = conectar_db()
                if db:
                    c = db.cursor(); b_data = {}; tablas = ["usuarios", "cli", "inv", "proveedores", "historial", "h_cab", "h_det", "n_cot"]
                    for t in tablas:
                        try:
                            c.execute(f"SELECT * FROM {t}"); cols = [desc[0] for desc in c.description]; rows = c.fetchall(); b_data[t] = {"cols": cols, "rows": rows}
                        except: pass
                    db.close()
                    
                    fecha_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                    usr = sesion["usuario"]
                    nombre_base = f"backup_ingectec_{usr}_{fecha_str}"
                    
                    with open(f"assets/{nombre_base}.json", "w", encoding="utf-8") as f: json.dump(b_data, f, default=str)
                    
                    import zipfile
                    with zipfile.ZipFile(f"assets/{nombre_base}.zip", "w", zipfile.ZIP_DEFLATED) as zipf:
                        zipf.write(f"assets/{nombre_base}.json", arcname=f"{nombre_base}.json")
                        
                    page.launch_url(f'/{nombre_base}.zip')
                    page.snack_bar = ft.SnackBar(ft.Text(f"✅ Backup {nombre_base}.zip descargado."), bgcolor="#2563eb"); page.snack_bar.open = True; page.update()

            e_json = ft.TextField(multiline=True, min_lines=6, max_lines=10, label="Pega aquí el contenido de tu archivo backup_ingectec.json")
            
            def subir_backup_json(evt):
                if not e_json.value.strip(): return
                try:
                    data = json.loads(e_json.value.strip()); db = conectar_db()
                    if db:
                        c = db.cursor()
                        for t, tdata in data.items():
                            c.execute(f"DELETE FROM {t}"); cols = tdata.get("cols", []); rows = tdata.get("rows", [])
                            if cols and rows:
                                col_names = ", ".join(cols); placeholders = ", ".join(["%s"] * len(cols))
                                for row in rows: c.execute(f"INSERT INTO {t} ({col_names}) VALUES ({placeholders})", tuple(row))
                        db.close(); page.snack_bar = ft.SnackBar(ft.Text("✅ Backup restaurado con éxito"), bgcolor="#10b981"); page.snack_bar.open = True; page.update(); e_json.value = ""
                except Exception as ex: mostrar_alerta("Error", f"Archivo JSON inválido o corrupto: {str(ex)}")

            def confirmar_reseteo(evt):
                ic = ft.TextField(label="Contraseña Maestra", password=True)
                def ex(e):
                    if ic.value.strip() == "7705178":
                        db=conectar_db()
                        if db:
                            c=db.cursor(); c.execute("DELETE FROM cli"); c.execute("DELETE FROM inv"); c.execute("DELETE FROM historial"); c.execute("DELETE FROM h_cab"); c.execute("DELETE FROM h_det"); c.execute("UPDATE n_cot SET num=100 WHERE id=1"); db.close()
                        cerrar_dialogo(dc); cerrar_dialogo(dlg_sis); page.snack_bar=ft.SnackBar(ft.Text("✅ RESTAURADO"), bgcolor="#10b981"); page.snack_bar.open=True; page.update()
                dc = ft.AlertDialog(title=ft.Text("⚠️ ADVERTENCIA EXTREMA", color="#ef4444"), content=ft.Column([ft.Text("Se borrará TODO."), ic], tight=True), actions=[ft.ElevatedButton("BORRAR", bgcolor="#ef4444", on_click=ex), ft.TextButton("Cancelar", on_click=lambda e: cerrar_dialogo(dc))])
                page.dialog = dc; dc.open = True; page.update()

            col_general = [
                ft.Container(height=10), 
                ft.ElevatedButton("📥 1. DESCARGAR BACKUP", bgcolor="#2563eb", color="white", width=350, on_click=generar_backup_json)
            ]
            
            if sesion["usuario"] in ["OMERA", "PLEAL"]:
                col_general.extend([
                    ft.Container(height=20), 
                    ft.Text("ZONA DE PELIGRO:", color="#ef4444", weight="bold"), 
                    ft.ElevatedButton("⚠️ 2. RESTAURAR DE FÁBRICA", bgcolor="#ef4444", color="white", width=350, on_click=confirmar_reseteo)
                ])

            dlg_sis = ft.AlertDialog(
                title=ft.Text("⚙️ Configuración del Sistema"),
                content=ft.Container(width=600, height=400, content=ft.Tabs(
                    selected_index=0, tabs=[
                        ft.Tab(text="General", content=ft.Column(col_general, tight=True)),
                        ft.Tab(text="Subir Backup", content=ft.Column([ft.Container(height=10), ft.Text("Abre tu archivo .json, copia todo el texto y pégalo aquí:", size=12, color="white54"), e_json, ft.ElevatedButton("RESTAURAR INFORMACIÓN", bgcolor="#10b981", color="white", on_click=subir_backup_json)], tight=True))
                    ]
                )), actions=[ft.TextButton("Cerrar", on_click=lambda e: cerrar_dialogo(dlg_sis))]
            )
            page.dialog = dlg_sis; dlg_sis.open = True; page.update()

        def limpiar_todo(e):
            lista_items.clear(); estado["nro_edicion"] = None; estado["creador_edicion"] = None; estado["permitidos_edicion"] = []; actualizar_tabla_visual()
            input_cliente.value = ""; input_nit.value = ""; input_atencion.value = ""; input_ref.value = ""; input_ciudad.value = "Yumbo"; input_tiempo_entrega.value = "4 Días hábiles"; input_validez.value = "20 Días"; input_pago.value = "30 Días"; input_garantia.value = "6 meses en mano de obra"; input_notas.value = "Toda la actividad será coordinada por el ingeniero Edward Álvarez y/o John Paniagua"; dropdown_modo_cot.value = "AIU"; input_pct_a.value = "10"; input_pct_i.value = "2"; input_pct_u.value = "8"; input_pct_iva_u.value = "19"; lista_busqueda_cli.visible = False; cambiar_modo_cot(None); page.update()

        def generar_pdf_web(e):
            try:
                if not lista_items or not input_cliente.value: return mostrar_alerta("Aviso", "Faltan datos.")
                
                puede_guardar = verificar_permiso_edicion(mostrar_aviso=False)

                c_nom = sanitizar_texto(input_cliente.value or "").upper().strip(); c_nit = sanitizar_texto(input_nit.value or "").strip(); c_ciu_origen = sanitizar_texto(input_ciudad.value or "Yumbo").strip(); c_atn = sanitizar_texto(input_atencion.value or "").strip(); c_ref = sanitizar_texto(input_ref.value or "").strip(); c_t_entrega = sanitizar_texto(input_tiempo_entrega.value or "").strip(); c_validez = sanitizar_texto(input_validez.value or "").strip(); c_pago = sanitizar_texto(input_pago.value or "").strip(); c_garantia = sanitizar_texto(input_garantia.value or "").strip(); c_notas = sanitizar_texto(input_notas.value or "").strip(); c_modo = dropdown_modo_cot.value or "AIU"
                try: pct_a = float(input_pct_a.value)
                except: pct_a = 0.0
                try: pct_i = float(input_pct_i.value)
                except: pct_i = 0.0
                try: pct_u = float(input_pct_u.value)
                except: pct_u = 0.0
                try: pct_iva_u = float(input_pct_iva_u.value)
                except: pct_iva_u = 0.0

                c_dir = ""; c_email = ""; c_ciu_cli = ""; c_tel = ""
                db = conectar_db()
                try:
                    c = db.cursor(); c.execute("SELECT dir, email, ciu, tel FROM cli WHERE n=%s", (c_nom,))
                    cli_d = c.fetchone()
                    if cli_d: c_dir=sanitizar_texto(cli_d[0] or ""); c_email=sanitizar_texto(cli_d[1] or ""); c_ciu_cli=sanitizar_texto(cli_d[2] or ""); c_tel=sanitizar_texto(cli_d[3] or "")
                except: pass

                nro_doc = estado["nro_edicion"]
                mes_act = datetime.now().strftime("%m")
                
                subtotal = 0; iva_bases = {}
                for i in lista_items:
                    cn=float(i['cant']); un=float(i['precio']); tot=float(i['total']); imps=i.get('impuesto', 'EXENTO'); u_s=i.get('und', 'UNID'); t_v=i.get('tipo', 'P')
                    subtotal += tot
                    if "IVA" in imps.upper():
                        try: pct = float(re.findall(r"[\d.]+", imps)[0]); iva_bases[pct] = iva_bases.get(pct, 0) + tot
                        except: pass

                val_a = subtotal * (pct_a / 100); val_i = subtotal * (pct_i / 100); val_u = subtotal * (pct_u / 100); tot_aiu = val_a + val_i + val_u; val_iva_u = val_u * (pct_iva_u / 100)
                tot_fin = (subtotal + tot_aiu + val_iva_u) if c_modo == "AIU" else subtotal
                for p_iva, b_amt in iva_bases.items(): tot_fin += b_amt * (p_iva / 100)

                if puede_guardar:
                    c_up = db.cursor()
                    if not nro_doc:
                        c_up.execute("UPDATE n_cot SET num = num + 1 WHERE id=1 RETURNING num")
                        nf = c_up.fetchone(); num_p = nf[0] if nf else 100; nro_doc = f"{mes_act}-{num_p:03d}"
                        estado["nro_edicion"] = nro_doc
                    else:
                        c_up.execute("DELETE FROM h_cab WHERE nro=%s", (nro_doc,)); c_up.execute("DELETE FROM h_det WHERE nro=%s", (nro_doc,)); c_up.execute("DELETE FROM historial WHERE nro=%s", (nro_doc,))
                        
                    c_up.execute("INSERT INTO cli (n, i) VALUES (%s, %s) ON CONFLICT(n) DO NOTHING", (c_nom, c_nit))
                    c_up.execute("""INSERT INTO h_cab (nro, cli, nit, atn, ref, ciu_origen, t_entrega, validez, pago, garantia, notas, modo, pct_a, pct_i, pct_u, pct_iva_u) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", (nro_doc, c_nom, c_nit, c_atn, c_ref, c_ciu_origen, c_t_entrega, c_validez, c_pago, c_garantia, c_notas, c_modo, pct_a, pct_i, pct_u, pct_iva_u))
                    
                    for i in lista_items:
                        cn=float(i['cant']); un=float(i['precio']); tot=float(i['total']); imps=i.get('impuesto', 'EXENTO'); u_s=i.get('und', 'UNID'); t_v=i.get('tipo', 'P')
                        c_up.execute('INSERT INTO h_det (nro, "desc", cant, und, unit, sub, imp, tipo) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)', (nro_doc, i['desc'], cn, u_s, un, tot, imps, t_v))
                        
                    nom_limp = re.sub(r'[^\w\s-]', '', c_nom).strip(); nom_arc = f"{nom_limp}-{nro_doc}.pdf"
                    
                    c_up.execute("SELECT permitidos FROM historial WHERE nro=%s", (nro_doc,))
                    row_perm = c_up.fetchone(); perm_string = row_perm[0] if row_perm else ""
                    
                    creador_final = estado.get("creador_edicion") or sesion["usuario"]
                    c_up.execute("INSERT INTO historial (nro, cliente, fecha, archivo, total, origen, creador, permitidos) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", (nro_doc, c_nom, datetime.now().strftime("%Y-%m-%d %H:%M"), nom_arc, tot_fin, "WEB", creador_final, perm_string))
                else:
                    if not nro_doc: nro_doc = f"{mes_act}-TEMP"
                    nom_limp = re.sub(r'[^\w\s-]', '', c_nom).strip(); nom_arc = f"{nom_limp}-{nro_doc}.pdf"
                    
                db.close()

                asesor_impresion = (estado.get("creador_edicion") or sesion["usuario"]).upper()
                
                numeros_whatsapp = {"OMERA": "573175046404", "YRESTREPO": "573002986963", "JCARDONA": "573225532559", "PLEAL": "573175046404"}
                numero_asesor = numeros_whatsapp.get(asesor_impresion, "573175046404")
                qr = qrcode.QRCode(box_size=10, border=2); qr.add_data(f"https://wa.me/{numero_asesor}"); qr.make(fit=True); qr.make_image(fill_color="black", back_color="white").save("assets/qr_temp.png")

                nombres_completos = {"OMERA": "OSCAR MERA", "YRESTREPO": "YEISON FABIAN RESTREPO", "JCARDONA": "JOHN JAIRO CARDONA", "PLEAL": "PAULO ANDRES LEAL GARCIA"}
                p = PDF(); p.asesor_nombre = nombres_completos.get(asesor_impresion, asesor_impresion) 
                
                p.set_margins(10, 10, 10); p.set_auto_page_break(auto=True, margin=30); p.add_page()
                p.set_font('helvetica', 'B', 11); hy = datetime.now()
                p.cell(0, 5, sanitizar_texto(f"{c_ciu_origen}, {hy.day} de {['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'][hy.month-1]} de {hy.year}"), border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT); p.ln(4)

                y_st = p.get_y(); lin_dir = c_dir
                if c_ciu_cli: lin_dir = f"{c_dir} - {c_ciu_cli}".strip(" -")
                lc = 1 + (1 if c_atn else 0) + (1 if c_nom else 0) + (1 if c_nit else 0) + (1 if lin_dir else 0) + (1 if c_tel else 0) + (1 if c_email else 0)
                
                p.set_fill_color(240, 240, 240); p.rounded_rect(8, y_st - 2, 105, (lc * 5) + 4, r=3, style='F'); p.rounded_rect(118, y_st - 2, 84, 14, r=3, style='F') 
                p.set_xy(10, y_st); p.cell(0, 5, "Señores:", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                
                if c_atn: p.set_font('helvetica', 'B', 11); p.set_text_color(31, 73, 125); p.cell(110, 5, c_atn, border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                p.set_text_color(0, 0, 0); p.set_font('helvetica', 'B', 11); p.cell(110, 5, c_nom, border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT); p.set_font('helvetica', '', 11)
                if c_nit: p.cell(110, 5, f"NIT / CC: {c_nit}", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                if lin_dir: p.cell(110, 5, lin_dir, border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                if c_tel: p.cell(110, 5, f"Tel: {c_tel}", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                if c_email: p.cell(110, 5, f"Email: {c_email}", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                
                y_ed = p.get_y(); p.set_xy(120, y_st + 2); p.set_font('helvetica', 'B', 12); p.set_text_color(31, 73, 125); p.cell(80, 5, f"COTIZACIÓN ING {nro_doc}", border=0, align='C'); p.set_text_color(0, 0, 0) 
                p.set_y(max(y_ed, y_st + 10) + 5)
                if c_ref:
                    ysr = p.get_y(); nl = (len("REFERENCIA: " + c_ref) // 85) + 1  
                    p.set_fill_color(240, 240, 240); p.rounded_rect(8, ysr - 2, 194, (nl * 5) + 4, r=3, style='F')
                    p.set_font('helvetica', 'B', 11); p.set_text_color(31, 73, 125); p.write(5, "REFERENCIA: "); p.set_font('helvetica', '', 11); p.set_text_color(0, 0, 0); p.write(5, f"{c_ref}\n"); p.ln(5)

                p.set_fill_color(194, 229, 194); p.set_text_color(0, 0, 0); p.set_font("helvetica", '', 8) 
                p.cell(10, 6, "ITEM", 1, fill=True, align='C'); p.cell(78, 6, "DESCRIPCION", 1, fill=True, align='C'); p.cell(12, 6, "CANT", 1, fill=True, align='C'); p.cell(25, 6, "UND", 1, fill=True, align='C')
                p.cell(20, 6, "V. UNIT", 1, fill=True, align='C'); p.cell(20, 6, "IMPUESTO", 1, fill=True, align='C'); p.cell(25, 6, "VALOR", 1, fill=True, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

                p.set_fill_color(255, 255, 255)
                
                for idx, i in enumerate(obtener_items_procesados(lista_items)):
                    is_title = bool(i['tipo'] == 'P' and i.get('has_subs', False))
                    
                    if is_title: 
                        c_s=""; u_s=""; pu=""; imps=""; tot_s=f"${int(i['total']):,}" if i['total']>0 else ""
                        p.set_fill_color(255, 248, 204) 
                        p.set_font('helvetica', 'B', 8)
                    elif i['tipo'] == 'P': 
                        c_s=f"{i['cant']:g}" if i['cant']>0 else ""; u_s=sanitizar_texto(i['und']) if i['cant']>0 else ""; pu=f"${int(i['precio']):,}" if i['total']>0 else ""; imps=sanitizar_texto(i['impuesto']) if i['total']>0 else ""; tot_s=f"${int(i['total']):,}" if i['total']>0 else ""
                        p.set_fill_color(255, 255, 255)
                        p.set_font('helvetica', '', 8)
                    else: 
                        c_s=f"{i['cant']:g}" if i['cant']>0 else ""; u_s=sanitizar_texto(i['und']) if i['cant']>0 else ""; pu=""; imps=""; tot_s=""
                        p.set_fill_color(255, 255, 255)
                        p.set_font('helvetica', '', 8)

                    d_lin = textwrap.wrap(sanitizar_texto(i['desc']), width=43) or [""]
                    for li, l_txt in enumerate(d_lin):
                        bs = 1 if len(d_lin)==1 else ('LTR' if li==0 else ('LBR' if li==len(d_lin)-1 else 'LR'))
                        if li == 0:
                            p.cell(10, 6, i['num'], border=bs, align='C', fill=is_title); p.cell(78, 6, f" {l_txt}", border=bs, fill=is_title); p.cell(12, 6, c_s, border=bs, align='C', fill=is_title); p.cell(25, 6, u_s, border=bs, align='C', fill=is_title); p.cell(20, 6, pu, border=bs, align='R', fill=is_title); p.cell(20, 6, imps, border=bs, align='C', fill=is_title); p.cell(25, 6, tot_s, border=bs, align='R', fill=is_title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                        else:
                            p.cell(10, 6, "", border=bs, align='C', fill=is_title); p.cell(78, 6, f" {l_txt}", border=bs, fill=is_title); p.cell(12, 6, "", border=bs, align='C', fill=is_title); p.cell(25, 6, "", border=bs, align='C', fill=is_title); p.cell(20, 6, "", border=bs, align='R', fill=is_title); p.cell(20, 6, "", border=bs, align='C', fill=is_title); p.cell(25, 6, "", border=bs, align='R', fill=is_title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

                def p_tot(lbl, val, b=False):
                    if b: p.set_font('helvetica', 'B', 9)
                    p.set_x(135); p.cell(40, 5, sanitizar_texto(lbl), 1, align='C'); p.cell(25, 5, f"$ {int(val):,}", 1, align='R', new_x=XPos.LMARGIN, new_y=YPos.NEXT) 
                    if b: p.set_font('helvetica', '', 9)

                p.set_font('helvetica', '', 9); p_tot("SUBTOTAL", subtotal)
                if c_modo == "AIU": p_tot(f"ADMINISTRACIÓN ({pct_a:g}%)", val_a); p_tot(f"IMPREVISTOS ({pct_i:g}%)", val_i); p_tot(f"UTILIDAD ({pct_u:g}%)", val_u); p_tot("TOTAL AIU", tot_aiu, True); p_tot(f"IVA S/UTILIDAD ({pct_iva_u:g}%)", val_iva_u)
                for pv, ba in iva_bases.items(): p_tot(f"IVA ({pv:g}%)", ba * (pv / 100))
                p_tot("TOTAL", tot_fin, True)

                p.ln(10); p.set_font('helvetica', 'B', 10); p.cell(0, 5, "CONDICIONES COMERCIALES", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT); p.ln(2); p.set_font('helvetica', '', 10)
                p.cell(0, 5, f"- Tiempo de entrega: {c_t_entrega}", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT); p.cell(0, 5, f"- Validez de la cotizacion: {c_validez}", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT); p.cell(0, 5, f"- Forma de pago: {c_pago}", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT); p.cell(0, 5, f"- Garantia: {c_garantia}", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                if c_notas: p.multi_cell(0, 5, f"- Notas: {c_notas}", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                
                p.ln(8); p.set_font("helvetica", 'B', 8); p.cell(0, 5, "Escanee este código para atención personalizada y directa con nuestra Gerencia.", border=0, align='L', new_x=XPos.LMARGIN, new_y=YPos.NEXT); p.image("assets/qr_temp.png", 10, p.get_y(), 25, 25)

                p.output(f"assets/{nom_arc}")
                try: os.remove("assets/qr_temp.png")
                except: pass
                
                if not puede_guardar:
                    page.snack_bar = ft.SnackBar(ft.Text("⚠️ Modo Lectura: PDF de consulta generado. Original sin alterar.", color="black"), bgcolor="#f59e0b")
                    page.snack_bar.open = True
                
                dlg_d = ft.AlertDialog(title=ft.Text("✅ Generado", color="#10b981"), content=ft.Text(f"Archivo: {nom_arc}"), actions=[ft.ElevatedButton("📥 DESCARGAR", bgcolor="#2563eb", color="white", on_click=lambda ev: page.launch_url(f"/{nom_arc}")), ft.TextButton("Cerrar", on_click=lambda ev: cerrar_dialogo(dlg_d))])
                page.dialog = dlg_d; dlg_d.open = True; page.update()
            except Exception as eFallo: mostrar_alerta("Error al generar PDF", f"Hubo un fallo: {str(eFallo)}")

        botones_lista = [
            ft.ElevatedButton("AÑADIR ÍTEM", icon=ft.icons.ADD, bgcolor="#f59e0b", color="black", on_click=abrir_modal_item),
            ft.ElevatedButton("BODEGA", icon=ft.icons.INVENTORY_2, bgcolor="#334155", color="white", on_click=abrir_modal_bodega),
            ft.ElevatedButton("CLIENTES", icon=ft.icons.GROUPS, bgcolor="#334155", color="white", on_click=abrir_modal_clientes),
            ft.ElevatedButton("USUARIOS", icon=ft.icons.SECURITY, bgcolor="#334155", color="white", on_click=abrir_modal_usuarios),
            ft.ElevatedButton("HISTORIAL", icon=ft.icons.HISTORY, bgcolor="#334155", color="white", on_click=abrir_modal_historial),
            ft.ElevatedButton("LIMPIAR", icon=ft.icons.DELETE_SWEEP, bgcolor="#475569", color="white", on_click=limpiar_todo)
        ]
        
        if sesion["usuario"] in ["OMERA", "PLEAL"]: 
            botones_lista.append(ft.ElevatedButton("SISTEMA", icon=ft.icons.SETTINGS, bgcolor="#475569", color="white", on_click=abrir_modal_sistema))
            
        botones_lista.append(ft.ElevatedButton("SALIR", icon=ft.icons.LOGOUT, bgcolor="#ef4444", color="white", on_click=lambda e: mostrar_login()))

        contenedor_botones = ft.Container(
            content=ft.Row(
                botones_lista, 
                wrap=True, 
                alignment=ft.MainAxisAlignment.CENTER, 
                spacing=10
            ),
            alignment=ft.alignment.center,
            margin=ft.margin.only(bottom=15, top=5)
        )

        tabla = ft.Container(content=ft.Column([ft.Row([ft.Text(f"COTIZACIÓN ING {nro_actual}", weight="bold", color="#fbbf24", size=16)], alignment=ft.MainAxisAlignment.CENTER), ft.Divider(color="white24"), ft.ResponsiveRow([ft.Text("DESCRIPCIÓN (Clic para editar)", weight="bold", color="#fbbf24", col={"sm": 6}, text_align="center"), ft.Text("CANTIDAD", weight="bold", color="#fbbf24", col={"sm": 3}, text_align="center"), ft.Text("TOTAL", weight="bold", color="#fbbf24", col={"sm": 3}, text_align="center")]), columna_tabla_items, ft.Container(height=10)]), bgcolor="#0f172a", padding=15, border_radius=8, border=ft.border.all(1, "white12"))
        
        f_cli = ft.Container(content=ft.Column([
            ft.ResponsiveRow([ft.Column([input_cliente, lista_busqueda_cli], col={"sm": 12, "md": 5, "lg": 5}), ft.Container(content=input_nit, col={"sm": 6, "md": 3, "lg": 3}), ft.Container(content=input_ciudad, col={"sm": 6, "md": 4, "lg": 4})]),
            ft.ResponsiveRow([ft.Container(content=input_atencion, col={"sm": 12, "md": 4, "lg": 4}), ft.Container(content=input_ref, col={"sm": 12, "md": 8, "lg": 8})]),
            ft.ResponsiveRow([ft.Container(content=input_tiempo_entrega, col={"sm": 6, "md": 3, "lg": 3}), ft.Container(content=input_validez, col={"sm": 6, "md": 3, "lg": 3}), ft.Container(content=input_pago, col={"sm": 6, "md": 3, "lg": 3}), ft.Container(content=input_garantia, col={"sm": 6, "md": 3, "lg": 3})]),
            ft.ResponsiveRow([ft.Container(content=input_notas, col={"sm": 12, "md": 12, "lg": 12})]),
            ft.ResponsiveRow([ft.Container(content=dropdown_modo_cot, col={"sm": 6, "md": 2, "lg": 2}), container_texto_aiu, cont_a, cont_i, cont_u, cont_iva_u], vertical_alignment=ft.CrossAxisAlignment.CENTER)
        ], spacing=10), bgcolor="#0f172a", padding=15, border_radius=8, border=ft.border.all(1, "white12"))

        page.add(
            ft.Container(content=ft.Row([ft.Icon(ft.icons.BOLT, color="#fbbf24", size=30), ft.Text(f"INGECTEC SAS", size=22, weight="bold", color="#fbbf24")], alignment=ft.MainAxisAlignment.CENTER), padding=5), 
            ft.Container(content=ft.Text(f"👤 Conectado: {sesion['usuario']} ({sesion['rol']})", size=12, color="#94a3b8"), alignment=ft.alignment.center_right), 
            contenedor_botones, 
            tabla, 
            f_cli, 
            ft.Container(content=ft.ElevatedButton("GENERAR COTIZACIÓN PROFESIONAL", icon=ft.icons.BOLT, bgcolor="#f59e0b", color="black", height=50, on_click=generar_pdf_web), alignment=ft.alignment.center, padding=ft.padding.only(top=10, bottom=20))
        )
        page.update()

        page.snack_bar = ft.SnackBar(
            ft.Text("🛡️ RECORDATORIO: Por favor, genere un Backup en 'SISTEMA' periódicamente para salvaguardar la información contra vulnerabilidades o ciberataques.", color="black", weight="bold"),
            bgcolor="#fbbf24",
            duration=10000
        )
        page.snack_bar.open = True
        page.update()

    mostrar_login()

ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=PORT, host="0.0.0.0", assets_dir="assets")