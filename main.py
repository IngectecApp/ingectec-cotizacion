import flet as ft
import sqlite3
import os

PORT = int(os.environ.get("PORT", 8080))

# --- FUNCIÓN PARA VERIFICAR BASE DE DATOS ---
def conectar_db():
    try:
        return sqlite3.connect('ingectec.db', timeout=10)
    except Exception as e:
        print(f"Error conectando a la BD: {e}")
        return None

def main(page: ft.Page):
    page.title = "INGECTEC V300 - PREMIUM"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#1e293b"
    page.padding = 15
    page.scroll = ft.ScrollMode.AUTO

    # Variables de control de datos
    lista_items = []

    # --- 1. ENCABEZADO ---
    header = ft.Container(
        content=ft.Text("⚡ INGECTEC SAS", size=22, weight="bold", color="#fbbf24"),
        alignment=ft.alignment.center,
        padding=5
    )

    # --- 2. ACCIONES (DIÁLOGOS MODALES PARA MÓVIL) ---
    def mostrar_alerta(titulo, mensaje):
        dialogo = ft.AlertDialog(
            title=ft.Text(titulo),
            content=ft.Text(mensaje),
            actions=[ft.TextButton("OK", on_click=lambda e: cerrar_dialogo(dialogo))]
        )
        page.dialog = dialogo
        dialogo.open = True
        page.update()

    def cerrar_dialogo(dlg):
        dlg.open = False
        page.update()

    # Botón Añadir Ítem (Modales responsivos)
    def abrir_modal_item(e):
        input_desc = ft.TextField(label="Descripción del Ítem")
        input_cant = ft.TextField(label="Cantidad", value="1")
        input_precio = ft.TextField(label="Precio Unitario")

        def guardar_item_modal(evt):
            try:
                d = input_desc.value.upper()
                c = float(input_cant.value)
                p = float(input_precio.value)
                total = c * p
                lista_items.append({"desc": d, "cant": c, "total": total})
                
                # Actualizar la vista de la tabla
                actualizar_tabla_visual()
                cerrar_dialogo(modal_item)
            except Exception as err:
                mostrar_alerta("Error", f"Verifica los datos numéricos: {err}")

        modal_item = ft.AlertDialog(
            title=ft.Text("➕ Añadir Ítem a Propuesta"),
            content=ft.Column([input_desc, input_cant, input_precio], tight=True),
            actions=[
                ft.ElevatedButton("Guardar", bgcolor="#10b981", color="white", on_click=guardar_item_modal),
                ft.TextButton("Cancelar", on_click=lambda evt: cerrar_dialogo(modal_item))
            ]
        )
        page.dialog = modal_item
        modal_item.open = True
        page.update()

    # Botones Superiores
    botones_top = ft.Row([
        ft.ElevatedButton("➕ AÑADIR ÍTEM", bgcolor="#10b981", color="white", on_click=abrir_modal_item),
        ft.ElevatedButton("📦 BODEGA", bgcolor="#2563eb", color="white", on_click=lambda e: mostrar_alerta("Bodega", "Módulo de bodega en sincronización con nube.")),
        ft.ElevatedButton("👥 CLIENTES", bgcolor="#2563eb", color="white", on_click=lambda e: mostrar_alerta("Clientes", "Gestión de clientes activa.")),
        ft.ElevatedButton("🧹 LIMPIAR", bgcolor="#ef4444", color="white", on_click=lambda e: limpiar_todo()),
    ], wrap=True, alignment=ft.MainAxisAlignment.CENTER)

    # --- 3. TABLA DE PROPUESTA ---
    columna_tabla_items = ft.Column()

    def actualizar_tabla_visual():
        columna_tabla_items.controls.clear()
        for idx, item in enumerate(lista_items):
            columna_tabla_items.controls.append(
                ft.ResponsiveRow([
                    ft.Text(f"{idx+1}. {item['desc']}", col={"sm": 6, "md": 6, "lg": 6}, color="white"),
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
        ]),
        bgcolor="#0f172a",
        padding=10,
        border_radius=8,
        border=ft.border.all(1, "white12")
    )

    def limpiar_todo():
        lista_items.clear()
        actualizar_tabla_visual()
        input_cliente.value = ""
        input_nit.value = ""
        page.update()

    # --- 4. FORMULARIO CLIENTE Y BASE DE DATOS ---
    input_cliente = ft.TextField(label="Buscar nombre de cliente...", col={"sm": 12, "md": 5, "lg": 5})
    input_nit = ft.TextField(label="NIT / C.C.", col={"sm": 6, "md": 4, "lg": 4})
    
    # Autocompletar cliente desde SQLite en la nube
    def buscar_cliente_db(e):
        texto = input_cliente.value.upper()
        if len(texto) > 1:
            db = conectar_db()
            if db:
                res = db.execute("SELECT i FROM cli WHERE n LIKE ?", ('%' + texto + '%',)).fetchone()
                db.close()
                if res and res[0]:
                    input_nit.value = str(res[0])
                    page.update()

    input_cliente.on_change = buscar_cliente_db

    f_cli = ft.ResponsiveRow([
        input_cliente,
        input_nit,
        ft.TextField(label="Ciudad", value="Yumbo", col={"sm": 6, "md": 3, "lg": 3}),
        ft.TextField(label="Atención a: (Ej. ING. OSCAR MERA)", col={"sm": 12, "md": 6, "lg": 5}),
        ft.TextField(label="Forma Pago", value="30 DIAS", col={"sm": 6, "md": 3, "lg": 4}),
        ft.TextField(label="Tiempo Oferta", value="15 DIAS", col={"sm": 6, "md": 3, "lg": 3}),
        ft.TextField(label="Escribe la REFERENCIA aquí...", col={"sm": 12, "md": 6, "lg": 7}),
        ft.Dropdown(
            label="Asesor Comercial",
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

    # --- 5. CONFIGURACIÓN AIU ---
    f_aiu = ft.ResponsiveRow([
        ft.Text("⚙️ Config. AIU (Global):", weight="bold", col={"sm": 12, "md": 3, "lg": 3}),
        ft.TextField(label="Imprev %", value="2", col={"sm": 4, "md": 3, "lg": 2}),
        ft.TextField(label="Util %", value="8", col={"sm": 4, "md": 3, "lg": 2}),
        ft.TextField(label="IVA s/U %", value="19", col={"sm": 4, "md": 3, "lg": 2}),
    ], vertical_alignment=ft.CrossAxisAlignment.CENTER)

    # --- 6. BOTÓN GENERAR PROPUESTA ---
    def generar_propuesta_accion(e):
        if not input_cliente.value or not lista_items:
            mostrar_alerta("Faltan datos", "Debe ingresar un cliente y al menos un ítem.")
            return
        mostrar_alerta("¡Éxito!", "Propuesta lista para procesar con la base de datos.")

    btn_generar = ft.Container(
        content=ft.ElevatedButton(
            "🚀