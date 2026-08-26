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
                except: 
                    pass
        self.set_y(40) 
        
    def footer(self):
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
    page.scroll = ft.ScrollMode.AUTO

    # --- AUTO-RECUPERADOR DE ÍTEMS PERDIDOS ---
    db_rec = conectar_db()
    if db_rec:
        cursor_r = db_rec.cursor()
        items_perdidos = [
            ("BREAKER 2X40", 101861, 100),
            ("TUBO EMT DE 1\" (INCLUYE ASCESORIOS DE INSTALACION)", 35547, 100)
        ]
        for desc, precio, stock in items_perdidos:
            cursor_r.execute("SELECT count(*) FROM inv WHERE d=?", (desc,))
            if cursor_r.fetchone()[0] == 0:
                cursor_r.execute("INSERT INTO inv (d, p, stock) VALUES (?,?,?)", (desc, precio, stock))
        db_rec.commit()
        db_rec.close()

    lista_items = []
    estado = {"nro_edicion": None}
    MI_WHATSAPP = "573175046404"

    header = ft.Container(content=ft.Text("⚡ INGECTEC SAS", size=22, weight="bold", color="#fbbf24"), alignment=ft.alignment.center, padding=5)

    def cerrar_dialogo(dlg):
        dlg.open = False; page.update()

    def mostrar_alerta(titulo, mensaje):
        dialogo = ft.AlertDialog(title=ft.Text(titulo, weight="bold", color="#fbbf24"), content=ft.Text(str(mensaje)), actions=[ft.TextButton("OK", on_click=lambda e: cerrar_dialogo(dialogo))])
        page.dialog = dialogo; dialogo.open = True; page.update()

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

    # --- 1. MÓDULO AÑADIR ÍTEM (VENTANA ANCHA Y UNIDADES DINÁMICAS) ---
    def abrir_modal_item(e):
        resultados_inv = ft.ListView(expand=True, spacing=10, height=150)
        input_desc = ft.TextField(label="Producto Seleccionado", read_only=True)
        
        input_cant = ft.TextField(label="Cantidad", value="1", col={"sm": 3})
        input_und_custom = ft.TextField(label="Iniciales (Ej. KGS)", visible=False, col={"sm": 3})
        input_precio = ft.TextField(label="Precio Unit", col={"sm": 5})
        
        def cambiar_und(evt):
            if input_und.value == "✍️ ESCRIBIR...":
                # Si escoge escribir, hacemos espacio para la nueva casilla
                input_cant.col = {"sm": 2}
                input_und.col = {"sm": 3}
                input_und_custom.visible = True
                input_precio.col = {"sm": 4}
                input_und_custom.focus()
            else:
                # Si vuelve a escoger una normal, ocultamos la casilla custom
                input_cant.col = {"sm": 3}
                input_und.col = {"sm": 4}
                input_und_custom.visible = False
                input_precio.col = {"sm": 5}
            page.update()

        lista_unidades = ["ML", "UNID", "MTS", "GLB", "ROLLO", "DIA", "PAQ", "✍️ ESCRIBIR..."]
        input_und = ft.Dropdown(
            label="Und", 
            options=[ft.dropdown.Option(u) for u in lista_unidades], 
            value="UNID", 
            col={"sm": 4},
            on_change=cambiar_und
        )
        
        input_imp_tipo = ft.Dropdown(label="Impuesto", options=[ft.dropdown.Option("AIU"), ft.dropdown.Option("IVA"), ft.dropdown.Option("EXENTO")], value="AIU", col={"sm": 6})
        input_imp_pct = ft.TextField(label="% Imp", value="10", col={"sm": 6})

        def buscar_inv_bd(evt):
            resultados_inv.controls.clear()
            db = conectar_db()
            if db:
                txt = (buscador_inv.value or "").upper()
                cursor = db.cursor()
                cursor.execute("SELECT d, p FROM inv WHERE UPPER(d) LIKE ? ORDER BY d ASC LIMIT 30", ('%'+txt+'%',))
                for row in cursor.fetchall():
                    d, p = row[0], (row[1] if row[1] else 0)
                    def sel(evt, desc=d, precio=p): 
                        input_desc.value = desc
                        input_precio.value = str(int(float(precio)))
                        
                        if "TUBO" in desc.upper() or "CABLE" in desc.upper():
                            input_und.value = "ML"
                        elif "INSTALACION" in desc.upper():
                            input_und.value = "GLB"
                        else:
                            input_und.value = "UNID"
                            
                        # Restaurar el diseño ancho
                        input_und_custom.visible = False
                        input_cant.col = {"sm": 3}
                        input_und.col = {"sm": 4}
                        input_precio.col = {"sm": 5}
                        page.update()
                        
                    resultados_inv.controls.append(ft.ListTile(title=ft.Text(d, color="#fbbf24", size=14), subtitle=ft.Text(f"${int(float(p)):,}"), on_click=sel))
                db.close()
            page.update()

        def guardar_item(evt):
            if not input_desc.value or not input_precio.value: return
            try:
                d, c, p = input_desc.value, float(input_cant.value), float(input_precio.value)
                imp = "EXENTO" if input_imp_tipo.value == "EXENTO" else f"{input_imp_tipo.value} {input_imp_pct.value}%"
                
                # Rescatar la unidad exacta que el asesor quiere
                if input_und.value == "✍️ ESCRIBIR...":
                    und_final = str(input_und_custom.value).upper().strip()
                else:
                    und_final = input_und.value
                    
                if not und_final: und_final = "UNID"
                
                lista_items.append({"desc": d, "cant": c, "precio": p, "total": c*p, "impuesto": imp, "und": und_final})
                actualizar_tabla_visual()
                
                input_desc.value = ""; input_cant.value = "1"; input_precio.value = ""
                input_und.value = "UNID"; input_und_custom.value = ""; input_und_custom.visible = False
                input_cant.col = {"sm": 3}; input_und.col = {"sm": 4}; input_precio.col = {"sm": 5}
                
                buscador_inv.value = ""; buscar_inv_bd(None)
                page.snack_bar = ft.SnackBar(ft.Text("✅ Ítem agregado"), bgcolor="#10b981"); page.snack_bar.open = True; page.update()
            except: pass

        buscador_inv = ft.TextField(label="Buscar en bodega...", on_change=buscar_inv_bd)
        
        dlg = ft.AlertDialog(
            title=ft.Text("➕ Añadir a Propuesta"), 
            # ¡AQUÍ ESTÁ LA MAGIA PARA QUE NO SE VEA APEÑUSCADO! (width=750)
            content=ft.Container(
                width=750,
                content=ft.Column([
                    buscador_inv, 
                    resultados_inv, 
                    input_desc, 
                    ft.ResponsiveRow([input_cant, input_und, input_und_custom, input_precio]), 
                    ft.ResponsiveRow([input_imp_tipo, input_imp_pct])
                ], tight=True)
            ), 
            actions=[
                ft.ElevatedButton("Guardar", bgcolor="#10b981", color="white", on_click=guardar_item), 
                ft.TextButton("Cerrar", on_click=lambda e: cerrar_dialogo(dlg))
            ]
        )
        page.dialog = dlg; dlg.open = True; buscar_inv_bd(None)

    def abrir_modal_bodega(e):
        resultados_bod = ft.ListView(height=150)
        e_desc = ft.TextField(label="Nombre del Producto")
        e_precio = ft.TextField(label="Precio", col={"sm": 6})
        e_stock = ft.TextField(label="Stock a Sumar", value="0", col={"sm": 6})
        
        def buscar_bodega(evt):
            resultados_bod.controls.clear()
            db = conectar_db()
            if db:
                txt = (e_desc.value or "").upper()
                for row in db.execute("SELECT d, p, stock FROM inv WHERE UPPER(d) LIKE ? LIMIT 20", ('%'+txt+'%',)):
                    d, p, s = row
                    def sel(evt, desc=d, prec=p): e_desc.value = desc; e_precio.value = str(int(float(prec))); e_stock.value="0"; page.update()
                    resultados_bod.controls.append(ft.ListTile(title=ft.Text(f"{d} (Stock: {s})", size=13), on_click=sel))
                db.close()
            page.update()

        def guardar_bodega(evt):
            if not e_desc.value: return
            try:
                db = conectar_db()
                db.execute("INSERT INTO inv VALUES (?,?,?) ON CONFLICT(d) DO UPDATE SET stock=stock+excluded.stock, p=excluded.p", (e_desc.value.upper(), float(e_precio.value or 0), float(e_stock.value or 0)))
                db.commit(); db.close()
                e_desc.value = ""; e_precio.value = ""; e_stock.value = "0"; buscar_bodega(None)
                page.snack_bar = ft.SnackBar(ft.Text("✅ Bodega actualizada"), bgcolor="#2563eb"); page.snack_bar.open = True; page.update()
            except Exception as ex: mostrar_alerta("Error", str(ex))

        e_desc.on_change = buscar_bodega
        dlg = ft.AlertDialog(title=ft.Text("📦 Gestión de Bodega"), content=ft.Column([e_desc, resultados_bod, ft.ResponsiveRow([e_precio, e_stock])], tight=True), actions=[ft.ElevatedButton("Guardar/Sumar", bgcolor="#2563eb", color="white", on_click=guardar_bodega), ft.TextButton("Cerrar", on_click=lambda e: cerrar_dialogo(dlg))])
        page.dialog = dlg; dlg.open = True; buscar_bodega(None)

    def abrir_modal_clientes(e):
        resultados_cli = ft.ListView(expand=True, spacing=10, height=250)
        def buscar_clientes_bd(evt):
            resultados_cli.controls.clear()
            txt = (buscador_cli.value or "").upper()
            db = conectar_db()
            if db:
                for row in db.execute("SELECT n, i FROM cli WHERE UPPER(n) LIKE ? ORDER BY n ASC LIMIT 50", ('%'+txt+'%',)):
                    n, i = row[0], (row[1] if row[1] else "")
                    def sel(evt, nom=n, nit=i): input_cliente.value = nom; input_nit.value = nit; cerrar_dialogo(dlg)
                    resultados_cli.controls.append(ft.ListTile(title=ft.Text(n, color="#fbbf24", weight="bold"), subtitle=ft.Text(f"NIT: {i}"), on_click=sel))
                db.close()
            page.update()

        buscador_cli = ft.TextField(label="Buscar cliente...", on_change=buscar_clientes_bd)
        dlg = ft.AlertDialog(title=ft.Text("👥 Base de Datos Clientes"), content=ft.Column([buscador_cli, resultados_cli], tight=True), actions=[ft.TextButton("Cerrar", on_click=lambda e: cerrar_dialogo(dlg))])
        page.dialog = dlg; dlg.open = True; buscar_clientes_bd(None)

    def abrir_modal_historial(e):
        resultados_hist = ft.ListView(height=300)
        db = conectar_db()
        if db:
            for row in db.execute("SELECT nro, cliente, fecha, total FROM historial ORDER BY nro DESC LIMIT 30"):
                nro, cli, fec, tot = row
                def cargar_historial(evt, numero=nro):
                    db_h = conectar_db()
                    cab = db_h.execute("SELECT cli, nit FROM h_cab WHERE nro=?", (numero,)).fetchone()
                    if cab: 
                        input_cliente.value = cab[0] if cab[0] else ""
                        input_nit.value = cab[1] if cab[1] else ""
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
                            temp = impuesto_str
                            impuesto_str = und_str
                            und_str = temp if temp not in ["EXENTO", ""] else "UNID"
                        lista_items.append({"desc": desc_str, "cant": cant_f, "und": und_str, "precio": unit_f, "total": sub_f, "impuesto": impuesto_str})
                    db_h.close()
                    estado["nro_edicion"] = numero
                    actualizar_tabla_visual()
                    cerrar_dialogo(dlg)
                    mostrar_alerta("Cargado", f"Propuesta N° {numero} cargada correctamente.")
                resultados_hist.controls.append(ft.ListTile(title=ft.Text(f"N° {nro} - {cli}", color="#fbbf24", weight="bold"), subtitle=ft.Text(f"Fecha: {fec} | Total: ${int(float(tot)):,}"), on_click=cargar_historial))
            db.close()
        dlg = ft.AlertDialog(title=ft.Text("🔍 Historial de Propuestas"), content=resultados_hist, actions=[ft.TextButton("Cerrar", on_click=lambda e: cerrar_dialogo(dlg))])
        page.dialog = dlg; dlg.open = True; page.update()

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
        
    def quitar_seleccionado(e):
        if lista_items: lista_items.pop(); actualizar_tabla_visual()

    botones_top = ft.Row([
        ft.ElevatedButton("➕ AÑADIR ÍTEM", bgcolor="#10b981", color="white", on_click=abrir_modal_item),
        ft.ElevatedButton("📦 BODEGA", bgcolor="#2563eb", color="white", on_click=abrir_modal_bodega),
        ft.ElevatedButton("👥 CLIENTES", bgcolor="#2563eb", color="white", on_click=abrir_modal_clientes),
        ft.ElevatedButton("🔍 HISTORIAL", bgcolor="#2563eb", color="white", on_click=abrir_modal_historial),
        ft.ElevatedButton("✏️ EDITAR", bgcolor="#475569", color="white", on_click=abrir_modal_editar),
        ft.ElevatedButton("🧹 LIMPIAR", bgcolor="#ef4444", color="white", on_click=limpiar_todo),
        ft.ElevatedButton("📂 BACKUPS", bgcolor="#475569", color="white", on_click=descargar_backup),
    ], wrap=True, alignment=ft.MainAxisAlignment.CENTER)

    tabla = ft.Container(
        content=ft.Column([
            ft.Row([ft.Text("PROPUESTA EN CURSO", weight="bold", color="#fbbf24", size=16)], alignment=ft.MainAxisAlignment.CENTER),
            ft.Divider(color="white24"),
            ft.ResponsiveRow([ft.Text("DESCRIPCIÓN", weight="bold", color="#fbbf24", col={"sm": 6}), ft.Text("CANT", weight="bold", color="#fbbf24", col={"sm": 3}, text_align="center"), ft.Text("TOTAL", weight="bold", color="#fbbf24", col={"sm": 3}, text_align="right")]),
            columna_tabla_items, ft.Container(height=10),
            ft.Row([ft.TextButton("❌ QUITAR ÚLTIMO", icon_color="#ef4444", on_click=quitar_seleccionado)], alignment=ft.MainAxisAlignment.CENTER)
        ]), bgcolor="#0f172a", padding=10, border_radius=8, border=ft.border.all(1, "white12")
    )

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

    input_cliente = ft.TextField(label="Buscar nombre de cliente...", on_change=buscar_cliente_realtime)
    input_nit = ft.TextField(label="NIT / C.C.", col={"sm": 6, "md": 4, "lg": 4})
    input_ciudad = ft.TextField(label="Ciudad", value="Yumbo", col={"sm": 6, "md": 3, "lg": 3})
    input_atencion = ft.TextField(label="Atención a:", col={"sm": 12, "md": 6, "lg": 5})
    input_pago = ft.TextField(label="Forma Pago", value="30 DIAS", col={"sm": 6, "md": 3, "lg": 4})
    input_tiempo = ft.TextField(label="Tiempo Oferta", value="15 DIAS", col={"sm": 6, "md": 3, "lg": 3})
    input_ref = ft.TextField(label="REFERENCIA", col={"sm": 12, "md": 6, "lg": 7})
    
    input_pct_i = ft.TextField(label="Imprev %", value="2", col={"sm": 4, "md": 3})
    input_pct_u = ft.TextField(label="Util %", value="8", col={"sm": 4, "md": 3})
    input_pct_iva_u = ft.TextField(label="IVA s/U %", value="19", col={"sm": 4, "md": 3})

    f_cli = ft.ResponsiveRow([
        ft.Column([input_cliente, lista_busqueda_cli], col={"sm": 12, "md": 5, "lg": 5}),
        input_nit, input_ciudad, input_atencion, input_pago, input_tiempo, input_ref,
        ft.Dropdown(label="Asesor", options=[ft.dropdown.Option("OSCAR MERA"), ft.dropdown.Option("YEISON FABIAN RESTREPO"), ft.dropdown.Option("PAULO LEAL")], value="YEISON FABIAN RESTREPO", col={"sm": 12, "md": 6, "lg": 5}),
    ])
    f_aiu = ft.ResponsiveRow([ft.Text("⚙️ Config. AIU:", weight="bold", col={"sm": 12, "md": 3}), input_pct_i, input_pct_u, input_pct_iva_u], vertical_alignment=ft.CrossAxisAlignment.CENTER)

    def generar_pdf_web(e):
        try:
            if not lista_items or not input_cliente.value: 
                return mostrar_alerta("Aviso", "Faltan ítems o nombre del cliente.")
            
            c_nom = str(input_cliente.value or "").upper()
            c_nit = str(input_nit.value or "")
            c_ciu = str(input_ciudad.value or "Yumbo")
            c_atn = str(input_atencion.value or "")
            c_ref = str(input_ref.value or "")

            db = conectar_db()
            nro_doc = estado["nro_edicion"]
            if not nro_doc:
                num = db.execute("SELECT num FROM n_cot WHERE id=1").fetchone()
                nro_doc = f"{num[0]:03d}" if num else "100"
                db.execute("UPDATE n_cot SET num = num + 1 WHERE id=1")
            else:
                db.execute("DELETE FROM h_cab WHERE nro=?", (nro_doc,))
                db.execute("DELETE FROM h_det WHERE nro=?", (nro_doc,))
                db.execute("DELETE FROM historial WHERE nro=?", (nro_doc,))
                
            db.execute("INSERT OR IGNORE INTO cli (n, i) VALUES (?, ?)", (c_nom, c_nit))
            db.execute("INSERT INTO h_cab VALUES (?,?,?,?,?,?,?)", (nro_doc, c_nom, c_nit, "", "", "", ""))
            
            subtotal_aiu = 0
            subtotal_exe = 0
            iva_bases = {}
            aiu_bases = {}
            
            for item in lista_items:
                cant_n = float(item['cant'])
                unit_n = float(item['precio'])
                tot_item_n = float(item['total'])
                imp_str = item.get('impuesto', 'EXENTO')
                und_str = item.get('und', 'UNID')
                
                db.execute("INSERT INTO h_det VALUES (?,?,?,?,?,?,?)", (nro_doc, item['desc'], cant_n, und_str, unit_n, tot_item_n, imp_str))
                if not estado["nro_edicion"]: 
                    db.execute("UPDATE inv SET stock = stock - ? WHERE d=?", (cant_n, item['desc']))
                
                if "AIU" in imp_str:
                    subtotal_aiu += tot_item_n
                    try: pct = float(re.findall(r"[\d.]+", imp_str)[0])
                    except: pct = 10
                    aiu_bases[pct] = aiu_bases.get(pct, 0) + tot_item_n
                elif "IVA" in imp_str:
                    try: pct = float(re.findall(r"[\d.]+", imp_str)[0])
                    except: pct = 19
                    iva_bases[pct] = iva_bases.get(pct, 0) + tot_item_n
                else:
                    subtotal_exe += tot_item_n

            subtotal_global = subtotal_aiu + sum(iva_bases.values()) + subtotal_exe
            db.execute("INSERT INTO historial VALUES (?,?,?,?,?,?)", (nro_doc, c_nom, datetime.now().strftime("%Y-%m-%d"), "web.pdf", subtotal_global, "WEB"))
            db.commit(); db.close()

            qr = qrcode.QRCode(box_size=10, border=2)
            qr.add_data(f"https://wa.me/{MI_WHATSAPP}")
            qr.make(fit=True)
            qr.make_image(fill_color="black", back_color="white").save("assets/qr_temp.png")

            p = PDF()
            p.set_margins(10, 10, 10)
            p.set_auto_page_break(auto=True, margin=30)
            p.add_page()
            
            p.set_font('helvetica', 'B', 11)
            meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
            hoy = datetime.now()
            p.cell(0, 5, f"{c_ciu}, {hoy.day} de {meses[hoy.month-1]} de {hoy.year}", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            p.ln(4)

            y_start_cli = p.get_y()
            lines_client = 1 
            if c_atn: lines_client += 1
            if c_nom: lines_client += 1
            if c_nit: lines_client += 1
            p.set_fill_color(240, 240, 240)
            p.rounded_rect(8, y_start_cli - 2, 105, (lines_client * 5) + 4, r=3, style='F') 
            p.rounded_rect(118, y_start_cli - 2, 84, 14, r=3, style='F') 
            
            p.set_xy(10, y_start_cli)
            p.cell(0, 5, "Señores:", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            
            if c_atn:
                p.set_font('helvetica', 'B', 11)
                p.set_text_color(31, 73, 125)
                p.cell(110, 5, c_atn, border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            p.set_text_color(0, 0, 0)
            p.set_font('helvetica', 'B', 11)
            p.cell(110, 5, c_nom, border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            p.set_font('helvetica', '', 11)
            if c_nit: p.cell(110, 5, f"NIT / CC: {c_nit}", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            y_end_cli = p.get_y()

            p.set_xy(120, y_start_cli + 2)
            p.set_font('helvetica', 'B', 12)
            p.set_text_color(31, 73, 125)
            p.cell(80, 5, f"PROPUESTA ING {nro_doc}", border=0, align='C')
            p.set_text_color(0, 0, 0) 

            p.set_y(max(y_end_cli, y_start_cli + 10) + 5)
            if c_ref:
                y_start_ref = p.get_y()
                num_lines = (len("REFERENCIA: " + c_ref) // 85) + 1  
                p.set_fill_color(240, 240, 240)
                p.rounded_rect(8, y_start_ref - 2, 194, (num_lines * 5) + 4, r=3, style='F')
                p.set_font('helvetica', 'B', 11)
                p.set_text_color(31, 73, 125) 
                p.write(5, "REFERENCIA: ")
                p.set_font('helvetica', '', 11)
                p.set_text_color(0, 0, 0) 
                p.write(5, f"{c_ref}\n")
                p.ln(5)

            p.set_fill_color(194, 229, 194) 
            p.set_text_color(0, 0, 0)
            p.set_font("helvetica", '', 8) 
            p.cell(10, 6, "ITEM", 1, fill=True, align='C')
            p.cell(78, 6, "DESCRIPCION", 1, fill=True, align='C')
            p.cell(12, 6, "CANT", 1, fill=True, align='C')
            p.cell(25, 6, "UND", 1, fill=True, align='C')
            p.cell(20, 6, "V. UNIT", 1, fill=True, align='C')
            p.cell(20, 6, "IMPUESTO", 1, fill=True, align='C')
            p.cell(25, 6, "VALOR", 1, fill=True, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

            p.set_fill_color(255, 255, 255)
            for idx, i in enumerate(lista_items):
                cant_n = float(i['cant'])
                unit_n = float(i['precio'])
                tot_item_n = float(i['total'])
                desc_lines = textwrap.wrap(i['desc'], width=43) 
                if not desc_lines: desc_lines = [""]
                
                for line_idx, line_text in enumerate(desc_lines):
                    if len(desc_lines) == 1: b_style = 1
                    elif line_idx == 0: b_style = 'LTR'
                    elif line_idx == len(desc_lines) - 1: b_style = 'LBR'
                    else: b_style = 'LR'
                        
                    if line_idx == 0:
                        p.cell(10, 6, f"{idx+1}", border=b_style, align='C')
                        p.cell(78, 6, f" {line_text}", border=b_style)
                        p.cell(12, 6, f"{cant_n:g}", border=b_style, align='C')
                        p.cell(25, 6, i.get('und', 'UNID'), border=b_style, align='C')
                        p.cell(20, 6, f"${int(unit_n):,}", border=b_style, align='R')
                        p.cell(20, 6, i.get('impuesto', 'EXENTO'), border=b_style, align='C')
                        p.cell(25, 6, f"${int(tot_item_n):,}", border=b_style, align='R', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                    else:
                        p.cell(10, 6, "", border=b_style, align='C')
                        p.cell(78, 6, f" {line_text}", border=b_style)
                        p.cell(12, 6, "", border=b_style, align='C')
                        p.cell(25, 6, "", border=b_style, align='C')
                        p.cell(20, 6, "", border=b_style, align='R')
                        p.cell(20, 6, "", border=b_style, align='C')
                        p.cell(25, 6, "", border=b_style, align='R', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

            try: pct_i = float(input_pct_i.value)
            except: pct_i = 0
            try: pct_u = float(input_pct_u.value)
            except: pct_u = 0
            try: pct_iva_u = float(input_pct_iva_u.value)
            except: pct_iva_u = 0

            total_global = subtotal_global
            
            def print_total_row(label, value, bold=False):
                if bold: p.set_font('helvetica', 'B', 9)
                p.set_x(135) 
                p.cell(40, 5, label, 1, align='C') 
                p.cell(25, 5, f"$ {int(value):,}", 1, align='R', new_x=XPos.LMARGIN, new_y=YPos.NEXT) 
                if bold: p.set_font('helvetica', '', 9)

            p.set_font('helvetica', '', 9)
            print_total_row("SUBTOTAL", subtotal_global)
            
            if subtotal_aiu > 0:
                val_a_total = 0
                for pct_a, base_amt in aiu_bases.items():
                    if pct_a > 0:
                        val_a = base_amt * (pct_a / 100)
                        print_total_row(f"ADMINISTRACIÓN ({pct_a:g}%)", val_a)
                        val_a_total += val_a
                        total_global += val_a

                val_i = subtotal_aiu * (pct_i / 100)
                val_u = subtotal_aiu * (pct_u / 100)
                val_iva_u_val = val_u * (pct_iva_u / 100)

                if pct_i > 0: 
                    print_total_row(f"IMPREVISTOS ({pct_i:g}%)", val_i)
                    total_global += val_i
                if pct_u > 0: 
                    print_total_row(f"UTILIDAD ({pct_u:g}%)", val_u)
                    total_global += val_u
                    
                total_aiu_sum = val_a_total + val_i + val_u
                if total_aiu_sum > 0:
                    print_total_row("TOTAL AIU", total_aiu_sum, bold=True)

                if pct_iva_u > 0: 
                    print_total_row(f"IVA S/UTILIDAD ({pct_iva_u:g}%)", val_iva_u_val)
                    total_global += val_iva_u_val
            
            for pct_iva, base_amt in iva_bases.items():
                if pct_iva > 0:
                    val_iva_normal = base_amt * (pct_iva / 100)
                    print_total_row(f"IVA ({pct_iva:g}%)", val_iva_normal)
                    total_global += val_iva_normal
            
            print_total_row("TOTAL", total_global, bold=True)

            p.ln(10)
            p.set_font('helvetica', 'B', 10)
            p.cell(0, 5, "CONDICIONES COMERCIALES", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            p.ln(2)
            p.set_font('helvetica', '', 10)
            p.cell(45, 5, "FORMA DE PAGO:", border=0)
            p.cell(0, 5, str(input_pago.value), border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            p.cell(45, 5, "TIEMPO DE OFERTA:", border=0)
            p.cell(0, 5, str(input_tiempo.value), border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

            p.ln(8)
            p.set_font("helvetica", 'B', 8)
            p.cell(0, 5, "Escanee este código para atención personalizada y directa con nuestra Gerencia.", border=0, align='L', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            p.image("assets/qr_temp.png", 10, p.get_y(), 25, 25)

            nombre_archivo = f"Cotizacion_{nro_doc}.pdf"
            p.output(f"assets/{nombre_archivo}")
            
            try: os.remove("assets/qr_temp.png")
            except: pass
            
            dlg_d = ft.AlertDialog(
                title=ft.Text("✅ Guardado y Generado", color="#10b981"), 
                content=ft.Text("Tu cotización está lista en PDF."), 
                actions=[
                    ft.ElevatedButton("📥 DESCARGAR PDF", bgcolor="#2563eb", color="white", on_click=lambda evt: page.launch_url(f"/{nombre_archivo}")), 
                    ft.TextButton("Cerrar", on_click=lambda evt: cerrar_dialogo(dlg_d))
                ]
            )
            page.dialog = dlg_d; dlg_d.open = True; page.update()
            
        except Exception as errorFallo:
            mostrar_alerta("Error al generar PDF", f"Hubo un fallo: {str(errorFallo)}")

    btn_generar = ft.Container(content=ft.ElevatedButton("🚀 GENERAR PROPUESTA PROFESIONAL", bgcolor="#f59e0b", color="black", height=50, on_click=generar_pdf_web), alignment=ft.alignment.center, padding=ft.padding.only(top=10, bottom=20))
    page.add(header, botones_top, tabla, f_cli, f_aiu, btn_generar)

ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=PORT, host="0.0.0.0", assets_dir="assets")