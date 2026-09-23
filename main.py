import flet as ft
import psycopg2
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

# --- CONEXIÓN SEGURA A POSTGRESQL MEDIANTE VARIABLE DE ENTORNO ---
DB_URL = os.environ.get("DATABASE_URL", "postgresql://ingectec_bd_user:HY7iwKhvaILCeuUKd7Pgknsh6Nsv4aUE@dpg-dapicrvf3r2c73ep15ag-a.oregon-postgres.render.com/ingectec_bd")

def conectar_db():
    try:
        return psycopg2.connect(DB_URL)
    except Exception as e:
        print("Error de conexión:", e)
        return None

# --- INICIALIZADOR AUTOMÁTICO DE TABLAS ---
def init_db():
    try:
        conn = conectar_db()
        if conn:
            c = conn.cursor()
            c.execute("CREATE TABLE IF NOT EXISTS usuarios (usuario TEXT PRIMARY KEY, password TEXT, rol TEXT, intentos INTEGER DEFAULT 0, bloqueado INTEGER DEFAULT 0)")
            c.execute("INSERT INTO usuarios (usuario, password, rol, intentos, bloqueado) VALUES ('OSCAR', '1234', 'ADMIN', 0, 0) ON CONFLICT (usuario) DO NOTHING")
            c.execute("INSERT INTO usuarios (usuario, password, rol, intentos, bloqueado) VALUES ('YEISON', '1234', 'ASESOR', 0, 0) ON CONFLICT (usuario) DO NOTHING")
            c.execute("INSERT INTO usuarios (usuario, password, rol, intentos, bloqueado) VALUES ('PAULO', '1234', 'ADMIN', 0, 0) ON CONFLICT (usuario) DO NOTHING")
            c.execute("INSERT INTO usuarios (usuario, password, rol, intentos, bloqueado) VALUES ('JOHN', '1234', 'ASESOR', 0, 0) ON CONFLICT (usuario) DO NOTHING")
            
            c.execute("CREATE TABLE IF NOT EXISTS n_cot (id SERIAL PRIMARY KEY, num INTEGER)")
            c.execute("INSERT INTO n_cot (id, num) VALUES (1, 100) ON CONFLICT (id) DO NOTHING")
            
            c.execute("CREATE TABLE IF NOT EXISTS cli (n TEXT PRIMARY KEY, i TEXT, dir TEXT, email TEXT, ciu TEXT, tel TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS inv (d TEXT PRIMARY KEY, p NUMERIC, stock NUMERIC, proveedor TEXT)")
            try: c.execute("ALTER TABLE inv ADD COLUMN IF NOT EXISTS proveedor TEXT")
            except: pass

            # --- NUEVA TABLA PARA PROVEEDORES ---
            c.execute("CREATE TABLE IF NOT EXISTS proveedores (nombre TEXT PRIMARY KEY, telefono TEXT)")
            c.execute("SELECT count(*) FROM proveedores")
            if c.fetchone()[0] == 0:
                provs_defecto = [("MECATRONIC", ""), ("RG REDES", ""), ("SMT INTERNACIONAL", ""), ("DON ELECTRICO", "")]
                for p_n, p_t in provs_defecto:
                    c.execute("INSERT INTO proveedores (nombre, telefono) VALUES (%s, %s) ON CONFLICT DO NOTHING", (p_n, p_t))

            c.execute("CREATE TABLE IF NOT EXISTS historial (nro TEXT PRIMARY KEY, cliente TEXT, fecha TEXT, archivo TEXT, total NUMERIC, origen TEXT, creador TEXT)")
            c.execute("""CREATE TABLE IF NOT EXISTS h_cab (
                nro TEXT PRIMARY KEY, cli TEXT, nit TEXT, atn TEXT, ref TEXT, ciu_origen TEXT, t_entrega TEXT, validez TEXT, pago TEXT, garantia TEXT, notas TEXT, modo TEXT, pct_a NUMERIC, pct_i NUMERIC, pct_u NUMERIC, pct_iva_u NUMERIC
            )""")
            
            columnas_extra = [
                ("atn", "TEXT"), ("ref", "TEXT"), ("ciu_origen", "TEXT"), ("t_entrega", "TEXT"), ("validez", "TEXT"), ("pago", "TEXT"),
                ("garantia", "TEXT"), ("notas", "TEXT"), ("modo", "TEXT"), ("pct_a", "NUMERIC"), ("pct_i", "NUMERIC"), ("pct_u", "NUMERIC"), ("pct_iva_u", "NUMERIC")
            ]
            for col, tipo in columnas_extra:
                try: c.execute(f"ALTER TABLE h_cab ADD COLUMN IF NOT EXISTS {col} {tipo}")
                except: pass

            c.execute('CREATE TABLE IF NOT EXISTS h_det (id SERIAL PRIMARY KEY, nro TEXT, "desc" TEXT, cant NUMERIC, und TEXT, unit NUMERIC, sub NUMERIC, imp TEXT, tipo TEXT)')
            
            conn.commit()
            conn.close()
    except Exception as e:
        print("Error inicializando BD:", e)

init_db()

def sanitizar_texto(texto):
    if not texto: return ""
    s = str(texto)
    reemplazos = {"•": "-", "·": "-", "–": "-", "—": "-", "“": '"', "”": '"', "‘": "'", "’": "'", "…": "...", "€": "EUR"}
    for orig, nuevo in reemplazos.items(): s = s.replace(orig, nuevo)
    return s.encode("latin-1", "replace").decode("latin-1")

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

