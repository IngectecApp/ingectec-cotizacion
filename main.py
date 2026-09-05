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
        
        # INYECTOR DE SEGURIDAD PARA BLOQUEOS
        try: db_setup.execute("ALTER TABLE usuarios ADD COLUMN intentos INTEGER DEFAULT 0")
        except: pass
        try: db_setup.execute("ALTER TABLE usuarios ADD COLUMN bloqueado INTEGER DEFAULT 0")
        except: pass

        db_setup.execute("INSERT OR IGNORE INTO usuarios (usuario, password, rol, intentos, bloqueado) VALUES ('OSCAR', '1234', 'ADMIN', 0, 0)")
        db_setup.execute("INSERT OR IGNORE INTO usuarios (usuario, password, rol, intentos, bloqueado) VALUES ('YEISON', '1234', 'ADMIN', 0, 0)")
        db_setup.execute("INSERT OR IGNORE INTO usuarios (usuario, password, rol, intentos, bloqueado) VALUES ('PAULO', '1234', 'ADMIN', 0, 0)")
        
        db_setup.execute("CREATE TABLE IF NOT EXISTS n_cot (id INTEGER PRIMARY KEY, num INTEGER)")
        db_setup.execute("INSERT OR IGNORE INTO n_cot (id, num) VALUES (1, 100)")
        
        try: db_setup.execute("ALTER TABLE historial ADD COLUMN creador TEXT DEFAULT 'SISTEMA'")
        except: pass
        try: db_setup.execute("ALTER TABLE historial ADD COLUMN origen TEXT DEFAULT 'WEB'")
        except: pass

        try:
            db_setup.execute("CREATE TABLE IF NOT EXISTS cli (n TEXT PRIMARY KEY, i TEXT, dir TEXT, email TEXT, ciu TEXT, tel TEXT)")
        except: pass

        cursor_r = db_setup.cursor()
        items_perdidos = [("BREAKER 2X40", 101861), ("TUBO EMT DE 1\" (INCLUYE ASCESORIOS DE INSTALACION)", 35547)]
        for desc, precio in items_perdidos:
            cursor_r.execute("SELECT count(*) FROM inv WHERE d=?", (desc,))
            if cursor_r.fetchone()[0] == 0:
                cursor_r.execute("INSERT INTO inv (d, p, stock) VALUES (?,?,0)", (desc, precio))
        
        db_setup.commit(); db_setup.close()

    input_usr = ft.TextField(label="Usuario (Ej. OSCAR, PAULO, YEISON)", width=300)
    input_pwd = ft.TextField(label="Contraseña", password=True, can_reveal_password=True, width=300)

    # ==========================================
    # LÓGICA DE INGRESO CON SEGURIDAD 3 INTENTOS
    # ==========================================
    def procesar_login(e):
        u = input_usr.value.upper().strip()
        p = input_pwd.value.strip()
        db_login = conectar_db()
        if db_login:
            user_row = db_login.execute("SELECT password, rol, bloqueado, intentos FROM usuarios WHERE usuario=?", (u,)).fetchone()
            
            if user_row:
                db_pwd, rol, bloqueado, intentos = user_row
                
                # Si el usuario ya está bloqueado, no lo dejamos pasar
                if bloqueado == 1:
                    mostrar_alerta("Acceso Bloqueado 🔒", "Tu usuario ha sido bloqueado por superar los 3 intentos fallidos. Contacta al administrador del sistema para desbloquearlo.")
                    db_login.close()
                    return
                
                # Verificamos la contraseña
                if db_pwd == p:
                    # Todo bien: se reinician los intentos a cero
                    db_login.execute("UPDATE usuarios SET intentos=0, bloqueado=0 WHERE usuario=?", (u,))
                    db_login.commit()
                    db_login.close()
                    sesion["usuario"] = u
                    sesion["rol"] = rol
                    iniciar_app_principal()
                else:
                    # Contraseña mala: sumamos un intento
                    intentos += 1
                    if intentos >= 3:
                        db_login.execute("UPDATE usuarios SET intentos=?, bloqueado=1 WHERE usuario=?", (intentos, u))
                        db_login.commit()
                        mostrar_alerta("Acceso Bloqueado 🚫", "Has superado los 3 intentos de acceso fallidos. Tu usuario ha sido bloqueado por seguridad.")
                    else:
                        db_login.execute("UPDATE usuarios SET intentos=? WHERE usuario=?", (intentos, u))
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
        input_usr.value = ""
        input_pwd.value = ""
        
        page.scroll = None  
        page.controls.clear()
        page.add(pantalla_login)
        page.update()

    # ==========================================
    # INTERFAZ PRINCIPAL AISLADA
    # ==========================================
    def iniciar_app_principal():
        page.scroll = ft.ScrollMode.AUTO
        page.controls.clear()
        
        input_cliente = ft.TextField(label="Buscar nombre de cliente...")
        input_nit = ft.TextField(label="NIT / C.C.")
        input_ciudad = ft.TextField(label="Ciudad (Origen Cotización)", value="Yumbo")
        input_atencion = ft.TextField(label="Atención a: (Ej. ING. MICHAEL MESIAS)")
        input_pago = ft.TextField(label="Forma Pago", value="30 DIAS")
        input_tiempo = ft.TextField(label="Tiempo Oferta", value="15 DIAS")
        input_ref = ft.TextField(label="REFERENCIA")
        
        input_pct_a = ft.TextField(label="Admin %", value="10")
        input_pct_i = ft.TextField(label="Imprev %", value="2")
        input_pct_u = ft.TextField(label="Util %", value="8")
        input_pct_iva_u = ft.TextField(label="IVA s/Util %", value="19")
        lista_busqueda_cli = ft.ListView(height=150, visible=False, spacing=2)

        def buscar_cliente_realtime(e):
            texto = (input_cliente.value or "").upper().strip()
            lista_busqueda_cli.controls.clear()
            if len(texto) > 0:
                db = conectar_db()
                if db:
                    for row in db.execute("SELECT n, i FROM cli WHERE UPPER(n) LIKE ? ORDER BY n ASC LIMIT 10", ('%'+texto+'%',)):
                        def seleccionar(evt, nombre=row[0], nit=(row[1] if row[1] else "")):
                            input_cliente.value = nombre; input_nit.value = nit; lista_busqueda_cli.visible = False; page.update()
                        lista_busqueda_cli.controls.append(ft.ListTile(title=ft.Text(row[0], color="#fbbf24", size=13, weight="bold"), on_click=seleccionar))
                    db.close(); lista_busqueda_cli.visible = len(lista_busqueda_cli.controls) > 0
            else: lista_busqueda_cli.visible = False
            page.update()

        input_cliente.on_change = buscar_cliente_realtime

        db_num = conectar_db()
        nro_actual = "100"
        mes_actual_ui = datetime.now().strftime("%m")
        if db_num:
            res_num = db_num.execute("SELECT num FROM n_cot WHERE id=1").fetchone()
            if res_num: nro_actual = f"{mes_actual_ui}-{res_num[0]:03d}"
            db_num.close()

        header = ft.Container(content=ft.Text(f"⚡ INGECTEC SAS", size=22, weight="bold", color="#fbbf24"), alignment=ft.alignment.center, padding=5)

        columna_tabla_items = ft.Column()
        def actualizar_tabla_visual():
            columna_tabla_items.controls.clear()
            for idx, item in enumerate(lista_items):
                total_seguro = int(float(item['total']))
                columna_tabla_items.controls.append(
                    ft.ResponsiveRow([
                        ft.Text(f"{idx+1}. {item['desc']} ({item.get('impuesto', '')})", col={"sm": 6}, color="white", size=12),
                        ft.Text(f"{item['cant']} {item.get('und', '')}", col={"sm": 3}, text_align="center", color="white"),
                        ft.Text(f"${total_seguro:,}", col={"sm": 3}, text_align="right", color="#fbbf24"),
                    ])
                )
            page.update()

        def quitar_seleccionado(e):
            if lista_items: lista_items.pop(); actualizar_tabla_visual()

        def abrir_modal_item(e):
            resultados_inv = ft.ListView(expand=True, spacing=10, height=150)
            input_desc = ft.TextField(label="Producto Seleccionado", read_only=True)
            input_cant = ft.TextField(label="Cantidad", value="1", col={"sm": 3})
            input_und_custom = ft.TextField(label="Iniciales (Ej. KGS)", visible=False, col={"sm": 3})
            input_precio = ft.TextField(label="Precio Unit", col={"sm": 5})
            
            def cambiar_und(evt):
                if input_und.value == "✍️ ESCRIBIR...":
                    input_cant.col = {"sm": 2}; input_und.col = {"sm": 3}; input_und_custom.visible = True; input_precio.col = {"sm": 4}; input_und_custom.focus()
                else:
                    input_cant.col = {"sm": 3}; input_und.col = {"sm": 4}; input_und_custom.visible = False; input_precio.col = {"sm": 5}
                page.update()

            def cambiar_impuesto(evt):
                if input_imp_tipo.value == "IVA":
                    input_imp_pct.value = "19"
                elif input_imp_tipo.value == "AIU":
                    input_imp_pct.value = "10"
                elif input_imp_tipo.value == "EXENTO":
                    input_imp_pct.value = "0"
                page.update()

            lista_unidades = ["ML", "UNID", "MTS", "GLB", "ROLLO", "DIA", "PAQ", "✍️ ESCRIBIR..."]
            input_und = ft.Dropdown(label="Und", options=[ft.dropdown.Option(u) for u in lista_unidades], value="UNID", col={"sm": 4}, on_change=cambiar_und)
            
            input_imp_tipo = ft.Dropdown(
                label="Impuesto", 
                options=[ft.dropdown.Option("AIU"), ft.dropdown.Option("IVA"), ft.dropdown.Option("EXENTO")], 
                value="AIU", 
                col={"sm": 6}, 
                on_change=cambiar_impuesto
            )
            input_imp_pct = ft.TextField(label="% Imp", value="10", col={"sm": 6})

            def buscar_inv_bd(evt):
                resultados_inv.controls.clear()
                db = conectar_db()
                if db:
                    txt = (buscador_inv.value or "").upper()
                    for row in db.execute("SELECT d, p FROM inv WHERE UPPER(d) LIKE ? ORDER BY d ASC LIMIT 30", ('%'+txt+'%',)):
                        d, p = row[0], (row[1] if row[1] else 0)
                        def sel(evt, desc=d, precio=p): 
                            input_desc.value = desc; input_precio.value = str(int(float(precio)))
                            if "TUBO" in desc.upper() or "CABLE" in desc.upper(): input_und.value = "ML"
                            elif "INSTALACION" in desc.upper(): input_und.value = "GLB"
                            else: input_und.value = "UNID"
                            input_und_custom.visible = False; input_cant.col = {"sm": 3}; input_und.col = {"sm": 4}; input_precio.col = {"sm": 5}; page.update()
                        resultados_inv.controls.append(ft.ListTile(title=ft.Text(d, color="#fbbf24", size=14), subtitle=ft.Text(f"${int(float(p)):,}"), on_click=sel))
                    db.close()
                page.update()

            def guardar_item(evt):
                if not input_desc.value or not input_precio.value: return
                try:
                    d, c, p = input_desc.value, float(input_cant.value), float(input_precio.value)
                    imp = "EXENTO" if input_imp_tipo.value == "EXENTO" else f"{input_imp_tipo.value} {input_imp_pct.value}%"
                    und_final = str(input_und_custom.value).upper().strip() if input_und.value == "✍️ ESCRIBIR..." else input_und.value
                    if not und_final: und_final = "UNID"
                    
                    lista_items.append({"desc": d, "cant": c, "precio": p, "total": c*p, "impuesto": imp, "und": und_final})
                    actualizar_tabla_visual()
                    
                    input_desc.value = ""; input_cant.value = "1"; input_precio.value = ""; input_und.value = "UNID"; input_und_custom.value = ""; input_und_custom.visible = False
                    input_cant.col = {"sm": 3}; input_und.col = {"sm": 4}; input_precio.col = {"sm": 5}
                    input_imp_tipo.value = "AIU"; input_imp_pct.value = "10"
                    
                    buscador_inv.value = ""; buscar_inv_bd(None)
                    page.snack_bar = ft.SnackBar(ft.Text("✅ Ítem agregado"), bgcolor="#10b981"); page.snack_bar.open = True; page.update()
                except: pass

            buscador_inv = ft.TextField(label="Buscar en bodega...", on_change=buscar_inv_bd)
            dlg = ft.AlertDialog(
                title=ft.Text("➕ Añadir a Propuesta"), 
                content=ft.Container(width=750, content=ft.Column([buscador_inv, resultados_inv, input_desc, ft.ResponsiveRow([input_cant, input_und, input_und_custom, input_precio]), ft.ResponsiveRow([input_imp_tipo, input_imp_pct])], tight=True)), 
                actions=[ft.ElevatedButton("Guardar", bgcolor="#10b981", color="white", on_click=guardar_item), ft.TextButton("Cerrar", on_click=lambda e: cerrar_dialogo(dlg))]
            )
            page.dialog = dlg; dlg.open = True; buscar_inv_bd(None)

        def abrir_modal_bodega(e):
            resultados_bod = ft.ListView(height=200)
            e_desc = ft.TextField(label="Nombre del Producto")
            e_precio = ft.TextField(label="Precio del Producto")
            
            def buscar_bodega(evt):
                resultados_bod.controls.clear()
                db = conectar_db()
                if db:
                    txt = (e_desc.value or "").upper()
                    for row in db.execute("SELECT d, p FROM inv WHERE UPPER(d) LIKE ? LIMIT 20", ('%'+txt+'%',)):
                        d, p = row[0], row[1]
                        def sel(evt, desc=d, prec=p): e_desc.value = desc; e_precio.value = str(int(float(prec))); page.update()
                        
                        def eliminar(evt, desc=d):
                            db_d = conectar_db()
                            db_d.execute("DELETE FROM inv WHERE d=?", (desc,))
                            db_d.commit(); db_d.close()
                            buscar_bodega(None)
                            page.snack_bar = ft.SnackBar(ft.Text(f"🗑️ Producto eliminado"), bgcolor="#ef4444"); page.snack_bar.open = True; page.update()

                        resultados_bod.controls.append(ft.ListTile(
                            title=ft.Text(d, size=13, color="#fbbf24", weight="bold"), 
                            subtitle=ft.Text(f"${int(float(p)):,}"), 
                            on_click=sel,
                            trailing=ft.IconButton(ft.icons.DELETE, icon_color="#ef4444", on_click=eliminar)
                        ))
                    db.close()
                page.update()

            def guardar_bodega(evt):
                if not e_desc.value: return
                try:
                    db = conectar_db()
                    db.execute("INSERT INTO inv (d, p, stock) VALUES (?,?,0) ON CONFLICT(d) DO UPDATE SET p=excluded.p", (e_desc.value.upper(), float(e_precio.value or 0)))
                    db.commit(); db.close()
                    e_desc.value = ""; e_precio.value = ""; buscar_bodega(None)
                    page.snack_bar = ft.SnackBar(ft.Text("✅ Precio guardado correctamente"), bgcolor="#2563eb"); page.snack_bar.open = True; page.update()
                except Exception as ex: mostrar_alerta("Error", str(ex))

            e_desc.on_change = buscar_bodega
            dlg = ft.AlertDialog(
                title=ft.Text("📦 Gestión de Bodega / Catálogo"), 
                content=ft.Container(width=600, content=ft.Column([
                    ft.Text("Crear o Actualizar Producto:", size=12, color="white54"),
                    e_desc, e_precio,
                    ft.ElevatedButton("Guardar Producto", bgcolor="#2563eb", color="white", on_click=guardar_bodega),
                    ft.Divider(),
                    ft.Text("Productos Registrados:", weight="bold"),
                    resultados_bod
                ], tight=True)), 
                actions=[ft.TextButton("Cerrar", on_click=lambda e: cerrar_dialogo(dlg))]
            )
            page.dialog = dlg; dlg.open = True; buscar_bodega(None)

        def abrir_modal_clientes(e):
            resultados_cli = ft.ListView(expand=True, spacing=10, height=200)
            
            e_cli_nom = ft.TextField(label="Nombre Cliente*", col={"sm": 12})
            e_cli_nit = ft.TextField(label="NIT / C.C.*", col={"sm": 6})
            e_cli_tel = ft.TextField(label="Teléfono", col={"sm": 6})
            e_cli_dir = ft.TextField(label="Dirección", col={"sm": 6})
            e_cli_ciu = ft.TextField(label="Ciudad (Ej. Yumbo)", col={"sm": 6})
            e_cli_email = ft.TextField(label="Email", col={"sm": 12})

            def cargar_clientes_lista():
                resultados_cli.controls.clear()
                db = conectar_db()
                if db:
                    for row in db.execute("SELECT n, i, ciu, tel FROM cli ORDER BY n ASC"):
                        n, i, ciu, tel = row
                        
                        def editar(evt, nombre=n):
                            db_i = conectar_db()
                            c_data = db_i.execute("SELECT n, i, dir, email, ciu, tel FROM cli WHERE n=?", (nombre,)).fetchone()
                            db_i.close()
                            if c_data:
                                e_cli_nom.value, e_cli_nit.value, e_cli_dir.value, e_cli_email.value, e_cli_ciu.value, e_cli_tel.value = c_data
                                page.update()

                        def eliminar(evt, nombre=n):
                            db_d = conectar_db()
                            db_d.execute("DELETE FROM cli WHERE n=?", (nombre,))
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
                    db.close()
                page.update()

            def guardar_cliente_crud(evt):
                if not e_cli_nom.value: return
                db = conectar_db()
                if db:
                    db.execute("INSERT OR REPLACE INTO cli (n, i, dir, email, ciu, tel) VALUES (?,?,?,?,?,?)", 
                               (e_cli_nom.value.upper(), e_cli_nit.value, e_cli_dir.value, e_cli_email.value, e_cli_ciu.value, e_cli_tel.value))
                    db.commit(); db.close()
                    limpiar_form_cliente(None)
                    cargar_clientes_lista()
                    page.snack_bar = ft.SnackBar(ft.Text("✅ Cliente guardado/actualizado"), bgcolor="#10b981"); page.snack_bar.open = True; page.update()

            def limpiar_form_cliente(evt):
                e_cli_nom.value = ""; e_cli_nit.value = ""; e_cli_dir.value = ""; e_cli_email.value = ""; e_cli_ciu.value = ""; e_cli_tel.value = ""
                page.update()

            dlg = ft.AlertDialog(
                title=ft.Text("👥 Gestión de Clientes"), 
                content=ft.Container(width=750, content=ft.Column([
                    ft.Text("Para crear o modificar, llena los datos y presiona Guardar:", size=12, color="white54"),
                    ft.ResponsiveRow([e_cli_nom, e_cli_nit, e_cli_tel, e_cli_dir, e_cli_ciu, e_cli_email]),
                    ft.Row([ft.ElevatedButton("Guardar Cliente", bgcolor="#10b981", color="white", on_click=guardar_cliente_crud), ft.TextButton("Limpiar Campos", on_click=limpiar_form_cliente)]),
                    ft.Divider(color="white24"),
                    ft.Text("Listado de Clientes Registrados:", weight="bold"),
                    resultados_cli
                ], tight=True, scroll=ft.ScrollMode.AUTO)), 
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
                    for row in db.execute("SELECT usuario, rol, bloqueado FROM usuarios ORDER BY usuario ASC"):
                        u, r, b = row[0], row[1], row[2]
                        
                        estado_txt = " (Bloqueado 🔒)" if b == 1 else ""
                        
                        def editar(evt, user_name=u, user_role=r):
                            e_usr_nom.value = user_name
                            e_usr_rol.value = user_role
                            e_usr_pwd.value = "" 
                            page.update()

                        def eliminar(evt, user_name=u):
                            if user_name == sesion["usuario"]:
                                return mostrar_alerta("Aviso", "No puedes eliminar tu propio usuario mientras lo estás usando.")
                            db_d = conectar_db()
                            db_d.execute("DELETE FROM usuarios WHERE usuario=?", (user_name,))
                            db_d.commit(); db_d.close()
                            cargar_usuarios()
                            page.snack_bar = ft.SnackBar(ft.Text(f"🗑️ Usuario {user_name} eliminado"), bgcolor="#ef4444"); page.snack_bar.open = True; page.update()

                        # --- BOTÓN PARA DESBLOQUEAR USUARIO ---
                        def desbloquear(evt, user_name=u):
                            db_u = conectar_db()
                            db_u.execute("UPDATE usuarios SET intentos=0, bloqueado=0 WHERE usuario=?", (user_name,))
                            db_u.commit(); db_u.close()
                            cargar_usuarios()
                            page.snack_bar = ft.SnackBar(ft.Text(f"✅ Usuario {user_name} desbloqueado exitosamente"), bgcolor="#10b981"); page.snack_bar.open = True; page.update()

                        botones_accion = [ft.IconButton(ft.icons.DELETE, icon_color="#ef4444", tooltip="Eliminar Usuario", on_click=eliminar)]
                        if b == 1:
                            botones_accion.insert(0, ft.IconButton(ft.icons.LOCK_OPEN, icon_color="#10b981", tooltip="Desbloquear Usuario", on_click=desbloquear))

                        resultados_usr.controls.append(
                            ft.ListTile(
                                title=ft.Text(f"{u}{estado_txt}", color="#ef4444" if b==1 else "#fbbf24", weight="bold"),
                                subtitle=ft.Text(f"Rol asignado: {r}"),
                                trailing=ft.Row(botones_accion, tight=True),
                                on_click=editar
                            )
                        )
                    db.close()
                page.update()

            def guardar_usuario(evt):
                if not e_usr_nom.value or not e_usr_pwd.value: 
                    return mostrar_alerta("Aviso", "Falta el nombre o la contraseña.")
                db = conectar_db()
                if db:
                    # Lógica inteligente: Si el usuario existe lo actualiza (y desbloquea), si no, lo crea.
                    usr_nom_limpio = e_usr_nom.value.upper().strip()
                    existe = db.execute("SELECT count(*) FROM usuarios WHERE usuario=?", (usr_nom_limpio,)).fetchone()[0]
                    
                    if existe > 0:
                        db.execute("UPDATE usuarios SET password=?, rol=?, intentos=0, bloqueado=0 WHERE usuario=?", 
                                   (e_usr_pwd.value.strip(), e_usr_rol.value, usr_nom_limpio))
                    else:
                        db.execute("INSERT INTO usuarios (usuario, password, rol, intentos, bloqueado) VALUES (?,?,?,0,0)", 
                                   (usr_nom_limpio, e_usr_pwd.value.strip(), e_usr_rol.value))
                    
                    db.commit(); db.close()
                    e_usr_nom.value = ""; e_usr_pwd.value = ""; e_usr_rol.value = "ASESOR"
                    cargar_usuarios()
                    page.snack_bar = ft.SnackBar(ft.Text("✅ Usuario guardado y habilitado con éxito"), bgcolor="#8b5cf6"); page.snack_bar.open = True; page.update()

            dlg = ft.AlertDialog(
                title=ft.Text("🔐 Gestión de Usuarios"), 
                content=ft.Container(width=700, content=ft.Column([
                    ft.Text("Crear o Modificar Usuario (Para modificar, escribe el nombre existente y la nueva clave):", size=12, color="white54"),
                    ft.ResponsiveRow([e_usr_nom, e_usr_pwd, e_usr_rol]),
                    ft.ElevatedButton("Guardar Usuario", bgcolor="#8b5cf6", color="white", on_click=guardar_usuario),
                    ft.Divider(color="white24"),
                    ft.Text("Usuarios Registrados en el Sistema:", weight="bold"),
                    resultados_usr
                ], tight=True)), 
                actions=[ft.TextButton("Cerrar", on_click=lambda e: cerrar_dialogo(dlg))]
            )
            page.dialog = dlg; dlg.open = True; cargar_usuarios()

        def abrir_modal_historial(e):
            resultados_hist = ft.ListView(expand=True, spacing=10, height=300)
            buscador_hist = ft.TextField(label="🔍 Buscar por nombre de cliente...", width=400)

            def cargar_historial_lista(evt=None):
                resultados_hist.controls.clear()
                txt_busqueda = (buscador_hist.value or "").upper().strip()
                db = conectar_db()
                if db:
                    if txt_busqueda:
                        # Si hay texto, filtra por cliente
                        filas = db.execute("SELECT nro, cliente, fecha, total, creador FROM historial WHERE UPPER(cliente) LIKE ? ORDER BY nro DESC LIMIT 50", ('%'+txt_busqueda+'%',)).fetchall()
                    else:
                        # Si está vacío, trae los últimos 30
                        filas = db.execute("SELECT nro, cliente, fecha, total, creador FROM historial ORDER BY nro DESC LIMIT 30").fetchall()

                    for row in filas:
                        nro, cli, fec, tot, creador = row[0], row[1], row[2], row[3], row[4]
                        
                        def cargar_cotizacion(evt, numero=nro):
                            db_h = conectar_db()
                            cab = db_h.execute("SELECT cli, nit FROM h_cab WHERE nro=?", (numero,)).fetchone()
                            if cab: input_cliente.value = cab[0] if cab[0] else ""; input_nit.value = cab[1] if cab[1] else ""
                            lista_items.clear()
                            for d in db_h.execute("SELECT desc, cant, und, unit, sub, imp FROM h_det WHERE nro=?", (numero,)):
                                desc_str = d[0] if d[0] else ""
                                try: cant_f = float(d[1])
                                except: cant_f = 1.0
                                und_str = str(d[2]) if d[2] else "UNID"
                                try: unit_f = float(d[3])
                                except: unit_f = 100.0
                                try: sub_f = float(d[4])
                                except: sub_f = cant_f * unit_f
                                impuesto_str = str(d[5]) if d[5] else "EXENTO"
                                if "AIU" in und_str or "IVA" in und_str or "EXENTO" in und_str:
                                    temp = impuesto_str; impuesto_str = und_str; und_str = temp if temp not in ["EXENTO", ""] else "UNID"
                                lista_items.append({"desc": desc_str, "cant": cant_f, "und": und_str, "precio": unit_f, "total": sub_f, "impuesto": impuesto_str})
                            db_h.close()
                            estado["nro_edicion"] = numero
                            actualizar_tabla_visual(); cerrar_dialogo(dlg)
                            mostrar_alerta("Cargado", f"Cotización N° {numero} cargada correctamente.")
                        
                        etiqueta_creador = f" (Por: {creador})"
                        resultados_hist.controls.append(ft.ListTile(title=ft.Text(f"N° {nro} - {cli}{etiqueta_creador}", color="#fbbf24", weight="bold"), subtitle=ft.Text(f"Fecha/Hora: {fec} | Total: ${int(float(tot)):,}"), on_click=cargar_cotizacion))
                db.close()
                page.update()

            buscador_hist.on_change = cargar_historial_lista

            dlg = ft.AlertDialog(
                title=ft.Text("🔍 Historial de Cotizaciones"), 
                content=ft.Container(width=700, content=ft.Column([buscador_hist, resultados_hist], tight=True)), 
                actions=[ft.TextButton("Cerrar", on_click=lambda e: cerrar_dialogo(dlg))]
            )
            page.dialog = dlg; dlg.open = True; cargar_historial_lista()

        def abrir_modal_editar(e):
            if not lista_items: return mostrar_alerta("Aviso", "No hay ítems para editar.")
            lista_edicion = ft.ListView(height=250)
            dlg_editar = ft.AlertDialog(title=ft.Text("✏️ Editar Ítems Actuales"), actions=[ft.TextButton("Cerrar", on_click=lambda e: cerrar_dialogo(dlg_editar))])
            
            def construir_lista():
                lista_edicion.controls.clear()
                for i, item in enumerate(lista_items):
                    def abrir_edicion_individual(evt, index=i):
                        e_cant = ft.TextField(label="Nueva Cantidad", value=str(lista_items[index]['cant']))
                        e_precio = ft.TextField(label="Nuevo Precio", value=str(int(float(lista_items[index]['precio']))))
                        def guardar_cambio(ev):
                            try:
                                c, p = float(e_cant.value), float(e_precio.value)
                                lista_items[index]['cant'], lista_items[index]['precio'], lista_items[index]['total'] = c, p, c * p
                                actualizar_tabla_visual(); cerrar_dialogo(dlg_ind); construir_lista()
                            except: pass
                        dlg_ind = ft.AlertDialog(content=ft.Column([ft.Text(lista_items[index]['desc']), e_cant, e_precio], tight=True), actions=[ft.ElevatedButton("Actualizar", on_click=guardar_cambio)])
                        page.dialog = dlg_ind; dlg_ind.open = True; page.update()
                    tot_seguro = int(float(item['total']))
                    lista_edicion.controls.append(ft.ListTile(title=ft.Text(f"{item['desc']}", size=13), subtitle=ft.Text(f"Cant: {item['cant']} | Total: ${tot_seguro:,}"), on_click=abrir_edicion_individual))
                dlg_editar.content = lista_edicion; page.update()
                
            construir_lista()
            page.dialog = dlg_editar; dlg_editar.open = True; page.update()

        def descargar_backup(e):
            try:
                shutil.copy2('ingectec.db', 'assets/backup_ingectec.db')
                page.launch_url('/backup_ingectec.db')
                page.snack_bar = ft.SnackBar(ft.Text("✅ Backup descargando..."), bgcolor="#2563eb"); page.snack_bar.open = True; page.update()
            except Exception as ex: mostrar_alerta("Error", str(ex))

        def limpiar_todo(e):
            lista_items.clear(); estado["nro_edicion"] = None; actualizar_tabla_visual(); input_cliente.value = ""; input_nit.value = ""; lista_busqueda_cli.visible = False; page.update()

        def generar_pdf_web(e):
            try:
                if not lista_items or not input_cliente.value: 
                    return mostrar_alerta("Aviso", "Faltan ítems o nombre del cliente.")
                
                c_nom = str(input_cliente.value or "").upper()
                c_nit = str(input_nit.value or "")
                c_ciu_origen = str(input_ciudad.value or "Yumbo")
                c_atn = str(input_atencion.value or "")
                c_ref = str(input_ref.value or "")

                c_dir = ""
                c_email = ""
                c_ciu_cli = ""
                c_tel = ""

                db = conectar_db()
                try:
                    cli_data = db.execute("SELECT dir, email, ciu, tel FROM cli WHERE n=?", (c_nom,)).fetchone()
                    if cli_data:
                        c_dir = cli_data[0] or ""
                        c_email = cli_data[1] or ""
                        c_ciu_cli = cli_data[2] or ""
                        c_tel = cli_data[3] or ""
                except: pass

                nro_doc = estado["nro_edicion"]
                mes_actual = datetime.now().strftime("%m")
                
                if not nro_doc:
                    cursor_num = db.cursor()
                    cursor_num.execute("BEGIN IMMEDIATE")
                    cursor_num.execute("UPDATE n_cot SET num = num + 1 WHERE id=1")
                    cursor_num.execute("SELECT num FROM n_cot WHERE id=1")
                    num_fetch = cursor_num.fetchone()
                    num_puro = num_fetch[0] if num_fetch else 100
                    nro_doc = f"{mes_actual}-{num_puro:03d}"
                    db.commit()
                else:
                    db.execute("DELETE FROM h_cab WHERE nro=?", (nro_doc,))
                    db.execute("DELETE FROM h_det WHERE nro=?", (nro_doc,))
                    db.execute("DELETE FROM historial WHERE nro=?", (nro_doc,))
                    
                db.execute("INSERT OR IGNORE INTO cli (n, i) VALUES (?, ?)", (c_nom, c_nit))
                db.execute("INSERT INTO h_cab VALUES (?,?,?,?,?,?,?)", (nro_doc, c_nom, c_nit, "", "", "", ""))
                
                subtotal_global = 0
                iva_bases = {}
                
                for item in lista_items:
                    cant_n = float(item['cant']); unit_n = float(item['precio']); tot_item_n = float(item['total'])
                    imp_str = item.get('impuesto', 'EXENTO'); und_str = item.get('und', 'UNID')
                    
                    db.execute("INSERT INTO h_det VALUES (?,?,?,?,?,?,?)", (nro_doc, item['desc'], cant_n, und_str, unit_n, tot_item_n, imp_str))
                    subtotal_global += tot_item_n
                    
                    if "IVA" in imp_str.upper():
                        try: pct = float(re.findall(r"[\d.]+", imp_str)[0])
                        except: pct = 19
                        iva_bases[pct] = iva_bases.get(pct, 0) + tot_item_n

                try: pct_a = float(input_pct_a.value)
                except: pct_a = 0
                try: pct_i = float(input_pct_i.value)
                except: pct_i = 0
                try: pct_u = float(input_pct_u.value)
                except: pct_u = 0
                try: pct_iva_u = float(input_pct_iva_u.value)
                except: pct_iva_u = 0

                val_a = subtotal_global * (pct_a / 100)
                val_i = subtotal_global * (pct_i / 100)
                val_u = subtotal_global * (pct_u / 100)
                total_aiu_sum = val_a + val_i + val_u
                val_iva_u_val = val_u * (pct_iva_u / 100)

                total_final_cotizacion = subtotal_global + total_aiu_sum + val_iva_u_val
                for pct_iva, base_amt in iva_bases.items():
                    total_final_cotizacion += base_amt * (pct_iva / 100)

                fecha_hora_actual = datetime.now().strftime("%Y-%m-%d %H:%M")
                db.execute("INSERT INTO historial (nro, cliente, fecha, archivo, total, origen, creador) VALUES (?,?,?,?,?,?,?)", 
                           (nro_doc, c_nom, fecha_hora_actual, "web.pdf", total_final_cotizacion, "WEB", sesion["usuario"]))
                db.commit(); db.close()

                qr = qrcode.QRCode(box_size=10, border=2)
                qr.add_data(f"https://wa.me/{MI_WHATSAPP}")
                qr.make(fit=True)
                qr.make_image(fill_color="black", back_color="white").save("assets/qr_temp.png")

                p = PDF()
                p.asesor_nombre = sesion["usuario"] # Se inyecta para la trazabilidad
                p.set_margins(10, 10, 10)
                p.set_auto_page_break(auto=True, margin=30)
                p.add_page()
                
                p.set_font('helvetica', 'B', 11)
                meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
                hoy = datetime.now()
                p.cell(0, 5, f"{c_ciu_origen}, {hoy.day} de {meses[hoy.month-1]} de {hoy.year}", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
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
                    p.set_font('helvetica', 'B', 11); p.set_text_color(31, 73, 125); p.write(5, "REFERENCIA: ")
                    p.set_font('helvetica', '', 11); p.set_text_color(0, 0, 0); p.write(5, f"{c_ref}\n"); p.ln(5)

                p.set_fill_color(194, 229, 194); p.set_text_color(0, 0, 0); p.set_font("helvetica", '', 8) 
                p.cell(10, 6, "ITEM", 1, fill=True, align='C'); p.cell(78, 6, "DESCRIPCION", 1, fill=True, align='C')
                p.cell(12, 6, "CANT", 1, fill=True, align='C'); p.cell(25, 6, "UND", 1, fill=True, align='C')
                p.cell(20, 6, "V. UNIT", 1, fill=True, align='C'); p.cell(20, 6, "IMPUESTO", 1, fill=True, align='C')
                p.cell(25, 6, "VALOR", 1, fill=True, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

                p.set_fill_color(255, 255, 255)
                for idx, i in enumerate(lista_items):
                    cant_n = float(i['cant']); unit_n = float(i['precio']); tot_item_n = float(i['total'])
                    desc_lines = textwrap.wrap(i['desc'], width=43) 
                    if not desc_lines: desc_lines = [""]
                    for line_idx, line_text in enumerate(desc_lines):
                        if len(desc_lines) == 1: b_style = 1
                        elif line_idx == 0: b_style = 'LTR'
                        elif line_idx == len(desc_lines) - 1: b_style = 'LBR'
                        else: b_style = 'LR'
                            
                        if line_idx == 0:
                            p.cell(10, 6, f"{idx+1}", border=b_style, align='C'); p.cell(78, 6, f" {line_text}", border=b_style)
                            p.cell(12, 6, f"{cant_n:g}", border=b_style, align='C'); p.cell(25, 6, i.get('und', 'UNID'), border=b_style, align='C')
                            p.cell(20, 6, f"${int(unit_n):,}", border=b_style, align='R'); p.cell(20, 6, i.get('impuesto', 'EXENTO'), border=b_style, align='C')
                            p.cell(25, 6, f"${int(tot_item_n):,}", border=b_style, align='R', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                        else:
                            p.cell(10, 6, "", border=b_style, align='C'); p.cell(78, 6, f" {line_text}", border=b_style)
                            p.cell(12, 6, "", border=b_style, align='C'); p.cell(25, 6, "", border=b_style, align='C')
                            p.cell(20, 6, "", border=b_style, align='R'); p.cell(20, 6, "", border=b_style, align='C')
                            p.cell(25, 6, "", border=b_style, align='R', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

                def print_total_row(label, value, bold=False):
                    if bold: p.set_font('helvetica', 'B', 9)
                    p.set_x(135); p.cell(40, 5, label, 1, align='C'); p.cell(25, 5, f"$ {int(value):,}", 1, align='R', new_x=XPos.LMARGIN, new_y=YPos.NEXT) 
                    if bold: p.set_font('helvetica', '', 9)

                p.set_font('helvetica', '', 9)
                
                print_total_row("SUBTOTAL", subtotal_global)
                print_total_row(f"ADMINISTRACIÓN ({pct_a:g}%)", val_a)
                print_total_row(f"IMPREVISTOS ({pct_i:g}%)", val_i)
                print_total_row(f"UTILIDAD ({pct_u:g}%)", val_u)
                print_total_row("TOTAL AIU", total_aiu_sum, bold=True)
                print_total_row(f"IVA S/UTILIDAD ({pct_iva_u:g}%)", val_iva_u_val)
                
                for pct_iva, base_amt in iva_bases.items():
                    val_iva_normal = base_amt * (pct_iva / 100)
                    print_total_row(f"IVA ({pct_iva:g}%)", val_iva_normal)
                
                print_total_row("TOTAL", total_final_cotizacion, bold=True)

                p.ln(10); p.set_font('helvetica', 'B', 10); p.cell(0, 5, "CONDICIONES COMERCIALES", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                p.ln(2); p.set_font('helvetica', '', 10)
                p.cell(45, 5, "FORMA DE PAGO:", border=0); p.cell(0, 5, str(input_pago.value), border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                p.cell(45, 5, "TIEMPO DE OFERTA:", border=0); p.cell(0, 5, str(input_tiempo.value), border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                
                p.ln(8); p.set_font("helvetica", 'B', 8); p.cell(0, 5, "Escanee este código para atención personalizada y directa con nuestra Gerencia.", border=0, align='L', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                
                current_y = p.get_y()
                p.image("assets/qr_temp.png", 10, current_y, 25, 25)

                nombre_archivo = f"Cotizacion_{nro_doc}.pdf"
                p.output(f"assets/{nombre_archivo}")
                try: os.remove("assets/qr_temp.png")
                except: pass
                
                dlg_d = ft.AlertDialog(title=ft.Text("✅ Guardado y Generado", color="#10b981"), content=ft.Text("Tu cotización está lista en PDF."), actions=[ft.ElevatedButton("📥 DESCARGAR PDF", bgcolor="#2563eb", color="white", on_click=lambda evt: page.launch_url(f"/{nombre_archivo}")), ft.TextButton("Cerrar", on_click=lambda evt: cerrar_dialogo(dlg_d))])
                page.dialog = dlg_d; dlg_d.open = True; page.update()
            except Exception as errorFallo: mostrar_alerta("Error al generar PDF", f"Hubo un fallo: {str(errorFallo)}")

        btn_salir = ft.ElevatedButton("🚪 CERRAR SESIÓN", bgcolor="#ef4444", color="white", on_click=lambda e: mostrar_login())

        botones_top = ft.Row([
            ft.ElevatedButton("➕ AÑADIR ÍTEM", bgcolor="#10b981", color="white", on_click=abrir_modal_item),
            ft.ElevatedButton("📦 BODEGA", bgcolor="#2563eb", color="white", on_click=abrir_modal_bodega),
            ft.ElevatedButton("👥 CLIENTES", bgcolor="#2563eb", color="white", on_click=abrir_modal_clientes),
            ft.ElevatedButton("🔐 USUARIOS", bgcolor="#8b5cf6", color="white", on_click=abrir_modal_usuarios),
            ft.ElevatedButton("🔍 HISTORIAL", bgcolor="#2563eb", color="white", on_click=abrir_modal_historial),
            ft.ElevatedButton("✏️ EDITAR", bgcolor="#475569", color="white", on_click=abrir_modal_editar),
            ft.ElevatedButton("🧹 LIMPIAR", bgcolor="#64748b", color="white", on_click=limpiar_todo),
            ft.ElevatedButton("📂 BACKUPS", bgcolor="#475569", color="white", on_click=descargar_backup),
            btn_salir
        ], wrap=True, alignment=ft.MainAxisAlignment.CENTER)

        tabla = ft.Container(
            content=ft.Column([
                ft.Row([ft.Text(f"COTIZACIÓN ING {nro_actual}", weight="bold", color="#fbbf24", size=16)], alignment=ft.MainAxisAlignment.CENTER),
                ft.Divider(color="white24"),
                ft.ResponsiveRow([
                    ft.Text("DESCRIPCIÓN", weight="bold", color="#fbbf24", col={"sm": 6}, text_align="center"), 
                    ft.Text("CANTIDAD", weight="bold", color="#fbbf24", col={"sm": 3}, text_align="center"), 
                    ft.Text("TOTAL", weight="bold", color="#fbbf24", col={"sm": 3}, text_align="center")
                ]),
                columna_tabla_items, ft.Container(height=10),
                ft.Row([ft.TextButton("❌ QUITAR SELECCIONADO", icon_color="#ef4444", on_click=quitar_seleccionado)], alignment=ft.MainAxisAlignment.CENTER)
            ]), bgcolor="#0f172a", padding=15, border_radius=8, border=ft.border.all(1, "white12")
        )

        f_cli = ft.Container(
            content=ft.Column([
                ft.ResponsiveRow([
                    ft.Column([input_cliente, lista_busqueda_cli], col={"sm": 12, "md": 5, "lg": 5}),
                    ft.Container(content=input_nit, col={"sm": 6, "md": 3, "lg": 3}),
                    ft.Container(content=input_ciudad, col={"sm": 6, "md": 4, "lg": 4})
                ]),
                ft.ResponsiveRow([
                    ft.Container(content=input_atencion, col={"sm": 12, "md": 5, "lg": 5}),
                    ft.Container(content=input_pago, col={"sm": 6, "md": 3, "lg": 3}),
                    ft.Container(content=input_tiempo, col={"sm": 6, "md": 4, "lg": 4})
                ]),
                ft.ResponsiveRow([
                    ft.Container(content=input_ref, col={"sm": 12, "md": 12, "lg": 12})
                ]),
                ft.ResponsiveRow([
                    ft.Container(content=ft.Text("⚙️ Config. AIU (Global):", weight="bold", color="#fbbf24"), col={"sm": 12, "md": 3, "lg": 3}, alignment=ft.alignment.center_left),
                    ft.Container(content=input_pct_a, col={"sm": 4, "md": 2, "lg": 2}),
                    ft.Container(content=input_pct_i, col={"sm": 4, "md": 2, "lg": 2}),
                    ft.Container(content=input_pct_u, col={"sm": 4, "md": 2, "lg": 2}),
                    ft.Container(content=input_pct_iva_u, col={"sm": 4, "md": 3, "lg": 3}),
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER)
            ], spacing=10),
            bgcolor="#0f172a", padding=15, border_radius=8, border=ft.border.all(1, "white12")
        )

        btn_generar = ft.Container(content=ft.ElevatedButton("🚀 GENERAR COTIZACIÓN PROFESIONAL", bgcolor="#f59e0b", color="black", height=50, on_click=generar_pdf_web), alignment=ft.alignment.center, padding=ft.padding.only(top=10, bottom=20))
        lbl_bienvenida = ft.Container(content=ft.Text(f"👤 Usuario conectado: {sesion['usuario']} ({sesion['rol']})", size=12, color="#94a3b8"), alignment=ft.alignment.center_right)
        
        page.add(header, lbl_bienvenida, botones_top, tabla, f_cli, btn_generar)
        page.update()

    mostrar_login()

ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=PORT, host="0.0.0.0", assets_dir="assets")