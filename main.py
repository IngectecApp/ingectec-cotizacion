import flet as ft
import sqlite3
import os

PORT = int(os.environ.get("PORT", 8080))

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
    header = ft.Container(
        content=ft.Text("⚡ INGECTEC SAS", size=22, weight="bold", color="#fbbf24"),
        alignment=ft.alignment.center,
        padding=5
    )

    def cerrar_dialogo(dlg):
        dlg.open = False
        page.update()

    def mostrar_alerta(titulo, mensaje):
        dialogo = ft.AlertDialog(
            title=ft.Text(titulo, weight="bold", color="#fbbf24"),
            content=ft.Text(mensaje),
            actions=[ft.TextButton("OK", on_click=lambda e: cerrar_dialogo(dialogo))]
        )
        page.dialog = dialogo
        dialogo.open = True
        page.update()

    # --- 2. LÓGICA AÑADIR ÍTEM (AHORA CON IMPUESTOS) ---
    def abrir_modal_item(e):
        resultados_inv = ft.ListView(expand=True, spacing=10, height=150)
        
        input_desc = ft.TextField(label="Producto Seleccionado", read_only=True)
        input_cant = ft.TextField(label="Cantidad", value="1", col={"sm": 6})
        input_precio = ft.TextField(label="Precio Unitario", col={"sm": 6})
        
        # Nuevos campos de Impuesto tal como los pediste
        input_imp_tipo = ft.Dropdown(
            label="Impuesto", 
            options=[ft.dropdown.Option("AIU"), ft.dropdown.Option("IVA"), ft.dropdown.Option("EXENTO")], 
            value="AIU", col={"sm": 6}
        )
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
                    desc = row[0]
                    precio = row[1] if row[1] else 0
                    
                    def seleccionar_item(evt, d=desc, p=precio):
                        input_desc.value = d
                        input_precio.value = str(int(p))
                        page.update()

                    resultados_inv.controls.append(
                        ft.ListTile(title=ft.Text(desc, color="#fbbf24", size=14), subtitle=ft.Text(f"${int(precio):,}"), on_click=seleccionar_item)
                    )
                db.close()
            page.update()

        def guardar_item_modal(evt):
            if not input_desc.value or not input_precio.value:
                return
            try:
                d = input_desc.value
                c = float(input_cant.value)
                p = float(input_precio.value)
                
                # Construir el texto del impuesto ("AIU 10%")
                if input_imp_tipo.value == "EXENTO":
                    imp_str = "EXENTO"
                else:
                    imp_str = f"{input_imp_tipo.value} {input_imp_pct.value}%"

                total = c * p
                lista_items.append({"desc": d, "cant": c, "total": total, "impuesto": imp_str})
                actualizar_tabla_visual()
                cerrar_dialogo(modal_item)
            except Exception as err:
                pass

        buscador_inv = ft.TextField(label="Buscar en bodega...", on_change=buscar_inv_bd)

        modal_item = ft.AlertDialog(
            title=ft.Text("➕ Añadir a Propuesta"),
            content=ft.Column([
                buscador_inv, 
                resultados_inv,
                ft.Divider(color="white24"),
                input_desc,
                ft.ResponsiveRow([input_cant, input_precio]),
                ft.ResponsiveRow([input_imp_tipo, input_imp_pct]) # Aquí agregamos la fila de impuestos
            ], tight=True),
            actions=[
                ft.ElevatedButton("Guardar", bgcolor="#10b981", color="white", on_click=guardar_item_modal),
                ft.TextButton("Cancelar", on_click=lambda e: cerrar_dialogo(modal_item))
            ]
        )
        page.dialog = modal_item
        modal_item.open = True
        buscar_inv_bd(None)
        page.update()

    def limpiar_todo(e):
        lista_items.clear()
        actualizar_tabla_visual()
        input_cliente.value = ""
        input_nit.value = ""
        lista_busqueda_cli.visible = False
        page.update()
        
    def quitar_seleccionado(e):
        if lista_items:
            lista_items.pop()
            actualizar_tabla_visual()

    # --- BOTONES SUPERIORES (Se mantienen los originales) ---
    botones_top = ft.Row([
        ft.ElevatedButton("➕ AÑADIR ÍTEM", bgcolor="#10b981", color="white", on_click=abrir_modal_item),
        ft.ElevatedButton("📦 BODEGA", bgcolor="#2563eb", color="white", on_click=lambda e: mostrar_alerta("Bodega", "Próximo paso: Habilitar CRUD de bodega.")),
        ft.ElevatedButton("👥 CLIENTES", bgcolor="#2563eb", color="white", on_click=lambda e: mostrar_alerta("Clientes", "Próximo paso: Gestor completo de clientes.")),
        ft.ElevatedButton("🔍 HISTORIAL", bgcolor="#2563eb", color="white", on_click=lambda e: mostrar_alerta("Historial", "Próximo paso: Visor de facturas anteriores.")),
        ft.ElevatedButton("✏️ EDITAR", bgcolor="#475569", color="white", on_click=lambda e: mostrar_alerta("Editar", "Próximo paso: Editar ítem seleccionado.")),
        ft.ElevatedButton("🧹 LIMPIAR", bgcolor="#ef4444", color="white", on_click=limpiar_todo),
        ft.ElevatedButton("📂 BACKUPS", bgcolor="#475569", color="white", on_click=lambda e: mostrar_alerta("Backups", "En la nube, el backup se descarga como archivo .db")),
    ], wrap=True, alignment=ft.MainAxisAlignment.CENTER)

    # --- TABLA VISUAL ---
    columna_tabla_items = ft.Column()

    def actualizar_tabla_visual():
        columna_tabla_items.controls.clear()
        for idx, item in enumerate(lista_items):
            imp = item.get("impuesto", "")
            columna_tabla_items.controls.append(
                ft.ResponsiveRow([
                    ft.Text(f"{idx+1}. {item['desc']} ({imp})", col={"sm": 6, "md": 6, "lg": 6}, color="white", size=12),
                    ft.Text(f"{item['cant']}", col={"sm": 3, "md": 3, "lg": 3}, text_align="center", color="white"),
                    ft.Text(f"${int(item['total']):,}", col={"sm": 3, "md": 3, "lg": 3}, text_align="right", color="#fbbf24"),
                ])
            )
        page.update()

    tabla = ft.Container(
        content=ft.Column([
            ft.Row([ft.Text("PROPUESTA EN CURSO", weight="bold", color="#fbbf24", size=16)], alignment=ft.MainAxisAlignment.CENTER),
            ft.Divider(color="white24"),
            ft.ResponsiveRow([
                ft.Text("DESCRIPCIÓN", weight="bold", color="#fbbf24", col={"sm": 6, "md": 6, "lg": 6}),
                ft.Text("CANT", weight="bold", color="#fbbf24", col={"sm": 3, "md": 3, "lg": 3}, text_align="center"),
                ft.Text("TOTAL", weight="bold", color="#fbbf24", col={"sm": 3, "md": 3, "lg": 3}, text_align="right"),
            ]),
            columna_tabla_items,
            ft.Container(height=10),
            ft.Row([ft.TextButton("❌ QUITAR ÚLTIMO", icon_color="#ef4444", style=ft.ButtonStyle(color="#ef4444"), on_click=quitar_seleccionado)], alignment=ft.MainAxisAlignment.CENTER)
        ]),
        bgcolor="#0f172a",
        padding=10,
        border_radius=8,
        border=ft.border.all(1, "white12")
    )

    # --- 3. BÚSQUEDA DE CLIENTES EN VIVO (Tal como lo pediste) ---
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
                        input_cliente.value = nombre
                        input_nit.value = nit
                        lista_busqueda_cli.visible = False
                        page.update()
                        
                    lista_busqueda_cli.controls.append(
                        ft.ListTile(
                            title=ft.Text(n, color="#fbbf24", size=13, weight="bold"), 
                            subtitle=ft.Text(f"NIT: {i}", size=11), 
                            on_click=seleccionar
                        )
                    )
                db.close()
                lista_busqueda_cli.visible = len(filas) > 0
        else:
            lista_busqueda_cli.visible = False
            
        page.update()

    input_cliente = ft.TextField(label="Buscar nombre de cliente...", on_change=buscar_cliente_realtime)
    input_nit = ft.TextField(label="NIT / C.C.", col={"sm": 6, "md": 4, "lg": 4})

    # Agrupamos el buscador y la lista desplegable en una sola columna para que no deforme el diseño
    col_buscador = ft.Column([input_cliente, lista_busqueda_cli], col={"sm": 12, "md": 5, "lg": 5})

    f_cli = ft.ResponsiveRow([
        col_buscador,
        input_nit,
        ft.TextField(label="Ciudad", value="Yumbo", col={"sm": 6, "md": 3, "lg": 3}),
        ft.TextField(label="Atención a: (Ej. ING. OSCAR MERA)", col={"sm": 12, "md": 6, "lg": 5}),
        ft.TextField(label="Forma Pago", value="30 DIAS", col={"sm": 6, "md": 3, "lg": 4}),
        ft.TextField(label="Tiempo Oferta", value="15 DIAS", col={"sm": 6, "md": 3, "lg": 3}),
        ft.TextField(label="Escribe la REFERENCIA aquí...", col={"sm": 12, "md": 6, "lg": 7}),
        ft.Dropdown(
            label="Asesor",
            options=[
                ft.dropdown.Option("OSCAR MERA"),
                ft.dropdown.Option("YEISON FABIAN RESTREPO"),
                ft.dropdown.Option("ORLANDO"),
                ft.dropdown.Option("PAULO LEAL")
            ],
            value="YEISON FABIAN RESTREPO",
            col={"sm": 12, "md": 6, "lg": 5}
        ),
    ])

    f_aiu = ft.ResponsiveRow([
        ft.Text("⚙️ Config. AIU (Global):", weight="bold", col={"sm": 12, "md": 3, "lg": 3}),
        ft.TextField(label="Imprev %", value="2", col={"sm": 4, "md": 3, "lg": 2}),
        ft.TextField(label="Util %", value="8", col={"sm": 4, "md": 3, "lg": 2}),
        ft.TextField(label="IVA s/U %", value="19", col={"sm": 4, "md": 3, "lg": 2}),
    ], vertical_alignment=ft.CrossAxisAlignment.CENTER)

    btn_generar = ft.Container(
        content=ft.ElevatedButton(
            "🚀 GENERAR PROPUESTA PROFESIONAL",
            bgcolor="#f59e0b",
            color="black",
            height=50,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=25)),
            on_click=lambda e: mostrar_alerta("Aviso", "Generador PDF en proceso de conexión.")
        ),
        alignment=ft.alignment.center,
        padding=ft.padding.only(top=10, bottom=20)
    )

    page.add(header, botones_top, tabla, f_cli, f_aiu, btn_generar)

ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=PORT, host="0.0.0.0")