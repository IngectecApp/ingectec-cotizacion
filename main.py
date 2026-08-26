import flet as ft
import sqlite3
import os
import shutil
from fpdf import FPDF
from datetime import datetime

PORT = int(os.environ.get("PORT", 8080))
if not os.path.exists("assets"): os.makedirs("assets")

def conectar_db():
    try: return sqlite3.connect('ingectec.db', timeout=10)
    except: return None

def main(page: ft.Page):
    page.title = "INGECTEC V300 - PREMIUM"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#1e293b"
    page.padding = 15
    page.scroll = ft.ScrollMode.AUTO

    lista_items = []
    estado = {"nro_edicion": None}

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
            columna_tabla_items.controls.append(
                ft.ResponsiveRow([
                    ft.Text(f"{idx+1}. {item['desc']} ({item.get('impuesto', '')})", col={"sm": 6}, color="white", size=12),
                    ft.Text(f"{item['cant']}", col={"sm": 3}, text_align="center", color="white"),
                    ft.Text(f"${int(item['total']):,}", col={"sm": 3}, text_align="right", color="#fbbf24"),
                ])
            )
        page.update()

    # --- 1. AÑADIR ÍTEM ---
    def abrir_modal_item(e):
        resultados_inv = ft.ListView(expand=True, spacing=10, height=150)
        input_desc = ft.TextField(label="Producto Seleccionado", read_only=True)
        input_cant = ft.TextField(label="Cantidad", value="1", col={"sm": 6})
        input_precio = ft.TextField(label="Precio Unit", col={"sm": 6})
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
                    def sel(evt, desc=d, precio=p): input_desc.value = desc; input_precio.value = str(int(precio)); page.update()
                    resultados_inv.controls.append(ft.ListTile(title=ft.Text(d, color="#fbbf24", size=14), subtitle=ft.Text(f"${int(p):,}"), on_click=sel))
                db.close()
            page.update()

        def guardar_item(evt):
            if not input_desc.value or not input_precio.value: return
            try:
                d, c, p = input_desc.value, float(input_cant.value), float(input_precio.value)
                imp = "EXENTO" if input_imp_tipo.value == "EXENTO" else f"{input_imp_tipo.value} {input_imp_pct.value}%"
                lista_items.append({"desc": d, "cant": c, "precio": p, "total": c*p, "impuesto": imp, "und": "UNID"})
                actualizar_tabla_visual()
                input_desc.value = ""; input_cant.value = "1"; input_precio.value = ""; buscador_inv.value = ""; buscar_inv_bd(None)
                page.snack_bar = ft.SnackBar(ft.Text("✅ Ítem agregado"), bgcolor="#10b981"); page.snack_bar.open = True; page.update()
            except: pass

        buscador_inv = ft.TextField(label="Buscar en bodega...", on_change=buscar_inv_bd)
        dlg = ft.AlertDialog(
            title=ft.Text("➕ Añadir a Propuesta"),
            content=ft.Column([buscador_inv, resultados_inv, input_desc, ft.ResponsiveRow([input_cant, input_precio]), ft.ResponsiveRow([input_imp_tipo, input_imp_pct])], tight=True),
            actions=[ft.ElevatedButton("Guardar", bgcolor="#10b981", color="white", on_click=guardar_item), ft.TextButton("Cerrar", on_click=lambda e: cerrar_dialogo(dlg))]
        )
        page.dialog = dlg; dlg.open = True; buscar_inv_bd(None)

    # --- 2. BODEGA (CRUD) ---
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
                    def sel(evt, desc=d, prec=p): e_desc.value = desc; e_precio.value = str(int(prec)); e_stock.value="0"; page.update()
                    resultados_bod.controls.append(ft.ListTile(title=ft.Text(f"{d} (Stock: {s})", size=13), on_click=sel))
                db.close()
            page.update()

        def guardar_bodega(evt):
            if not e_desc.value: return
            try:
                db = conectar_db()
                db.execute("INSERT INTO inv VALUES (?,?,?) ON CONFLICT(d) DO UPDATE SET stock=stock+excluded.stock, p=excluded.p", 
                           (e_desc.value.upper(), float(e_precio.value or 0), float(e_stock.value or 0)))
                db.commit(); db.close()
                e_desc.value = ""; e_precio.value = ""; e_stock.value = "0"; buscar_bodega(None)
                page.snack_bar = ft.SnackBar(ft.Text("✅ Bodega actualizada"), bgcolor="#2563eb"); page.snack_bar.open = True; page.update()
            except Exception as ex: mostrar_alerta("Error", str(ex))

        e_desc.on_change = buscar_bodega
        dlg = ft.AlertDialog(title=ft.Text("📦 Gestión de Bodega"), content=ft.Column([e_desc, resultados_bod, ft.ResponsiveRow([e_precio, e_stock])], tight=True), actions=[ft.ElevatedButton("Guardar/Sumar", bgcolor="#2563eb", color="white", on_click=guardar_bodega), ft.TextButton("Cerrar", on_click=lambda e: cerrar_dialogo(dlg))])
        page.dialog = dlg; dlg.open = True; buscar_bodega(None)

    # --- 3. CLIENTES (VENTANA FLOTANTE) ---
    def abrir_modal_clientes(e):
        resultados_cli = ft.ListView(expand=True, spacing=10, height=250)
        def buscar_clientes_bd(evt):
            resultados_cli.controls.clear()
            txt = (buscador_cli.value or "").upper()
            db = conectar_db()
            if db:
                for row in db.execute("SELECT n, i FROM cli WHERE UPPER(n) LIKE ? ORDER BY n ASC LIMIT 50", ('%'+txt+'%',)):
                    n, i = row[0], (row[1] if row[1] else "")
                    def sel(evt, nom=n, nit=i):
                        input_cliente.value = nom; input_nit.value = nit; cerrar_dialogo(dlg)
                    resultados_cli.controls.append(ft.ListTile(title=ft.Text(n, color="#fbbf24", weight="bold"), subtitle=ft.Text(f"NIT: {i}"), on_click=sel))
                db.close()
            page.update()

        buscador_cli = ft.TextField(label="Buscar cliente...", on_change=buscar_clientes_bd)
        dlg = ft.AlertDialog(title=ft.Text("👥 Base de Datos Clientes"), content=ft.Column([buscador_cli, resultados_cli], tight=True), actions=[ft.TextButton("Cerrar", on_click=lambda e: cerrar_dialogo(dlg))])
        page.dialog = dlg; dlg.open = True; buscar_clientes_bd(None)

    # --- 4. HISTORIAL ---
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
                        lista_items.append({"desc": d[0], "cant": d[1], "und": d[2], "precio": d[3], "total": d[4], "impuesto": d[5]})
                    db_h.close()
                    estado["nro_edicion"] = numero
                    actualizar_tabla_visual()
                    cerrar_dialogo(dlg)
                    mostrar_alerta("Cargado", f"Propuesta N° {numero} cargada para edición.")
                resultados_hist.controls.append(ft.ListTile(title=ft.Text(f"N° {nro} - {cli}", color="#fbbf24", weight="bold"), subtitle=ft.Text(f"Fecha: {fec} | Total: ${int(tot):,}"), on_click=cargar_historial))
            db.close()
            
        dlg = ft.AlertDialog(title=ft.Text("🔍 Historial de Propuestas"), content=resultados_hist, actions=[ft.TextButton("Cerrar", on_click=lambda e: cerrar_dialogo(dlg))])
        page.dialog = dlg; dlg.open = True; page.update()

    # --- 5. EDITAR ÍTEMS ACTUALES ---
    def abrir_modal_editar(e):
        if not lista_items: return mostrar_alerta("Aviso", "No hay ítems para editar.")
        lista_edicion = ft.ListView(height=250)
        dlg_editar = ft.AlertDialog(title=ft.Text("✏️ Editar Ítems Actuales"), actions=[ft.TextButton("Cerrar", on_click=lambda e: cerrar_dialogo(dlg_editar))])
        
        def construir_lista():
            lista_edicion.controls.clear()
            for i, item in enumerate(lista_items):
                def abrir_edicion_individual(evt, index=i):
                    e_cant = ft.TextField(label="Nueva Cantidad", value=str(lista_items[index]['cant']))
                    e_precio = ft.TextField(label="Nuevo Precio", value=str(lista_items[index]['precio']))
                    def guardar_cambio(ev):
                        try:
                            c, p = float(e_cant.value), float(e_precio.value)
                            lista_items[index]['cant'], lista_items[index]['precio'], lista_items[index]['total'] = c, p, c * p
                            actualizar_tabla_visual(); cerrar_dialogo(dlg_ind); construir_lista()
                        except: pass
                    dlg_ind = ft.AlertDialog(content=ft.Column([ft.Text(lista_items[index]['desc']), e_cant, e_precio], tight=True), actions=[ft.ElevatedButton("Actualizar", on_click=guardar_cambio)])
                    page.dialog = dlg_ind; dlg_ind.open = True; page.update()
                lista_edicion.controls.append(ft.ListTile(title=ft.Text(f"{item['desc']}", size=13), subtitle=ft.Text(f"Cant: {item['cant']} | Total: ${int(item['total']):,}"), on_click=abrir_edicion_individual))
            dlg_editar.content = lista_edicion; page.update()
            
        construir_lista()
        page.dialog = dlg_editar; dlg_editar.open = True; page.update()

    # --- BACKUPS Y LIMPIAR ---
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

    # --- BOTONES PRINCIPALES ACTIVOS ---
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

    f_cli = ft.ResponsiveRow([
        ft.Column([input_cliente, lista_busqueda_cli], col={"sm": 12, "md": 5, "lg": 5}),
        input_nit, input_ciudad, input_atencion,
        ft.TextField(label="Forma Pago", value="30 DIAS", col={"sm": 6, "md": 3, "lg": 4}),
        ft.TextField(label="Tiempo Oferta", value="15 DIAS", col={"sm": 6, "md": 3, "lg": 3}),
        ft.TextField(label="REFERENCIA", col={"sm": 12, "md": 6, "lg": 7}),
        ft.Dropdown(label="Asesor", options=[ft.dropdown.Option("OSCAR MERA"), ft.dropdown.Option("YEISON FABIAN RESTREPO"), ft.dropdown.Option("PAULO LEAL")], value="YEISON FABIAN RESTREPO", col={"sm": 12, "md": 6, "lg": 5}),
    ])

    f_aiu = ft.ResponsiveRow([ft.Text("⚙️ Config. AIU:", weight="bold", col={"sm": 12, "md": 3}), ft.TextField(label="Imprev %", value="2", col={"sm": 4, "md": 3}), ft.TextField(label="Util %", value="8", col={"sm": 4, "md": 3}), ft.TextField(label="IVA s/U %", value="19", col={"sm": 4, "md": 3})], vertical_alignment=ft.CrossAxisAlignment.CENTER)

    # --- 6. GENERADOR ROBUSTO DE PDF ---
    def generar_pdf_web(e):
        try:
            if not lista_items or not input_cliente.value: 
                return mostrar_alerta("Aviso", "Faltan ítems o nombre del cliente.")
            
            # 1. Aseguramos que ningún texto esté vacío para que FPDF no falle
            c_nom = str(input_cliente.value or "").upper()
            c_nit = str(input_nit.value or "")
            c_ciu = str(input_ciudad.value or "Yumbo")
            c_atn = str(input_atencion.value or "")

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
            
            subtotal = 0
            for item in lista_items:
                db.execute("INSERT INTO h_det VALUES (?,?,?,?,?,?,?)", (nro_doc, item['desc'], item['cant'], item.get('und', 'UNID'), item['precio'], item['total'], item.get('impuesto', 'EXENTO')))
                if not estado["nro_edicion"]: # Solo resta inventario si es una cotización nueva
                    db.execute("UPDATE inv SET stock = stock - ? WHERE d=?", (item['cant'], item['desc']))
                subtotal += item['total']
                
            db.execute("INSERT INTO historial VALUES (?,?,?,?,?,?)", (nro_doc, c_nom, datetime.now().strftime("%Y-%m-%d"), "web.pdf", subtotal, "WEB"))
            db.commit(); db.close()

            pdf = FPDF()
            pdf.add_page(); pdf.set_font('helvetica', 'B', 14)
            pdf.cell(0, 10, f"PROPUESTA COMERCIAL - ING {nro_doc}", new_x="LMARGIN", new_y="NEXT", align="C")
            pdf.set_font('helvetica', '', 10)
            pdf.cell(0, 5, f"Fecha: {datetime.now().strftime('%Y-%m-%d')} - {c_ciu}", new_x="LMARGIN", new_y="NEXT")
            pdf.cell(0, 5, f"Cliente: {c_nom} | NIT: {c_nit}", new_x="LMARGIN", new_y="NEXT")
            if c_atn: pdf.cell(0, 5, f"Atención: {c_atn}", new_x="LMARGIN", new_y="NEXT")
            
            pdf.ln(5); pdf.set_font('helvetica', 'B', 9); pdf.set_fill_color(220, 220, 220)
            pdf.cell(100, 8, "DESCRIPCIÓN", border=1, fill=True); pdf.cell(20, 8, "CANT", border=1, align="C", fill=True)
            pdf.cell(30, 8, "V. UNIT", border=1, align="C", fill=True); pdf.cell(40, 8, "TOTAL", border=1, align="C", new_x="LMARGIN", new_y="NEXT", fill=True)
            pdf.set_font('helvetica', '', 9)
            
            for item in lista_items:
                desc_corta = str(item['desc'])[:50]
                pdf.cell(100, 8, f"{desc_corta} ({item.get('impuesto', 'EXENTO')})", border=1); pdf.cell(20, 8, str(item['cant']), border=1, align="C")
                pdf.cell(30, 8, f"${int(item['precio']):,}", border=1, align="R"); pdf.cell(40, 8, f"${int(item['total']):,}", border=1, align="R", new_x="LMARGIN", new_y="NEXT")
            
            pdf.ln(5); pdf.set_font('helvetica', 'B', 12); pdf.cell(150, 10, "TOTAL PROPUESTA:", align="R")
            pdf.cell(40, 10, f"${int(subtotal):,}", align="R", new_x="LMARGIN", new_y="NEXT")
            
            nombre_archivo = f"Cotizacion_{nro_doc}.pdf"
            pdf.output(f"assets/{nombre_archivo}")
            
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
            # Si algo vuelve a fallar, te mostrará la alerta exacta en pantalla
            mostrar_alerta("Error al generar PDF", f"Hubo un fallo: {str(errorFallo)}")

    btn_generar = ft.Container(content=ft.ElevatedButton("🚀 GENERAR PROPUESTA PROFESIONAL", bgcolor="#f59e0b", color="black", height=50, on_click=generar_pdf_web), alignment=ft.alignment.center, padding=ft.padding.only(top=10, bottom=20))
    page.add(header, botones_top, tabla, f_cli, f_aiu, btn_generar)

ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=PORT, host="0.0.0.0", assets_dir="assets")