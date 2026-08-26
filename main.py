import flet as ft
import sqlite3
import os
from fpdf import FPDF
from datetime import datetime

PORT = int(os.environ.get("PORT", 8080))

# Pre-crear la carpeta de archivos para que el servidor web la reconozca desde el inicio
if not os.path.exists("assets"):
    os.makedirs("assets")

def conectar_db():
    try:
        return sqlite3.connect('ingectec.db', timeout=10)
    except Exception as e:
        return None

def main(page: ft.Page):
    page.title = "INGECTEC V300 - PREMIUM"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#1e293b"
    page.padding = 15
    page.scroll = ft.ScrollMode.AUTO

    lista_items = []

    # --- 1. ENCABEZADO ---
    header = ft.Container(content=ft.Text("⚡ INGECTEC SAS", size=22, weight="bold", color="#fbbf24"), alignment=ft.alignment.center, padding=5)

    def cerrar_dialogo(dlg):
        dlg.open = False
        page.update()

    def mostrar_alerta(titulo, mensaje):
        dialogo = ft.AlertDialog(title=ft.Text(titulo, weight="bold", color="#fbbf24"), content=ft.Text(mensaje), actions=[ft.TextButton("OK", on_click=lambda e: cerrar_dialogo(dialogo))])
        page.dialog = dialogo
        dialogo.open = True
        page.update()

    # --- LÓGICA DEL BOTÓN CLIENTES (MODAL COMPLETO) ---
    def abrir_modal_clientes(e):
        resultados_cli = ft.ListView(expand=True, spacing=10, height=300)
        
        def buscar_clientes_bd(evt):
            resultados_cli.controls.clear()
            texto = buscador_cli.value.upper()
            db = conectar_db()
            if db:
                cursor = db.cursor()
                if texto:
                    cursor.execute("SELECT n, i FROM cli WHERE UPPER(n) LIKE ? ORDER BY n ASC", ('%'+texto+'%',))
                else:
                    cursor.execute("SELECT n, i FROM cli ORDER BY n ASC")
                for row in cursor.fetchall():
                    nombre = row[0]
                    nit = row[1] if row[1] else "S/N"
                    def seleccionar(evt, n=nombre, i=nit):
                        input_cliente.value = n
                        input_nit.value = i
                        cerrar_dialogo(modal_cli)
                    resultados_cli.controls.append(ft.ListTile(title=ft.Text(nombre, color="#fbbf24", weight="bold"), subtitle=ft.Text(f"NIT: {nit}"), on_click=seleccionar))
                db.close()
            page.update()

        buscador_cli = ft.TextField(label="Buscar cliente...", on_change=buscar_clientes_bd)
        modal_cli = ft.AlertDialog(
            title=ft.Text("👥 Base de Datos Clientes"),
            content=ft.Column([buscador_cli, resultados_cli], tight=True),
            actions=[ft.TextButton("Cerrar", on_click=lambda evt: cerrar_dialogo(modal_cli))]
        )
        page.dialog = modal_cli
        modal_cli.open = True
        buscar_clientes_bd(None) 
        page.update()

    # --- LÓGICA AÑADIR ÍTEM (MULTIPLE SIN CERRAR) ---
    def abrir_modal_item(e):
        resultados_inv = ft.ListView(expand=True, spacing=10, height=150)
        input_desc = ft.TextField(label="Producto Seleccionado", read_only=True)
        input_cant = ft.TextField(label="Cantidad", value="1", col={"sm": 6})
        input_precio = ft.TextField(label="Precio Unitario", col={"sm": 6})
        
        input_imp_tipo = ft.Dropdown(label="Impuesto", options=[ft.dropdown.Option("AIU"), ft.dropdown.Option("IVA"), ft.dropdown.Option("EXENTO")], value="AIU", col={"sm": 6})
        input_imp_pct = ft.TextField(label="% Impuesto", value="10", col={"sm": 6})

        def buscar_inv_bd(evt):
            resultados_inv.controls.clear()
            texto = buscador_inv.value.upper()
            db = conectar_db()
            if db:
                cursor = db.cursor()
                if texto:
                    cursor.execute("SELECT d, p FROM inv WHERE UPPER(d) LIKE ? ORDER BY d ASC", ('%'+texto+'%',))
                else:
                    cursor.execute("SELECT d, p FROM inv ORDER BY d ASC LIMIT 30")
                for row in cursor.fetchall():
                    desc, precio = row[0], (row[1] if row[1] else 0)
                    def seleccionar_item(evt, d=desc, p=precio):
                        input_desc.value = d; input_precio.value = str(int(p)); page.update()
                    resultados_inv.controls.append(ft.ListTile(title=ft.Text(desc, color="#fbbf24", size=14), subtitle=ft.Text(f"${int(precio):,}"), on_click=seleccionar_item))
                db.close()
            page.update()

        def guardar_item_modal(evt):
            if not input_desc.value or not input_precio.value:
                return
            try:
                d, c, p = input_desc.value, float(input_cant.value), float(input_precio.value)
                imp_str = "EXENTO" if input_imp_tipo.value == "EXENTO" else f"{input_imp_tipo.value} {input_imp_pct.value}%"
                lista_items.append({"desc": d, "cant": c, "total": c * p, "impuesto": imp_str, "precio": p})
                actualizar_tabla_visual()
                
                input_desc.value = ""; input_cant.value = "1"; input_precio.value = ""; buscador_inv.value = ""; buscar_inv_bd(None)
                page.snack_bar = ft.SnackBar(ft.Text("✅ Ítem agregado"), bgcolor="#10b981")
                page.snack_bar.open = True
                page.update()
            except Exception as err:
                pass

        buscador_inv = ft.TextField(label="Buscar en bodega...", on_change=buscar_inv_bd)
        modal_item = ft.AlertDialog(
            title=ft.Text("➕ Añadir a Propuesta"),
            content=ft.Column([buscador_inv, resultados_inv, ft.Divider(color="white24"), input_desc, ft.ResponsiveRow([input_cant, input_precio]), ft.ResponsiveRow([input_imp_tipo, input_imp_pct])], tight=True),
            actions=[ft.ElevatedButton("Guardar", bgcolor="#10b981", color="white", on_click=guardar_item_modal), ft.TextButton("Cerrar Ventana", on_click=lambda e: cerrar_dialogo(modal_item))]
        )
        page.dialog = modal_item
        modal_item.open = True
        buscar_inv_bd(None)
        page.update()

    def limpiar_todo(e):
        lista_items.clear(); actualizar_tabla_visual(); input_cliente.value = ""; input_nit.value = ""; lista_busqueda_cli.visible = False; page.update()
        
    def quitar_seleccionado(e):
        if lista_items:
            lista_items.pop(); actualizar_tabla_visual()

    # --- BOTONES SUPERIORES CONECTADOS ---
    botones_top = ft.Row([
        ft.ElevatedButton("➕ AÑADIR ÍTEM", bgcolor="#10b981", color="white", on_click=abrir_modal_item),
        ft.ElevatedButton("📦 BODEGA", bgcolor="#2563eb", color="white", on_click=lambda e: mostrar_alerta("Bodega", "Opción web en construcción.")),
        ft.ElevatedButton("👥 CLIENTES", bgcolor="#2563eb", color="white", on_click=abrir_modal_clientes),
        ft.ElevatedButton("🔍 HISTORIAL", bgcolor="#2563eb", color="white", on_click=lambda e: mostrar_alerta("Historial", "Opción web en construcción.")),
        ft.ElevatedButton("✏️ EDITAR", bgcolor="#475569", color="white", on_click=lambda e: mostrar_alerta("Editar", "Opción web en construcción.")),
        ft.ElevatedButton("🧹 LIMPIAR", bgcolor="#ef4444", color="white", on_click=limpiar_todo),
        ft.ElevatedButton("📂 BACKUPS", bgcolor="#475569", color="white", on_click=lambda e: mostrar_alerta("Backups", "Se gestiona en servidor.")),
    ], wrap=True, alignment=ft.MainAxisAlignment.CENTER)

    # --- TABLA VISUAL ---
    columna_tabla_items = ft.Column()

    def actualizar_tabla_visual():
        columna_tabla_items.controls.clear()
        for idx, item in enumerate(lista_items):
            columna_tabla_items.controls.append(
                ft.ResponsiveRow([
                    ft.Text(f"{idx+1}. {item['desc']} ({item.get('impuesto', '')})", col={"sm": 6, "md": 6, "lg": 6}, color="white", size=12),
                    ft.Text(f"{item['cant']}", col={"sm": 3, "md": 3, "lg": 3}, text_align="center", color="white"),
                    ft.Text(f"${int(item['total']):,}", col={"sm": 3, "md": 3, "lg": 3}, text_align="right", color="#fbbf24"),
                ])
            )
        page.update()

    tabla = ft.Container(
        content=ft.Column([
            ft.Row([ft.Text("PROPUESTA EN CURSO", weight="bold", color="#fbbf24", size=16)], alignment=ft.MainAxisAlignment.CENTER),
            ft.Divider(color="white24"),
            ft.ResponsiveRow([ft.Text("DESCRIPCIÓN", weight="bold", color="#fbbf24", col={"sm": 6, "md": 6, "lg": 6}), ft.Text("CANT", weight="bold", color="#fbbf24", col={"sm": 3, "md": 3, "lg": 3}, text_align="center"), ft.Text("TOTAL", weight="bold", color="#fbbf24", col={"sm": 3, "md": 3, "lg": 3}, text_align="right")]),
            columna_tabla_items, ft.Container(height=10),
            ft.Row([ft.TextButton("❌ QUITAR ÚLTIMO", icon_color="#ef4444", on_click=quitar_seleccionado)], alignment=ft.MainAxisAlignment.CENTER)
        ]),
        bgcolor="#0f172a", padding=10, border_radius=8, border=ft.border.all(1, "white12")
    )

    # --- BUSCADOR CLIENTES EN VIVO ---
    lista_busqueda_cli = ft.ListView(height=150, visible=False, spacing=2)

    def buscar_cliente_realtime(e):
        texto = input_cliente.value.upper().strip()
        lista_busqueda_cli.controls.clear()
        if len(texto) > 0:
            db = conectar_db()
            if db:
                cursor = db.cursor()
                cursor.execute("SELECT n, i FROM cli WHERE UPPER(n) LIKE ? ORDER BY n ASC LIMIT 10", ('%'+texto+'%',))
                filas = cursor.fetchall()
                for row in filas:
                    n, i = row[0], (row[1] if row[1] else "")
                    def seleccionar(evt, nombre=n, nit=i):
                        input_cliente.value = nombre; input_nit.value = nit; lista_busqueda_cli.visible = False; page.update()
                    lista_busqueda_cli.controls.append(ft.ListTile(title=ft.Text(n, color="#fbbf24", size=13, weight="bold"), subtitle=ft.Text(f"NIT: {i}", size=11), on_click=seleccionar))
                db.close()
                lista_busqueda_cli.visible = len(filas) > 0
        else:
            lista_busqueda_cli.visible = False
        page.update()

    input_cliente = ft.TextField(label="Buscar nombre de cliente...", on_change=buscar_cliente_realtime)
    input_nit = ft.TextField(label="NIT / C.C.", col={"sm": 6, "md": 4, "lg": 4})
    input_ciudad = ft.TextField(label="Ciudad", value="Yumbo", col={"sm": 6, "md": 3, "lg": 3})
    input_atencion = ft.TextField(label="Atención a: (Ej. ING. OSCAR MERA)", col={"sm": 12, "md": 6, "lg": 5})

    f_cli = ft.ResponsiveRow([
        ft.Column([input_cliente, lista_busqueda_cli], col={"sm": 12, "md": 5, "lg": 5}),
        input_nit, input_ciudad, input_atencion,
        ft.TextField(label="Forma Pago", value="30 DIAS", col={"sm": 6, "md": 3, "lg": 4}),
        ft.TextField(label="Tiempo Oferta", value="15 DIAS", col={"sm": 6, "md": 3, "lg": 3}),
        ft.TextField(label="REFERENCIA", col={"sm": 12, "md": 6, "lg": 7}),
        ft.Dropdown(label="Asesor", options=[ft.dropdown.Option("OSCAR MERA"), ft.dropdown.Option("YEISON FABIAN RESTREPO"), ft.dropdown.Option("PAULO LEAL")], value="YEISON FABIAN RESTREPO", col={"sm": 12, "md": 6, "lg": 5}),
    ])

    f_aiu = ft.ResponsiveRow([
        ft.Text("⚙️ Config. AIU (Global):", weight="bold", col={"sm": 12, "md": 3, "lg": 3}),
        ft.TextField(label="Imprev %", value="2", col={"sm": 4, "md": 3, "lg": 2}),
        ft.TextField(label="Util %", value="8", col={"sm": 4, "md": 3, "lg": 2}),
        ft.TextField(label="IVA s/U %", value="19", col={"sm": 4, "md": 3, "lg": 2}),
    ], vertical_alignment=ft.CrossAxisAlignment.CENTER)

    # --- 3. GENERADOR DE PDF (CON BOTÓN DE DESCARGA ANTI-BLOQUEOS) ---
    def generar_pdf_web(e):
        if not lista_items or not input_cliente.value:
            mostrar_alerta("Error", "Faltan ítems o nombre del cliente.")
            return

        # 1. Crear PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('helvetica', 'B', 14)
        pdf.cell(0, 10, f"PROPUESTA COMERCIAL - INGECTEC SAS", new_x="LMARGIN", new_y="NEXT", align="C")
        
        pdf.set_font('helvetica', '', 10)
        pdf.cell(0, 5, f"Fecha: {datetime.now().strftime('%Y-%m-%d')} - {input_ciudad.value}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 5, f"Cliente: {input_cliente.value} | NIT: {input_nit.value}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 5, f"Atención: {input_atencion.value}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

        pdf.set_font('helvetica', 'B', 9)
        pdf.set_fill_color(220, 220, 220)
        pdf.cell(100, 8, "DESCRIPCIÓN", border=1, fill=True)
        pdf.cell(20, 8, "CANT", border=1, align="C", fill=True)
        pdf.cell(30, 8, "V. UNIT", border=1, align="C", fill=True)
        pdf.cell(40, 8, "TOTAL", border=1, align="C", new_x="LMARGIN", new_y="NEXT", fill=True)

        pdf.set_font('helvetica', '', 9)
        subtotal = 0
        for item in lista_items:
            desc_corta = str(item['desc'])[:50]
            pdf.cell(100, 8, f"{desc_corta} ({item['impuesto']})", border=1)
            pdf.cell(20, 8, str(item['cant']), border=1, align="C")
            pdf.cell(30, 8, f"${int(item['precio']):,}", border=1, align="R")
            pdf.cell(40, 8, f"${int(item['total']):,}", border=1, align="R", new_x="LMARGIN", new_y="NEXT")
            subtotal += item['total']

        pdf.ln(5)
        pdf.set_font('helvetica', 'B', 12)
        pdf.cell(150, 10, "TOTAL PROPUESTA:", align="R")
        pdf.cell(40, 10, f"${int(subtotal):,}", align="R", new_x="LMARGIN", new_y="NEXT")

        # 2. Guardar archivo
        nombre_archivo = "cotizacion_actual.pdf"
        pdf.output(f"assets/{nombre_archivo}")
        
        # 3. Mostrar ventana con enlace manual para evitar bloqueos
        dialogo_descarga = ft.AlertDialog(
            title=ft.Text("✅ PDF Generado con Éxito", color="#10b981", weight="bold"),
            content=ft.Text("Tu propuesta está lista. Haz clic en el botón de abajo para descargarla a tu dispositivo."),
            actions=[
                ft.ElevatedButton("📥 DESCARGAR PDF", bgcolor="#2563eb", color="white", on_click=lambda evt: page.launch_url(f"/{nombre_archivo}")),
                ft.TextButton("Cerrar", on_click=lambda evt: cerrar_dialogo(dialogo_descarga))
            ]
        )
        page.dialog = dialogo_descarga
        dialogo_descarga.open = True
        page.update()

    btn_generar = ft.Container(
        content=ft.ElevatedButton("🚀 GENERAR PROPUESTA PROFESIONAL", bgcolor="#f59e0b", color="black", height=50, on_click=generar_pdf_web),
        alignment=ft.alignment.center, padding=ft.padding.only(top=10, bottom=20)
    )

    page.add(header, botones_top, tabla, f_cli, f_aiu, btn_generar)

ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=PORT, host="0.0.0.0", assets_dir="assets")