def main(page: ft.Page):
    page.title = "INGECTEC V300 - PREMIUM"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#1e293b"
    page.padding = 15

    sesion = {"usuario": None, "rol": None}
    lista_items = []
    estado = {"nro_edicion": None, "creador_edicion": None}

    def cerrar_dialogo(dlg):
        dlg.open = False; page.update()

    def mostrar_alerta(titulo, mensaje):
        dialogo = ft.AlertDialog(title=ft.Text(titulo, weight="bold", color="#fbbf24"), content=ft.Text(str(mensaje)), actions=[ft.TextButton("OK", on_click=lambda e: cerrar_dialogo(dialogo))])
        page.dialog = dialogo; dialogo.open = True; page.update()

    input_usr = ft.TextField(label="Usuario (Ej. OSCAR, PAULO, YEISON)", width=300)
    input_pwd = ft.TextField(label="Contraseña", password=True, can_reveal_password=True, width=300)

    def procesar_login(e):
        u = input_usr.value.upper().strip()
        p = input_pwd.value.strip()
        db_login = conectar_db()
        if db_login:
            c = db_login.cursor()
            c.execute("SELECT password, rol, bloqueado, intentos FROM usuarios WHERE usuario=%s", (u,))
            user_row = c.fetchone()
            
            if user_row:
                db_pwd, rol, bloqueado, intentos = user_row
                
                if bloqueado == 1:
                    mostrar_alerta("Acceso Bloqueado 🔒", "Tu usuario ha sido bloqueado por superar los 3 intentos fallidos. Contacta al administrador del sistema para desbloquearlo.")
                    db_login.close()
                    return
                
                if db_pwd == p:
                    c.execute("UPDATE usuarios SET intentos=0, bloqueado=0 WHERE usuario=%s", (u,))
                    db_login.commit()
                    db_login.close()
                    sesion["usuario"] = u
                    sesion["rol"] = rol
                    iniciar_app_principal()
                else:
                    intentos += 1
                    if intentos >= 3:
                        c.execute("UPDATE usuarios SET intentos=%s, bloqueado=1 WHERE usuario=%s", (intentos, u))
                        db_login.commit()
                        mostrar_alerta("Acceso Bloqueado 🚫", "Has superado los 3 intentos de acceso fallidos. Tu usuario ha sido bloqueado por seguridad.")
                    else:
                        c.execute("UPDATE usuarios SET intentos=%s WHERE usuario=%s", (intentos, u))
                        db_login.commit()
                        page.snack_bar = ft.SnackBar(ft.Text(f"❌ Contraseña incorrecta. Intento {intentos} de 3."), bgcolor="#ef4444")
                        page.snack_bar.open = True
                        page.update()
                    db_login.close()
            else:
                db_login.close()
                page.snack_bar = ft.SnackBar(ft.Text("❌ El usuario no existe"), bgcolor="#ef4444")
                page.snack_bar.open = True
                page.update()

    pantalla_login = ft.Container(
        content=ft.Column(
            [
                ft.Icon(ft.icons.LOCK_PERSON, size=50, color="#fbbf24"),
                ft.Text("INGECTEC - Acceso Seguro", size=20, weight="bold", color="white"),
                input_usr,
                input_pwd,
                ft.ElevatedButton("INICIAR SESIÓN", bgcolor="#2563eb", color="white", width=300, height=45, on_click=procesar_login)
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=15
        ),
        alignment=ft.alignment.center,
        expand=True
    )

    def mostrar_login():
        sesion["usuario"] = None
        sesion["rol"] = None
        lista_items.clear()
        estado["nro_edicion"] = None
        estado["creador_edicion"] = None
        input_usr.value = ""
        input_pwd.value = ""
        
        page.scroll = None  
        page.controls.clear()
        page.add(pantalla_login)
        page.update()

    def iniciar_app_principal():
        page.scroll = ft.ScrollMode.AUTO
        page.controls.clear()
        
        input_cliente = ft.TextField(label="Buscar nombre de cliente...")
        input_nit = ft.TextField(label="NIT / C.C.")
        input_ciudad = ft.TextField(label="Ciudad (Origen Cotización)", value="Yumbo")
        input_atencion = ft.TextField(label="Atención a: (Ej. ING. MICHAEL MESIAS)")
        input_ref = ft.TextField(label="REFERENCIA")

        input_tiempo_entrega = ft.TextField(label="Tiempo de entrega", value="4 Días hábiles")
        input_validez = ft.TextField(label="Validez cotización", value="20 Días")
        input_pago = ft.TextField(label="Forma de pago", value="30 Días")
        input_garantia = ft.TextField(label="Garantía", value="6 meses en mano de obra")
        input_notas = ft.TextField(label="Notas adicionales (Coordina., etc.)", value="Toda la actividad será coordinada por el ingeniero Edward Álvarez y/o John Paniagua", multiline=True)
        
        input_pct_a = ft.TextField(label="Admin %", value="10")
        input_pct_i = ft.TextField(label="Imprev %", value="2")
        input_pct_u = ft.TextField(label="Util %", value="8")
        input_pct_iva_u = ft.TextField(label="IVA s/U %", value="19")
        lista_busqueda_cli = ft.ListView(height=150, visible=False, spacing=2)

        dropdown_modo_cot = ft.Dropdown(label="Tipo Cotización", options=[ft.dropdown.Option("AIU"), ft.dropdown.Option("IVA")], value="AIU")
        texto_config_aiu = ft.Text("⚙️ Config. AIU:", weight="bold", color="#fbbf24")
        container_texto_aiu = ft.Container(content=texto_config_aiu, col={"sm": 12, "md": 2, "lg": 2}, alignment=ft.alignment.center_left)
        cont_a = ft.Container(content=input_pct_a, col={"sm": 3, "md": 2, "lg": 2})
        cont_i = ft.Container(content=input_pct_i, col={"sm": 3, "md": 2, "lg": 2})
        cont_u = ft.Container(content=input_pct_u, col={"sm": 3, "md": 2, "lg": 2})
        cont_iva_u = ft.Container(content=input_pct_iva_u, col={"sm": 3, "md": 2, "lg": 2})

        def verificar_permiso_edicion():
            if estado.get("nro_edicion") and estado.get("creador_edicion"):
                if estado["creador_edicion"] != "SISTEMA" and estado["creador_edicion"] != sesion["usuario"]:
                    mostrar_alerta("Acceso Protegido 🛡️", f"Esta cotización es propiedad exclusiva de {estado['creador_edicion']}. Solo puedes visualizarla, no modificarla.")
                    return False
            return True

        def cambiar_modo_cot(e):
            es_aiu = dropdown_modo_cot.value == "AIU"
            container_texto_aiu.visible = es_aiu
            cont_a.visible = es_aiu
            cont_i.visible = es_aiu
            cont_u.visible = es_aiu
            cont_iva_u.visible = es_aiu
            page.update()
            
        dropdown_modo_cot.on_change = cambiar_modo_cot

        def buscar_cliente_realtime(e):
            texto = (input_cliente.value or "").upper().strip()
            lista_busqueda_cli.controls.clear()
            if len(texto) > 0:
                db = conectar_db()
                if db:
                    c = db.cursor()
                    c.execute("SELECT n, i, tel, dir, ciu, email FROM cli WHERE UPPER(n) LIKE %s ORDER BY n ASC LIMIT 10", ('%'+texto+'%',))
                    for row in c.fetchall():
                        def seleccionar(evt, data=row):
                            input_cliente.value = data[0] or ""
                            input_nit.value = data[1] or ""
                            lista_busqueda_cli.visible = False
                            page.update()
                        lista_busqueda_cli.controls.append(ft.ListTile(title=ft.Text(row[0], color="#fbbf24", size=13, weight="bold"), on_click=seleccionar))
                    db.close(); lista_busqueda_cli.visible = len(lista_busqueda_cli.controls) > 0
            else: lista_busqueda_cli.visible = False
            page.update()

        input_cliente.on_change = buscar_cliente_realtime

        db_num = conectar_db()
        nro_actual = "100"
        mes_actual_ui = datetime.now().strftime("%m")
        if db_num:
            c = db_num.cursor()
            c.execute("SELECT num FROM n_cot WHERE id=1")
            res_num = c.fetchone()
            if res_num: nro_actual = f"{mes_actual_ui}-{res_num[0]:03d}"
            db_num.close()

        header = ft.Container(content=ft.Text(f"⚡ INGECTEC SAS", size=22, weight="bold", color="#fbbf24"), alignment=ft.alignment.center, padding=5)

        def obtener_items_procesados(lista):
            disp = []
            curr_p = -1
            np, ns = 0, 0
            for i, it in enumerate(lista):
                if it.get('tipo', 'P') == 'P':
                    np += 1; ns = 0
                    curr_p = len(disp)
                    disp.append({
                        "raw_idx": i, "desc": it['desc'], "cant": float(it['cant']), "und": it.get('und', ''),
                        "precio": float(it['precio']), "total": float(it['total']), 
                        "impuesto": it.get('impuesto', ''), "tipo": 'P', "num": str(np), "has_subs": False
                    })
                else:
                    ns += 1
                    num_str = f"{np}.{ns}" if np > 0 else f"0.{ns}"
                    disp.append({
                        "raw_idx": i, "desc": it['desc'], "cant": float(it['cant']), "und": it.get('und', ''),
                        "precio": float(it['precio']), "total": float(it['total']), 
                        "impuesto": it.get('impuesto', ''), "tipo": 'S', "num": num_str
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
            items_calculados = obtener_items_procesados(lista_items)
            for item in items_calculados:
                if item['tipo'] == 'P':
                    if item.get('has_subs', False):
                        tot_str = f"${int(item['total']):,}" if item['total'] > 0 else ""
                        c_str = ""
                        imp_label = ""
                    else:
                        tot_str = f"${int(item['total']):,}" if item['total'] > 0 else ""
                        imp_label = f" ({item['impuesto']})" if item['total'] > 0 else ""
                        c_str = f"{item['cant']:g} {item['und']}" if item['cant'] > 0 else ""
                else:
                    tot_str = ""
                    imp_label = ""
                    c_str = f"{item['cant']:g} {item['und']}" if item['cant'] > 0 else ""

                def crear_evento_editar(indice_real):
                    def abrir_edicion_directa(e):
                        if not verificar_permiso_edicion(): return
                        val_c = str(lista_items[indice_real]['cant'])
                        val_p = str(int(float(lista_items[indice_real]['precio'])))
                        e_cant = ft.TextField(label="Nueva Cantidad", value=val_c)
                        e_precio = ft.TextField(label="Nuevo Precio", value=val_p)
                        
                        def guardar_cambio(ev):
                            try:
                                c = float(e_cant.value) if e_cant.value.strip() else 0.0
                                p = float(e_precio.value) if e_precio.value.strip() else 0.0
                                lista_items[indice_real]['cant'] = c
                                lista_items[indice_real]['precio'] = p
                                lista_items[indice_real]['total'] = c * p
                                actualizar_tabla_visual()
                                cerrar_dialogo(dlg_ind)
                            except: pass
                            
                        def eliminar_item(ev):
                            lista_items.pop(indice_real)
                            actualizar_tabla_visual()
                            cerrar_dialogo(dlg_ind)

                        dlg_ind = ft.AlertDialog(
                            title=ft.Text(f"✏️ Editar: {lista_items[indice_real]['desc']}", size=16, weight="bold"),
                            content=ft.Column([e_cant, e_precio], tight=True), 
                            actions=[
                                ft.ElevatedButton("Guardar", bgcolor="#10b981", color="white", on_click=guardar_cambio),
                                ft.ElevatedButton("Eliminar Ítem", bgcolor="#ef4444", color="white", on_click=eliminar_item),
                                ft.TextButton("Cancelar", on_click=lambda ev: cerrar_dialogo(dlg_ind))
                            ]
                        )
                        page.dialog = dlg_ind; dlg_ind.open = True; page.update()
                    return abrir_edicion_directa

                fila_visual = ft.Container(
                    content=ft.ResponsiveRow([
                        ft.Text(f"{item['num']}. {item['desc']}{imp_label}", col={"sm": 6}, color="white", size=12),
                        ft.Text(c_str, col={"sm": 3}, text_align="center", color="white"),
                        ft.Text(tot_str, col={"sm": 3}, text_align="right", color="#fbbf24"),
                    ]),
                    on_click=crear_evento_editar(item['raw_idx']),
                    padding=ft.padding.symmetric(vertical=5, horizontal=5),
                    border_radius=5, ink=True, tooltip="Clic para Editar"
                )
                columna_tabla_items.controls.append(fila_visual)
            page.update()

        def quitar_seleccionado(e):
            if not verificar_permiso_edicion(): return
            if lista_items: lista_items.pop(); actualizar_tabla_visual()

        def abrir_modal_item(e):
            if not verificar_permiso_edicion(): return
            resultados_inv = ft.ListView(expand=True, spacing=10, height=150)
            tipo_item = ft.RadioGroup(content=ft.Row([ft.Radio(value="P", label="Ítem Principal"), ft.Radio(value="S", label="Sub-ítem")]), value="P")
            modo_actual_cotizacion = dropdown_modo_cot.value
            opciones_imp_dinamicas = [ft.dropdown.Option(modo_actual_cotizacion), ft.dropdown.Option("EXENTO")]
            pct_defecto = "19" if modo_actual_cotizacion == "IVA" else "10"

            input_desc = ft.TextField(label="Descripción", read_only=False)
            input_cant = ft.TextField(label="Cantidad", value="1", col={"sm": 3})
            input_und_custom = ft.TextField(label="Iniciales (Ej. KGS)", visible=False, col={"sm": 3})
            input_precio = ft.TextField(label="Precio Unit", value="0", col={"sm": 5})
            
            def cambiar_und(evt):
                if input_und.value == "✍️ ESCRIBIR...":
                    input_cant.col = {"sm": 2}; input_und.col = {"sm": 3}; input_und_custom.visible = True; input_precio.col = {"sm": 4}; input_und_custom.focus()
                else:
                    input_cant.col = {"sm": 3}; input_und.col = {"sm": 4}; input_und_custom.visible = False; input_precio.col = {"sm": 5}
                page.update()

            def cambiar_impuesto(evt):
                if input_imp_tipo.value == "IVA": input_imp_pct.value = "19"
                elif input_imp_tipo.value == "AIU": input_imp_pct.value = "10"
                elif input_imp_tipo.value == "EXENTO": input_imp_pct.value = "0"
                page.update()

            lista_unidades = ["ML", "UNID", "MTS", "GLB", "ROLLO", "DIA", "PAQ", "✍️ ESCRIBIR..."]
            input_und = ft.Dropdown(label="Und", options=[ft.dropdown.Option(u) for u in lista_unidades], value="UNID", col={"sm": 4}, on_change=cambiar_und)
            input_imp_tipo = ft.Dropdown(label="Impuesto", options=opciones_imp_dinamicas, value=modo_actual_cotizacion, col={"sm": 6}, on_change=cambiar_impuesto)
            input_imp_pct = ft.TextField(label="% Imp", value=pct_defecto, col={"sm": 6})

            def buscar_inv_bd(evt):
                resultados_inv.controls.clear()
                db = conectar_db()
                if db:
                    c = db.cursor()
                    txt = (buscador_inv.value or "").upper()
                    try: c.execute("SELECT d, p, proveedor FROM inv WHERE UPPER(d) LIKE %s ORDER BY d ASC LIMIT 30", ('%'+txt+'%',))
                    except: c.execute("SELECT d, p, '' FROM inv WHERE UPPER(d) LIKE %s ORDER BY d ASC LIMIT 30", ('%'+txt+'%',))

                    for row in c.fetchall():
                        d = row[0]
                        p = row[1] if row[1] else 0
                        prov = row[2] if len(row)>2 and row[2] else ""
                        
                        def sel(evt, desc=d, precio=p): 
                            input_desc.value = desc; input_precio.value = str(int(float(precio)))
                            if "TUBO" in desc.upper() or "CABLE" in desc.upper(): input_und.value = "ML"
                            elif "INSTALACION" in desc.upper(): input_und.value = "GLB"
                            else: input_und.value = "UNID"
                            input_und_custom.visible = False; input_cant.col = {"sm": 3}; input_und.col = {"sm": 4}; input_precio.col = {"sm": 5}; page.update()
                        
                        subtit = f"${int(float(p)):,}"
                        if prov: subtit += f"  (Proveedor: {prov})"
                        resultados_inv.controls.append(ft.ListTile(title=ft.Text(d, color="#fbbf24", size=14), subtitle=ft.Text(subtit, color="#94a3b8"), on_click=sel))
                    db.close()
                page.update()

            def guardar_item(evt):
                if not input_desc.value: return
                try:
                    c = float(input_cant.value) if input_cant.value.strip() else 0.0
                    p = float(input_precio.value) if input_precio.value.strip() else 0.0
                    imp = "EXENTO" if input_imp_tipo.value == "EXENTO" else f"{input_imp_tipo.value} {input_imp_pct.value}%"
                    und_final = str(input_und_custom.value).upper().strip() if input_und.value == "✍️ ESCRIBIR..." else input_und.value
                    if not und_final: und_final = "UNID"
                    
                    lista_items.append({"desc": input_desc.value, "cant": c, "precio": p, "total": c*p, "impuesto": imp, "und": und_final, "tipo": tipo_item.value})
                    actualizar_tabla_visual()
                    
                    input_desc.value = ""; input_cant.value = "1"; input_precio.value = "0"; input_und.value = "UNID"; input_und_custom.value = ""; input_und_custom.visible = False
                    input_cant.col = {"sm": 3}; input_und.col = {"sm": 4}; input_precio.col = {"sm": 5}
                    input_imp_tipo.value = modo_actual_cotizacion
                    input_imp_pct.value = pct_defecto
                    buscador_inv.value = ""; buscar_inv_bd(None)
                    page.snack_bar = ft.SnackBar(ft.Text("✅ Ítem agregado a la lista"), bgcolor="#10b981"); page.snack_bar.open = True; page.update()
                except: pass

            buscador_inv = ft.TextField(label="Buscar en bodega...", on_change=buscar_inv_bd)
            dlg = ft.AlertDialog(
                title=ft.Text("➕ Añadir a Propuesta"), 
                content=ft.Container(width=750, content=ft.Column([tipo_item, buscador_inv, resultados_inv, input_desc, ft.ResponsiveRow([input_cant, input_und, input_und_custom, input_precio]), ft.ResponsiveRow([input_imp_tipo, input_imp_pct])], tight=True)), 
                actions=[ft.ElevatedButton("Guardar", bgcolor="#10b981", color="white", on_click=guardar_item), ft.TextButton("Cerrar", on_click=lambda e: cerrar_dialogo(dlg))]
            )
            page.dialog = dlg; dlg.open = True; buscar_inv_bd(None)

        def abrir_modal_bodega(e):
            # --- PESTAÑA 1: BÚSQUEDA ---
            resultados_bod = ft.ListView(height=180)
            e_desc = ft.TextField(label="Nombre del Producto")
            e_precio = ft.TextField(label="Precio del Producto")
            
            # --- PESTAÑA 2: MASIVA ---
            e_masivo = ft.TextField(multiline=True, min_lines=6, max_lines=10, label="Pega aquí desde Excel (Columna 1: Nombre | Columna 2: Precio)")
            
            # --- PESTAÑA 3: COMPARADOR CON AUTOCOMPLETADO Y PROVEEDORES DE BD ---
            comp_item = ft.TextField(label="Buscar o escribir Ítem a cotizar...")
            lista_busqueda_comp = ft.ListView(height=100, visible=False, spacing=2)
            
            comp_prov1 = ft.Dropdown(label="Proveedor 1", col={"sm": 6})
            comp_pre1 = ft.TextField(label="Precio Prov 1", col={"sm": 6})
            comp_prov2 = ft.Dropdown(label="Proveedor 2", col={"sm": 6})
            comp_pre2 = ft.TextField(label="Precio Prov 2", col={"sm": 6})
            comp_prov3 = ft.Dropdown(label="Proveedor 3", col={"sm": 6})
            comp_pre3 = ft.TextField(label="Precio Prov 3", col={"sm": 6})

            # --- PESTAÑA 4: MIS PROVEEDORES ---
            e_prov_nom = ft.TextField(label="Nombre del Proveedor*", col={"sm": 7})
            e_prov_tel = ft.TextField(label="Teléfono", col={"sm": 5})
            lista_provs = ft.ListView(height=200)

            def cargar_proveedores():
                lista_provs.controls.clear()
                opciones_dropdown = []
                db = conectar_db()
                if db:
                    c = db.cursor()
                    c.execute("SELECT nombre, telefono FROM proveedores ORDER BY nombre ASC")
                    for row in c.fetchall():
                        n, t = row
                        opciones_dropdown.append(ft.dropdown.Option(n))
                        
                        def editar_p(evt, nombre=n, tel=t):
                            e_prov_nom.value = nombre
                            e_prov_tel.value = tel
                            page.update()
                            
                        def eliminar_p(evt, nombre=n):
                            db_d = conectar_db()
                            c_d = db_d.cursor()
                            c_d.execute("DELETE FROM proveedores WHERE nombre=%s", (nombre,))
                            db_d.commit(); db_d.close()
                            cargar_proveedores()
                            page.snack_bar = ft.SnackBar(ft.Text(f"🗑️ Proveedor {nombre} eliminado"), bgcolor="#ef4444"); page.snack_bar.open = True; page.update()

                        lista_provs.controls.append(ft.ListTile(
                            title=ft.Text(n, color="#fbbf24", weight="bold"),
                            subtitle=ft.Text(f"Teléfono: {t}" if t else "Sin teléfono"),
                            on_click=editar_p,
                            trailing=ft.IconButton(ft.icons.DELETE, icon_color="#ef4444", on_click=eliminar_p)
                        ))
                    db.close()
                
                comp_prov1.options = opciones_dropdown
                comp_prov2.options = opciones_dropdown
                comp_prov3.options = opciones_dropdown
                page.update()

            def guardar_nuevo_proveedor(evt):
                if not e_prov_nom.value: return
                db = conectar_db()
                if db:
                    c = db.cursor()
                    c.execute("INSERT INTO proveedores (nombre, telefono) VALUES (%s,%s) ON CONFLICT(nombre) DO UPDATE SET telefono=EXCLUDED.telefono", 
                             (e_prov_nom.value.upper().strip(), e_prov_tel.value.strip()))
                    db.commit(); db.close()
                    e_prov_nom.value = ""; e_prov_tel.value = ""
                    cargar_proveedores()
                    page.snack_bar = ft.SnackBar(ft.Text("✅ Proveedor guardado"), bgcolor="#10b981"); page.snack_bar.open = True; page.update()

            def buscar_bodega(evt):
                resultados_bod.controls.clear()
                db = conectar_db()
                if db:
                    c = db.cursor()
                    txt = (e_desc.value or "").upper()
                    c.execute("SELECT d, p FROM inv WHERE UPPER(d) LIKE %s LIMIT 20", ('%'+txt+'%',))
                    for row in c.fetchall():
                        d, p = row[0], row[1]
                        def sel(evt, desc=d, prec=p): e_desc.value = desc; e_precio.value = str(int(float(prec))); page.update()
                        def eliminar(evt, desc=d):
                            db_d = conectar_db()
                            c_d = db_d.cursor()
                            c_d.execute("DELETE FROM inv WHERE d=%s", (desc,))
                            db_d.commit(); db_d.close(); buscar_bodega(None)
                            page.snack_bar = ft.SnackBar(ft.Text(f"🗑️ Producto eliminado"), bgcolor="#ef4444"); page.snack_bar.open = True; page.update()
                        resultados_bod.controls.append(ft.ListTile(title=ft.Text(d, size=13, color="#fbbf24", weight="bold"), subtitle=ft.Text(f"${int(float(p)):,}"), on_click=sel, trailing=ft.IconButton(ft.icons.DELETE, icon_color="#ef4444", on_click=eliminar)))
                    db.close()
                page.update()

            def guardar_bodega(evt):
                if not e_desc.value: return
                try:
                    db = conectar_db()
                    c = db.cursor()
                    c.execute("INSERT INTO inv (d, p, stock, proveedor) VALUES (%s,%s,0,'') ON CONFLICT(d) DO UPDATE SET p=EXCLUDED.p", (e_desc.value.upper(), float(e_precio.value or 0)))
                    db.commit(); db.close()
                    e_desc.value = ""; e_precio.value = ""; buscar_bodega(None)
                    page.snack_bar = ft.SnackBar(ft.Text("✅ Precio guardado correctamente"), bgcolor="#2563eb"); page.snack_bar.open = True; page.update()
                except Exception as ex: mostrar_alerta("Error", str(ex))

            def procesar_masivo(evt):
                if not e_masivo.value.strip(): return
                lineas = e_masivo.value.strip().split('\n')
                db = conectar_db()
                if not db: return
                c = db.cursor()
                agregados = 0
                for linea in lineas:
                    partes = linea.split('\t') 
                    if len(partes) >= 1:
                        desc = partes[0].strip().upper()
                        if not desc: continue
                        prec_str = "0"
                        if len(partes) >= 2: prec_str = partes[1].replace("$", "").replace(".", "").replace(",", "").replace(" ", "").strip()
                        try: prec = float(prec_str)
                        except: prec = 0.0
                        c.execute("INSERT INTO inv (d, p, stock, proveedor) VALUES (%s,%s,0,'') ON CONFLICT(d) DO UPDATE SET p=EXCLUDED.p", (desc, prec))
                        agregados += 1
                db.commit(); db.close()
                e_masivo.value = ""; buscar_bodega(None)
                page.snack_bar = ft.SnackBar(ft.Text(f"✅ ¡Éxito! Se procesaron {agregados} productos."), bgcolor="#10b981"); page.snack_bar.open = True; page.update()

            # --- FUNCION AUTOCOMPLETAR EN EL COMPARADOR ---
            def buscar_item_comp(evt):
                txt = (comp_item.value or "").upper().strip()
                lista_busqueda_comp.controls.clear()
                if len(txt) > 0:
                    db = conectar_db()
                    if db:
                        c = db.cursor()
                        c.execute("SELECT d FROM inv WHERE UPPER(d) LIKE %s LIMIT 10", ('%'+txt+'%',))
                        for row in c.fetchall():
                            def seleccionar(e, desc=row[0]):
                                comp_item.value = desc
                                lista_busqueda_comp.visible = False
                                page.update()
                            lista_busqueda_comp.controls.append(ft.ListTile(title=ft.Text(row[0], size=13, color="#fbbf24"), on_click=seleccionar))
                        db.close()
                        lista_busqueda_comp.visible = len(lista_busqueda_comp.controls) > 0
                else:
                    lista_busqueda_comp.visible = False
                page.update()

            comp_item.on_change = buscar_item_comp

            def ejecutar_comparador(evt):
                item_desc = comp_item.value.strip().upper()
                if not item_desc:
                    return mostrar_alerta("Aviso", "Debes ingresar el nombre del ítem a cotizar.")
                
                ofertas = []
                if comp_prov1.value and comp_pre1.value:
                    try: ofertas.append((comp_prov1.value, float(comp_pre1.value)))
                    except: pass
                if comp_prov2.value and comp_pre2.value:
                    try: ofertas.append((comp_prov2.value, float(comp_pre2.value)))
                    except: pass
                if comp_prov3.value and comp_pre3.value:
                    try: ofertas.append((comp_prov3.value, float(comp_pre3.value)))
                    except: pass
                
                if not ofertas:
                    return mostrar_alerta("Aviso", "Debes ingresar al menos un proveedor con su precio.")

                ganador = min(ofertas, key=lambda x: x[1])
                prov_ganador, precio_ganador = ganador

                try:
                    db = conectar_db()
                    c = db.cursor()
                    c.execute("""INSERT INTO inv (d, p, stock, proveedor) VALUES (%s, %s, 0, %s) 
                                 ON CONFLICT(d) DO UPDATE SET p=EXCLUDED.p, proveedor=EXCLUDED.proveedor""", 
                              (item_desc, precio_ganador, prov_ganador))
                    db.commit(); db.close()
                    
                    comp_item.value = ""; comp_prov1.value = None; comp_pre1.value = ""; comp_prov2.value = None; comp_pre2.value = ""; comp_prov3.value = None; comp_pre3.value = ""
                    buscar_bodega(None)
                    
                    page.snack_bar = ft.SnackBar(ft.Text(f"🏆 GANADOR: {prov_ganador} con ${int(precio_ganador):,}. Bodega actualizada."), bgcolor="#8b5cf6")
                    page.snack_bar.open = True
                    page.update()
                except Exception as ex:
                    mostrar_alerta("Error", str(ex))

            e_desc.on_change = buscar_bodega
            
            pestañas_bodega = ft.Tabs(
                selected_index=0,
                animation_duration=300,
                tabs=[
                    ft.Tab(
                        text="Búsqueda",
                        content=ft.Column([
                            ft.Container(height=10), e_desc, e_precio, ft.ElevatedButton("Guardar Producto", bgcolor="#2563eb", color="white", on_click=guardar_bodega),
                            ft.Divider(), ft.Text("Productos Registrados:", weight="bold"), resultados_bod
                        ], tight=True)
                    ),
                    ft.Tab(
                        text="Carga Masiva",
                        content=ft.Column([
                            ft.Container(height=10), ft.Text("Pega desde Excel (Nombre y Precio)", size=12, color="white54"),
                            e_masivo, ft.ElevatedButton("📥 IMPORTAR DESDE EXCEL", bgcolor="#10b981", color="white", on_click=procesar_masivo)
                        ], tight=True)
                    ),
                    ft.Tab(
                        text="⚖️ Comparador",
                        content=ft.Column([
                            ft.Container(height=10), ft.Text("Busca el ítem, selecciona tus proveedores y anota el precio.", size=12, color="white54"),
                            comp_item, lista_busqueda_comp,
                            ft.ResponsiveRow([comp_prov1, comp_pre1]),
                            ft.ResponsiveRow([comp_prov2, comp_pre2]),
                            ft.ResponsiveRow([comp_prov3, comp_pre3]),
                            ft.ElevatedButton("⚖️ ANALIZAR Y ELEGIR GANADOR", bgcolor="#8b5cf6", color="white", on_click=ejecutar_comparador)
                        ], tight=True, scroll=ft.ScrollMode.AUTO)
                    ),
                    ft.Tab(
                        text="🏢 Proveedores",
                        content=ft.Column([
                            ft.Container(height=10), ft.Text("Registra tus proveedores (El nombre aparecerá en el comparador).", size=12, color="white54"),
                            ft.ResponsiveRow([e_prov_nom, e_prov_tel]),
                            ft.ElevatedButton("Guardar Proveedor", bgcolor="#10b981", color="white", on_click=guardar_nuevo_proveedor),
                            ft.Divider(), ft.Text("Lista de Proveedores:", weight="bold"), lista_provs
                        ], tight=True, scroll=ft.ScrollMode.AUTO)
                    )
                ],
                expand=1
            )

            dlg = ft.AlertDialog(
                title=ft.Text("📦 Gestión de Bodega / Catálogo"), 
                content=ft.Container(width=750, height=500, content=pestañas_bodega), 
                actions=[ft.TextButton("Cerrar", on_click=lambda e: cerrar_dialogo(dlg))]
            )
            page.dialog = dlg; dlg.open = True
            buscar_bodega(None)
            cargar_proveedores()

        def abrir_modal_clientes(e):
            resultados_cli = ft.ListView(expand=True, spacing=10, height=200)
            
            e_cli_nom = ft.TextField(label="Nombre Cliente*", col={"sm": 12})
            e_cli_nit = ft.TextField(label="NIT / C.C.*", col={"sm": 6})
            e_cli_tel = ft.TextField(label="Teléfono", col={"sm": 6})
            e_cli_dir = ft.TextField(label="Dirección", col={"sm": 6})
            e_cli_ciu = ft.TextField(label="Ciudad (Ej. Yumbo)", col={"sm": 6})
            e_cli_email = ft.TextField(label="Email", col={"sm": 12})

            e_masivo_cli = ft.TextField(
                multiline=True, 
                min_lines=8, 
                max_lines=12, 
                label="Pega aquí desde Excel (Orden: 1.Nombre | 2.NIT | 3.Teléfono | 4.Dirección | 5.Ciudad | 6.Email)"
            )

            def cargar_clientes_lista():
                resultados_cli.controls.clear()
                db = conectar_db()
                if db:
                    try:
                        c = db.cursor()
                        c.execute("SELECT n, i, ciu, tel FROM cli ORDER BY n ASC")
                        for row in c.fetchall():
                            n, i, ciu, tel = row
                            
                            def editar(evt, nombre=n):
                                db_i = conectar_db()
                                c_i = db_i.cursor()
                                c_i.execute("SELECT n, i, dir, email, ciu, tel FROM cli WHERE n=%s", (nombre,))
                                c_data = c_i.fetchone()
                                db_i.close()
                                if c_data:
                                    e_cli_nom.value, e_cli_nit.value, e_cli_dir.value, e_cli_email.value, e_cli_ciu.value, e_cli_tel.value = c_data
                                    page.update()

                            def eliminar(evt, nombre=n):
                                db_d = conectar_db()
                                c_d = db_d.cursor()
                                c_d.execute("DELETE FROM cli WHERE n=%s", (nombre,))
                                db_d.commit(); db_d.close()
                                limpiar_form_cliente(None)
                                cargar_clientes_lista()
                                page.snack_bar = ft.SnackBar(ft.Text(f"🗑️ Cliente {nombre} eliminado"), bgcolor="#ef4444"); page.snack_bar.open = True; page.update()

                            resultados_cli.controls.append(
                                ft.ListTile(
                                    title=ft.Text(n, color="#fbbf24", weight="bold"),
                                    subtitle=ft.Text(f"NIT: {i} | Ciudad: {ciu or ''} | Tel: {tel or ''}"),
                                    trailing=ft.IconButton(ft.icons.DELETE, icon_color="#ef4444", on_click=eliminar),
                                    on_click=editar
                                )
                            )
                    except: pass
                    db.close()
                page.update()

            def guardar_cliente_crud(evt):
                if not e_cli_nom.value: return
                db = conectar_db()
                if db:
                    try:
                        c = db.cursor()
                        c.execute("INSERT INTO cli (n, i, dir, email, ciu, tel) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT(n) DO UPDATE SET i=EXCLUDED.i, dir=EXCLUDED.dir, email=EXCLUDED.email, ciu=EXCLUDED.ciu, tel=EXCLUDED.tel", 
                                   (e_cli_nom.value.upper(), e_cli_nit.value, e_cli_dir.value, e_cli_email.value, e_cli_ciu.value, e_cli_tel.value))
                        db.commit()
                    except: pass
                    db.close()
                    limpiar_form_cliente(None)
                    cargar_clientes_lista()
                    page.snack_bar = ft.SnackBar(ft.Text("✅ Cliente guardado/actualizado"), bgcolor="#10b981"); page.snack_bar.open = True; page.update()

            def limpiar_form_cliente(evt):
                e_cli_nom.value = ""; e_cli_nit.value = ""; e_cli_dir.value = ""; e_cli_email.value = ""; e_cli_ciu.value = ""; e_cli_tel.value = ""
                page.update()

            def procesar_masivo_cli(evt):
                if not e_masivo_cli.value.strip(): return
                lineas = e_masivo_cli.value.strip().split('\n')
                
                db = conectar_db()
                if not db: return
                c = db.cursor()
                
                agregados = 0
                for linea in lineas:
                    partes = linea.split('\t') 
                    if len(partes) >= 1:
                        nom = sanitizar_texto(partes[0].strip().upper())
                        if not nom: continue
                        
                        nit = sanitizar_texto(partes[1].strip()) if len(partes) > 1 else ""
                        tel = sanitizar_texto(partes[2].strip()) if len(partes) > 2 else ""
                        dir_c = sanitizar_texto(partes[3].strip()) if len(partes) > 3 else ""
                        ciu = sanitizar_texto(partes[4].strip()) if len(partes) > 4 else ""
                        email = sanitizar_texto(partes[5].strip()) if len(partes) > 5 else ""
                        
                        c.execute("""INSERT INTO cli (n, i, tel, dir, ciu, email) 
                                     VALUES (%s,%s,%s,%s,%s,%s) 
                                     ON CONFLICT(n) DO UPDATE 
                                     SET i=EXCLUDED.i, tel=EXCLUDED.tel, dir=EXCLUDED.dir, ciu=EXCLUDED.ciu, email=EXCLUDED.email""", 
                                  (nom, nit, tel, dir_c, ciu, email))
                        agregados += 1
                        
                db.commit()
                db.close()
                e_masivo_cli.value = ""
                cargar_clientes_lista()
                page.snack_bar = ft.SnackBar(ft.Text(f"✅ ¡Éxito! Se procesaron {agregados} clientes."), bgcolor="#10b981")
                page.snack_bar.open = True
                page.update()

            pestañas_clientes = ft.Tabs(
                selected_index=0,
                animation_duration=300,
                tabs=[
                    ft.Tab(
                        text="Búsqueda y Edición",
                        content=ft.Column([
                            ft.Container(height=10),
                            ft.Text("Para crear o modificar, llena los datos y presiona Guardar:", size=12, color="white54"),
                            ft.ResponsiveRow([e_cli_nom, e_cli_nit, e_cli_tel, e_cli_dir, e_cli_ciu, e_cli_email]),
                            ft.Row([ft.ElevatedButton("Guardar Cliente", bgcolor="#10b981", color="white", on_click=guardar_cliente_crud), ft.TextButton("Limpiar Campos", on_click=limpiar_form_cliente)]),
                            ft.Divider(color="white24"),
                            ft.Text("Listado de Clientes Registrados:", weight="bold"),
                            resultados_cli
                        ], tight=True, scroll=ft.ScrollMode.AUTO)
                    ),
                    ft.Tab(
                        text="Importación Masiva",
                        content=ft.Column([
                            ft.Container(height=10),
                            ft.Text("Copia las filas de tus clientes desde Excel y pégalas abajo.", size=12, color="white54"),
                            ft.Text("Orden de columnas: 1.Nombre | 2.NIT | 3.Teléfono | 4.Dirección | 5.Ciudad | 6.Email (Los datos faltantes quedarán vacíos).", size=11, color="#fbbf24", weight="bold"),
                            e_masivo_cli,
                            ft.ElevatedButton("📥 IMPORTAR CLIENTES DESDE EXCEL", bgcolor="#10b981", color="white", on_click=procesar_masivo_cli)
                        ], tight=True)
                    )
                ],
                expand=1
            )

            dlg = ft.AlertDialog(
                title=ft.Text("👥 Gestión de Clientes"), 
                content=ft.Container(width=750, height=500, content=pestañas_clientes), 
                actions=[ft.TextButton("Cerrar", on_click=lambda e: cerrar_dialogo(dlg))]
            )
            page.dialog = dlg; dlg.open = True; cargar_clientes_lista()

        def abrir_modal_usuarios(e):
            if sesion["rol"] != "ADMIN":
                return mostrar_alerta("Acceso Denegado", "Solo el Administrador puede gestionar los usuarios del sistema.")
            
            resultados_usr = ft.ListView(expand=True, spacing=10, height=200)
            e_usr_nom = ft.TextField(label="Nombre de Usuario*", col={"sm": 4})
            e_usr_pwd = ft.TextField(label="Contraseña*", password=True, can_reveal_password=True, col={"sm": 4})
            e_usr_rol = ft.Dropdown(label="Rol", options=[ft.dropdown.Option("ADMIN"), ft.dropdown.Option("ASESOR")], value="ASESOR", col={"sm": 4})

            def cargar_usuarios():
                resultados_usr.controls.clear()
                db = conectar_db()
                if db:
                    c = db.cursor()
                    c.execute("SELECT usuario, rol, bloqueado FROM usuarios ORDER BY usuario ASC")
                    for row in c.fetchall():
                        u, r, b = row[0], row[1], row[2]
                        estado_txt = " (Bloqueado 🔒)" if b == 1 else ""
                        def editar(evt, user_name=u, user_role=r):
                            e_usr_nom.value = user_name; e_usr_rol.value = user_role; e_usr_pwd.value = ""; page.update()
                        def eliminar(evt, user_name=u):
                            if user_name == sesion["usuario"]: return mostrar_alerta("Aviso", "No puedes eliminar tu propio usuario.")
                            db_d = conectar_db(); c_d = db_d.cursor(); c_d.execute("DELETE FROM usuarios WHERE usuario=%s", (user_name,)); db_d.commit(); db_d.close(); cargar_usuarios(); page.snack_bar = ft.SnackBar(ft.Text(f"🗑️ Usuario eliminado"), bgcolor="#ef4444"); page.snack_bar.open = True; page.update()
                        def desbloquear(evt, user_name=u):
                            db_u = conectar_db(); c_u = db_u.cursor(); c_u.execute("UPDATE usuarios SET intentos=0, bloqueado=0 WHERE usuario=%s", (user_name,)); db_u.commit(); db_u.close(); cargar_usuarios(); page.snack_bar = ft.SnackBar(ft.Text(f"✅ Usuario desbloqueado"), bgcolor="#10b981"); page.snack_bar.open = True; page.update()

                        botones_accion = [ft.IconButton(ft.icons.DELETE, icon_color="#ef4444", tooltip="Eliminar Usuario", on_click=eliminar)]
                        if b == 1: botones_accion.insert(0, ft.IconButton(ft.icons.LOCK_OPEN, icon_color="#10b981", tooltip="Desbloquear Usuario", on_click=desbloquear))
                        resultados_usr.controls.append(ft.ListTile(title=ft.Text(f"{u}{estado_txt}", color="#ef4444" if b==1 else "#fbbf24", weight="bold"), subtitle=ft.Text(f"Rol asignado: {r}"), trailing=ft.Row(botones_accion, tight=True), on_click=editar))
                    db.close()
                page.update()

            def guardar_usuario(evt):
                if not e_usr_nom.value or not e_usr_pwd.value: return mostrar_alerta("Aviso", "Falta el nombre o la contraseña.")
                db = conectar_db()
                if db:
                    c = db.cursor()
                    usr_nom_limpio = e_usr_nom.value.upper().strip()
                    c.execute("SELECT count(*) FROM usuarios WHERE usuario=%s", (usr_nom_limpio,))
                    if c.fetchone()[0] > 0: c.execute("UPDATE usuarios SET password=%s, rol=%s, intentos=0, bloqueado=0 WHERE usuario=%s", (e_usr_pwd.value.strip(), e_usr_rol.value, usr_nom_limpio))
                    else: c.execute("INSERT INTO usuarios (usuario, password, rol, intentos, bloqueado) VALUES (%s,%s,%s,0,0)", (usr_nom_limpio, e_usr_pwd.value.strip(), e_usr_rol.value))
                    db.commit(); db.close()
                    e_usr_nom.value = ""; e_usr_pwd.value = ""; e_usr_rol.value = "ASESOR"; cargar_usuarios()
                    page.snack_bar = ft.SnackBar(ft.Text("✅ Usuario guardado"), bgcolor="#8b5cf6"); page.snack_bar.open = True; page.update()

            dlg = ft.AlertDialog(title=ft.Text("🔐 Gestión de Usuarios"), content=ft.Container(width=700, content=ft.Column([ft.Text("Crear o Modificar Usuario:", size=12, color="white54"), ft.ResponsiveRow([e_usr_nom, e_usr_pwd, e_usr_rol]), ft.ElevatedButton("Guardar Usuario", bgcolor="#8b5cf6", color="white", on_click=guardar_usuario), ft.Divider(color="white24"), ft.Text("Usuarios Registrados:", weight="bold"), resultados_usr], tight=True)), actions=[ft.TextButton("Cerrar", on_click=lambda e: cerrar_dialogo(dlg))])
            page.dialog = dlg; dlg.open = True; cargar_usuarios()

        def abrir_modal_historial(e):
            resultados_hist = ft.ListView(expand=True, spacing=10, height=300)
            buscador_hist = ft.TextField(label="🔍 Buscar por nombre de cliente...", width=400)

            def cargar_historial_lista(evt=None):
                resultados_hist.controls.clear()
                txt_busqueda = (buscador_hist.value or "").upper().strip()
                db = conectar_db()
                if db:
                    c = db.cursor()
                    if txt_busqueda: c.execute("SELECT nro, cliente, fecha, total, creador FROM historial WHERE UPPER(cliente) LIKE %s ORDER BY nro DESC LIMIT 50", ('%'+txt_busqueda+'%',))
                    else: c.execute("SELECT nro, cliente, fecha, total, creador FROM historial ORDER BY nro DESC LIMIT 30")

                    for row in c.fetchall():
                        nro, cli, fec, tot, creador = row[0], row[1], row[2], row[3], row[4]
                        
                        def cargar_cotizacion(evt, numero=nro, creador_doc=creador):
                            db_h = conectar_db()
                            c_h = db_h.cursor()
                            c_h.execute("""SELECT cli, nit, atn, ref, ciu_origen, t_entrega, validez, pago, garantia, notas, modo, pct_a, pct_i, pct_u, pct_iva_u FROM h_cab WHERE nro=%s""", (numero,))
                            cab = c_h.fetchone()
                            
                            if cab:
                                input_cliente.value = cab[0] or ""; input_nit.value = cab[1] or ""; input_atencion.value = cab[2] or ""; input_ref.value = cab[3] or ""; input_ciudad.value = cab[4] or "Yumbo"; input_tiempo_entrega.value = cab[5] or "4 Días hábiles"; input_validez.value = cab[6] or "20 Días"; input_pago.value = cab[7] or "30 Días"; input_garantia.value = cab[8] or "6 meses en mano de obra"; input_notas.value = cab[9] or ""
                                dropdown_modo_cot.value = cab[10] or "AIU"; input_pct_a.value = str(cab[11]) if cab[11] is not None else "10"; input_pct_i.value = str(cab[12]) if cab[12] is not None else "2"; input_pct_u.value = str(cab[13]) if cab[13] is not None else "8"; input_pct_iva_u.value = str(cab[14]) if cab[14] is not None else "19"
                                es_aiu = dropdown_modo_cot.value == "AIU"; container_texto_aiu.visible = es_aiu; cont_a.visible = es_aiu; cont_i.visible = es_aiu; cont_u.visible = es_aiu; cont_iva_u.visible = es_aiu

                            lista_items.clear()
                            c_h.execute('SELECT "desc", cant, und, unit, sub, imp, tipo FROM h_det WHERE nro=%s', (numero,))
                            for d in c_h.fetchall():
                                desc_str = d[0] if d[0] else ""
                                try: cant_f = float(d[1])
                                except: cant_f = 0.0
                                und_str = str(d[2]) if d[2] else "UNID"
                                try: unit_f = float(d[3])
                                except: unit_f = 0.0
                                try: sub_f = float(d[4])
                                except: sub_f = cant_f * unit_f
                                impuesto_str = str(d[5]) if d[5] else "EXENTO"
                                if "AIU" in und_str or "IVA" in und_str or "EXENTO" in und_str: temp = impuesto_str; impuesto_str = und_str; und_str = temp if temp not in ["EXENTO", ""] else "UNID"
                                tipo_str = str(d[6]) if d[6] else "P"
                                lista_items.append({"desc": desc_str, "cant": cant_f, "und": und_str, "precio": unit_f, "total": sub_f, "impuesto": impuesto_str, "tipo": tipo_str})
                            db_h.close()
                            
                            estado["nro_edicion"] = numero; estado["creador_edicion"] = creador_doc
                            actualizar_tabla_visual(); cerrar_dialogo(dlg)
                            
                            if creador_doc and creador_doc != "SISTEMA" and creador_doc != sesion["usuario"]:
                                page.snack_bar = ft.SnackBar(ft.Text(f"👁️ Visualizando cotización de {creador_doc}. Modo Solo Lectura."), bgcolor="#3b82f6"); page.snack_bar.open = True; page.update()
                            else: mostrar_alerta("Cargado", f"Cotización N° {numero} cargada exactamente con todos sus parámetros originales.")
                        
                        resultados_hist.controls.append(ft.ListTile(title=ft.Text(f"N° {nro} - {cli} (Por: {creador})", color="#fbbf24", weight="bold"), subtitle=ft.Text(f"Fecha/Hora: {fec} | Total: ${int(float(tot)):,}"), on_click=cargar_cotizacion))
                db.close(); page.update()

            buscador_hist.on_change = cargar_historial_lista
            dlg = ft.AlertDialog(title=ft.Text("🔍 Historial de Cotizaciones"), content=ft.Container(width=700, content=ft.Column([buscador_hist, resultados_hist], tight=True)), actions=[ft.TextButton("Cerrar", on_click=lambda e: cerrar_dialogo(dlg))])
            page.dialog = dlg; dlg.open = True; cargar_historial_lista()

        def abrir_modal_sistema(e):
            if sesion["rol"] != "ADMIN": return mostrar_alerta("Acceso Denegado", "Solo el Administrador tiene acceso a la configuración del sistema.")
            def hacer_backup(evt): mostrar_alerta("Backup en la Nube ☁️", "La plataforma ahora está respaldada de forma automática y blindada en PostgreSQL. Ya no es necesario descargar archivos locales de seguridad.")
            def confirmar_reseteo(evt):
                input_clave_maestra = ft.TextField(label="Contraseña Maestra", password=True, can_reveal_password=True, width=300)
                def ejecutar_reseteo(ev):
                    if input_clave_maestra.value.strip() == "7705178":
                        db = conectar_db()
                        if db:
                            c = db.cursor(); c.execute("DELETE FROM cli"); c.execute("DELETE FROM inv"); c.execute("DELETE FROM historial"); c.execute("DELETE FROM h_cab"); c.execute("DELETE FROM h_det"); c.execute("UPDATE n_cot SET num = 100 WHERE id=1"); db.commit(); db.close()
                        cerrar_dialogo(dlg_conf); cerrar_dialogo(dlg_sis)
                        page.snack_bar = ft.SnackBar(ft.Text("✅ SISTEMA RESTAURADO DE FÁBRICA CORRECTAMENTE"), bgcolor="#10b981"); page.snack_bar.open = True; page.update()
                    else:
                        page.snack_bar = ft.SnackBar(ft.Text("❌ Contraseña Maestra Incorrecta"), bgcolor="#ef4444"); page.snack_bar.open = True; page.update()
                dlg_conf = ft.AlertDialog(title=ft.Text("⚠️ ADVERTENCIA EXTREMA", color="#ef4444", weight="bold"), content=ft.Column([ft.Text("¿Estás 100% seguro? Esto borrará TODOS los clientes, TODOS los productos y TODO el historial."), ft.Text("Digita la Contraseña Maestra para confirmar:", weight="bold", color="#fbbf24"), input_clave_maestra], tight=True), actions=[ft.ElevatedButton("SÍ, BORRAR TODO", bgcolor="#ef4444", color="white", on_click=ejecutar_reseteo), ft.TextButton("CANCELAR", on_click=lambda e: cerrar_dialogo(dlg_conf))])
                page.dialog = dlg_conf; dlg_conf.open = True; page.update()
            dlg_sis = ft.AlertDialog(title=ft.Text("⚙️ Configuración del Sistema (ADMIN)"), content=ft.Container(width=400, content=ft.Column([ft.Text("Opciones avanzadas de la base de datos:"), ft.ElevatedButton("📥 1. DESCARGAR BACKUP", bgcolor="#2563eb", color="white", width=350, on_click=hacer_backup), ft.Container(height=20), ft.Text("ZONA DE PELIGRO:", color="#ef4444", weight="bold"), ft.ElevatedButton("⚠️ 2. RESTAURAR DE FÁBRICA", bgcolor="#ef4444", color="white", width=350, on_click=confirmar_reseteo)], tight=True)), actions=[ft.TextButton("Cerrar", on_click=lambda e: cerrar_dialogo(dlg_sis))])
            page.dialog = dlg_sis; dlg_sis.open = True; page.update()

        def limpiar_todo(e):
            lista_items.clear(); estado["nro_edicion"] = None; estado["creador_edicion"] = None; actualizar_tabla_visual()
            input_cliente.value = ""; input_nit.value = ""; input_atencion.value = ""; input_ref.value = ""; input_ciudad.value = "Yumbo"; input_tiempo_entrega.value = "4 Días hábiles"; input_validez.value = "20 Días"; input_pago.value = "30 Días"; input_garantia.value = "6 meses en mano de obra"; input_notas.value = "Toda la actividad será coordinada por el ingeniero Edward Álvarez y/o John Paniagua"; dropdown_modo_cot.value = "AIU"; input_pct_a.value = "10"; input_pct_i.value = "2"; input_pct_u.value = "8"; input_pct_iva_u.value = "19"; lista_busqueda_cli.visible = False; cambiar_modo_cot(None); page.update()

        def generar_pdf_web(e):
            if not verificar_permiso_edicion(): return
            try:
                if not lista_items or not input_cliente.value: 
                    return mostrar_alerta("Aviso", "Faltan ítems o nombre del cliente.")
                
                c_nom = sanitizar_texto(input_cliente.value or "").upper().strip()
                c_nit = sanitizar_texto(input_nit.value or "").strip()
                c_ciu_origen = sanitizar_texto(input_ciudad.value or "Yumbo").strip()
                c_atn = sanitizar_texto(input_atencion.value or "").strip()
                c_ref = sanitizar_texto(input_ref.value or "").strip()
                c_t_entrega = sanitizar_texto(input_tiempo_entrega.value or "").strip()
                c_validez = sanitizar_texto(input_validez.value or "").strip()
                c_pago = sanitizar_texto(input_pago.value or "").strip()
                c_garantia = sanitizar_texto(input_garantia.value or "").strip()
                c_notas = sanitizar_texto(input_notas.value or "").strip()
                c_modo = dropdown_modo_cot.value or "AIU"

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
                    c = db.cursor()
                    c.execute("SELECT dir, email, ciu, tel FROM cli WHERE n=%s", (c_nom,))
                    cli_data = c.fetchone()
                    if cli_data: c_dir = sanitizar_texto(cli_data[0] or ""); c_email = sanitizar_texto(cli_data[1] or ""); c_ciu_cli = sanitizar_texto(cli_data[2] or ""); c_tel = sanitizar_texto(cli_data[3] or "")
                except: pass

                nro_doc = estado["nro_edicion"]
                mes_actual = datetime.now().strftime("%m")
                
                c_up = db.cursor()
                if not nro_doc:
                    c_up.execute("UPDATE n_cot SET num = num + 1 WHERE id=1 RETURNING num")
                    num_fetch = c_up.fetchone()
                    num_puro = num_fetch[0] if num_fetch else 100
                    nro_doc = f"{mes_actual}-{num_puro:03d}"
                else:
                    c_up.execute("DELETE FROM h_cab WHERE nro=%s", (nro_doc,))
                    c_up.execute("DELETE FROM h_det WHERE nro=%s", (nro_doc,))
                    c_up.execute("DELETE FROM historial WHERE nro=%s", (nro_doc,))
                    
                c_up.execute("INSERT INTO cli (n, i) VALUES (%s, %s) ON CONFLICT(n) DO NOTHING", (c_nom, c_nit))
                
                c_up.execute("""INSERT INTO h_cab (nro, cli, nit, atn, ref, ciu_origen, t_entrega, validez, pago, garantia, notas, modo, pct_a, pct_i, pct_u, pct_iva_u) 
                                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", 
                             (nro_doc, c_nom, c_nit, c_atn, c_ref, c_ciu_origen, c_t_entrega, c_validez, c_pago, c_garantia, c_notas, c_modo, pct_a, pct_i, pct_u, pct_iva_u))
                
                subtotal_global = 0
                iva_bases = {}
                
                for item in lista_items:
                    cant_n = float(item['cant']); unit_n = float(item['precio']); tot_item_n = float(item['total'])
                    imp_str = item.get('impuesto', 'EXENTO'); und_str = item.get('und', 'UNID')
                    tipo_val = item.get('tipo', 'P')
                    
                    c_up.execute('INSERT INTO h_det (nro, "desc", cant, und, unit, sub, imp, tipo) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)', 
                               (nro_doc, item['desc'], cant_n, und_str, unit_n, tot_item_n, imp_str, tipo_val))
                    subtotal_global += tot_item_n
                    
                    if "IVA" in imp_str.upper():
                        try: pct = float(re.findall(r"[\d.]+", imp_str)[0])
                        except: pct = 19
                        iva_bases[pct] = iva_bases.get(pct, 0) + tot_item_n

                val_a = subtotal_global * (pct_a / 100)
                val_i = subtotal_global * (pct_i / 100)
                val_u = subtotal_global * (pct_u / 100)
                total_aiu_sum = val_a + val_i + val_u
                val_iva_u_val = val_u * (pct_iva_u / 100)

                if c_modo == "AIU": total_final_cotizacion = subtotal_global + total_aiu_sum + val_iva_u_val
                else: total_final_cotizacion = subtotal_global
                
                for pct_iva, base_amt in iva_bases.items(): total_final_cotizacion += base_amt * (pct_iva / 100)

                nombre_limpio_cli = re.sub(r'[^\w\s-]', '', c_nom).strip()
                nombre_archivo = f"{nombre_limpio_cli}-{nro_doc}.pdf"

                fecha_hora_actual = datetime.now().strftime("%Y-%m-%d %H:%M")
                c_up.execute("INSERT INTO historial (nro, cliente, fecha, archivo, total, origen, creador) VALUES (%s,%s,%s,%s,%s,%s,%s)", 
                           (nro_doc, c_nom, fecha_hora_actual, nombre_archivo, total_final_cotizacion, "WEB", sesion["usuario"]))
                db.commit(); db.close()

                nombres_completos = {"OSCAR": "OSCAR MERA", "YEISON": "YEISON FABIAN RESTREPO", "JOHN": "JOHN JAIRO CARDONA", "JHON": "JOHN JAIRO CARDONA", "PAULO": "PAULO ANDRES LEAL GARCIA"}
                numeros_whatsapp = {"OSCAR": "573175046404", "YEISON": "573002986963", "JOHN": "573225532559", "JHON": "573225532559", "PAULO": "573175046404"}
                
                asesor_actual = sesion["usuario"].upper()
                numero_asesor = numeros_whatsapp.get(asesor_actual, "573175046404")

                qr = qrcode.QRCode(box_size=10, border=2)
                qr.add_data(f"https://wa.me/{numero_asesor}"); qr.make(fit=True)
                qr.make_image(fill_color="black", back_color="white").save("assets/qr_temp.png")

                p = PDF()
                p.asesor_nombre = nombres_completos.get(asesor_actual, asesor_actual) 
                p.set_margins(10, 10, 10); p.set_auto_page_break(auto=True, margin=30); p.add_page()
                p.set_font('helvetica', 'B', 11)
                meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
                hoy = datetime.now()
                p.cell(0, 5, sanitizar_texto(f"{c_ciu_origen}, {hoy.day} de {meses[hoy.month-1]} de {hoy.year}"), border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                p.ln(4)

                y_start_cli = p.get_y()
                linea_direccion = c_dir
                if c_ciu_cli: linea_direccion = f"{c_dir} - {c_ciu_cli}".strip(" -")
                lines_client = 1 
                if c_atn: lines_client += 1
                if c_nom: lines_client += 1
                if c_nit: lines_client += 1
                if linea_direccion: lines_client += 1
                if c_tel: lines_client += 1
                if c_email: lines_client += 1
                
                p.set_fill_color(240, 240, 240)
                p.rounded_rect(8, y_start_cli - 2, 105, (lines_client * 5) + 4, r=3, style='F') 
                p.rounded_rect(118, y_start_cli - 2, 84, 14, r=3, style='F') 
                
                p.set_xy(10, y_start_cli)
                p.cell(0, 5, "Señores:", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                if c_atn: p.set_font('helvetica', 'B', 11); p.set_text_color(31, 73, 125); p.cell(110, 5, c_atn, border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                p.set_text_color(0, 0, 0); p.set_font('helvetica', 'B', 11); p.cell(110, 5, c_nom, border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                p.set_font('helvetica', '', 11)
                if c_nit: p.cell(110, 5, f"NIT / CC: {c_nit}", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                if linea_direccion: p.cell(110, 5, linea_direccion, border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                if c_tel: p.cell(110, 5, f"Tel: {c_tel}", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                if c_email: p.cell(110, 5, f"Email: {c_email}", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                
                y_end_cli = p.get_y()
                p.set_xy(120, y_start_cli + 2); p.set_font('helvetica', 'B', 12); p.set_text_color(31, 73, 125); p.cell(80, 5, f"COTIZACIÓN ING {nro_doc}", border=0, align='C'); p.set_text_color(0, 0, 0) 

                p.set_y(max(y_end_cli, y_start_cli + 10) + 5)
                if c_ref:
                    y_start_ref = p.get_y()
                    num_lines = (len("REFERENCIA: " + c_ref) // 85) + 1  
                    p.set_fill_color(240, 240, 240); p.rounded_rect(8, y_start_ref - 2, 194, (num_lines * 5) + 4, r=3, style='F')
                    p.set_font('helvetica', 'B', 11); p.set_text_color(31, 73, 125); p.write(5, "REFERENCIA: "); p.set_font('helvetica', '', 11); p.set_text_color(0, 0, 0); p.write(5, f"{c_ref}\n"); p.ln(5)

                p.set_fill_color(194, 229, 194); p.set_text_color(0, 0, 0); p.set_font("helvetica", '', 8) 
                p.cell(10, 6, "ITEM", 1, fill=True, align='C'); p.cell(78, 6, "DESCRIPCION", 1, fill=True, align='C'); p.cell(12, 6, "CANT", 1, fill=True, align='C'); p.cell(25, 6, "UND", 1, fill=True, align='C'); p.cell(20, 6, "V. UNIT", 1, fill=True, align='C'); p.cell(20, 6, "IMPUESTO", 1, fill=True, align='C'); p.cellPara implementar la función de autocompletado en el campo "Nombre del ítem a cotizar" en el modal de "Gestión de Bodega / Catálogo"[cite: 1], se debe reemplazar el campo de texto estándar por un componente de búsqueda dinámica (tipo *autocomplete* o *searchable dropdown*). Esto permitirá que el sistema filtre en tiempo real los ítems existentes en la base de datos a medida que se escribe "cinta", desplegando una lista para seleccionar el ítem exacto sin tener que digitar el nombre completo[cite: 1].

Para resolver la limitación en la gestión de proveedores, dado que la pestaña "Comparador Proveedores" actualmente solo muestra espacios fijos ("Proveedor 1", "Proveedor 2", "Proveedor 3")[cite: 1], se requieren las siguientes modificaciones estructurales en la aplicación:

*   **Creación rápida de proveedores:** Añadir un botón (como un ícono de "+") directamente al lado de los campos de selección de proveedores. Al presionarlo, debe desplegarse un pequeño formulario o ventana emergente que permita registrar un nuevo proveedor capturando únicamente los campos clave: **Nombre** y **Teléfono**.
*   **Filas dinámicas para comparar:** En lugar de tener una cantidad fija de campos para los proveedores y sus precios[cite: 1], se debe implementar un botón de "Añadir otro proveedor a la comparación". Esto permitirá generar nuevas filas dinámicamente si se requiere cotizar con más empresas, sin estar limitados a la cantidad predeterminada en el diseño actual.
*   **Búsqueda de proveedores existentes:** Los campos donde actualmente se escribe el nombre del proveedor (ej. Mecatronic, RG Redes)[cite: 1] también deben funcionar con autocompletado, conectándose a la lista de proveedores previamente guardados en el sistema.