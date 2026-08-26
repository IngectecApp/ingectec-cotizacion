import flet as ft
import sqlite3
import os

PORT = int(os.environ.get("PORT", 8080))

# --- FUNCIÓN PARA CONECTAR A TU BASE DE DATOS ---
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

    # --- LÓGICA DEL BOTÓN CLIENTES ---
    def abrir_modal_clientes(e):
        resultados_cli = ft.ListView(expand=True, spacing=10, height=300)
        
        def buscar_clientes_bd(evt):
            resultados_cli.controls.clear()
            texto = buscador_cli.value.upper()
            db = conectar_db()
            if db:
                cursor = db.cursor()
                # Se quitó el límite y se forzó a mayúsculas para que encuentre todo
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

                    resultados_cli.controls.append(
                        ft.ListTile(
                            title=ft.Text(nombre, color="#fbbf24", weight="bold"),
                            subtitle=ft.Text(f"NIT: {nit}"),
                            on_click=seleccionar
                        )
                    )
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

    # --- LÓGICA DEL BOTÓN AÑADIR ÍTEM ---
    def abrir_modal_item(e):
        resultados_inv = ft.ListView(expand=True, spacing=10, height=200)
        
        input_desc = ft.TextField(label="Producto Seleccionado", read_only=True)
        input_cant = ft.TextField(label="Cantidad", value="1")
        input_precio = ft.TextField(label="Precio Unitario", read_only=True)

        def buscar_inv_bd(evt):
            resultados_inv.controls.clear()
            texto = buscador_inv.value.upper()
            db = conectar_db()
            if db:
                cursor = db.cursor()
                # Se quitó el límite de ítems para mostrar toda la bodega
                if texto:
                    cursor.execute("SELECT d, p FROM inv WHERE UPPER(d) LIKE ? ORDER BY d ASC", ('%'+texto+'%',))
                else:
                    cursor.execute("SELECT d, p FROM inv ORDER BY d ASC")
                
                for row in cursor.fetchall():
                    desc = row[0]
                    precio = row[1] if row[1] else 0
                    
                    def seleccionar_item(evt, d=desc, p=precio):
                        input_desc.value = d
                        input_precio.value = str(int(p))
                        page.update()

                    resultados_inv.controls.append(
                        ft.ListTile(
                            title=ft.Text(desc, color="#fbbf24", weight="bold"),
                            subtitle=ft.Text(f"Precio: ${int(precio):,}"),
                            on_click=seleccionar_item
                        )
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
                total = c * p
                lista_items.append({"desc": d, "cant": c, "total": total})
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
                input_cant,
                input_precio
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

    # --- LIMPIAR PROPUESTA ---
    def limpiar_todo(e):
        lista_items.clear()
        actualizar_tabla_visual()
        input_cliente.value = ""
        input_nit.value = ""
        page.update()
        
    def quitar_seleccionado(e):
        if lista_items:
            lista_items.pop() # Por ahora quita el último para mantener la funcionalidad
            actualizar_tabla_visual()

    # --- BOTONES SUPERIORES ORIGINALES COMPLETOS ---
    botones_top = ft.Row([
        ft.ElevatedButton("➕ AÑADIR ÍTEM", bgcolor="#10b981", color="white", on_click=abrir_modal_item),
        ft.ElevatedButton("📦 BODEGA", bgcolor="#2563eb", color="white", on_click=lambda e: mostrar_alerta("Bodega", "Opción en construcción web.")),
        ft.ElevatedButton("👥 CLIENTES", bgcolor="#2563eb", color="white", on_click=abrir_modal_clientes),
        ft.ElevatedButton("🔍 HISTORIAL", bgcolor="#2563eb", color="white", on_click=lambda e: mostrar_alerta("Historial", "Opción en construcción web.")),
        ft.ElevatedButton("✏️ EDITAR", bgcolor="#475569", color="white", on_click=lambda e: mostrar_alerta("Editar", "Opción en construcción web.")),
        ft.ElevatedButton("🧹 LIMPIAR", bgcolor="#ef4444", color="white", on_click=limpiar_todo),
        ft.ElevatedButton("📂 BACKUPS", bgcolor="#475569", color="white", on_click=lambda e: mostrar_alerta("Backups", "Los backups se manejan internamente en el servidor web.")),
    ], wrap=True, alignment=ft.MainAxisAlignment.CENTER)

    # --- TABLA VISUAL DE LA PROPUESTA ---
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
            ft.Row([ft.Text(f"PROPUESTA ING 161", weight="bold", color="#fbbf24", size=16)], alignment=ft.MainAxisAlignment.CENTER),
            ft.Divider(color="white24"),
            ft.ResponsiveRow([
                ft.Text("DESCRIPCIÓN", weight="bold", color="#fbbf24", col={"sm": 6, "md": 6, "lg": 6}),
                ft.Text("CANT", weight="bold", color="#fbbf24", col={"sm": 3, "md": 3, "lg": 3}, text_align="center"),
                ft.Text("TOTAL", weight="bold", color="#fbbf24", col={"sm": 3, "md": 3, "lg": 3}, text_align="right"),
            ]),
            columna_tabla_items,
            ft.Container(height=20),
            ft.Row([ft.TextButton("❌ QUITAR SELECCIONADO", icon_color="#ef4444", style=ft.ButtonStyle(color="#ef4444"), on_click=quitar_seleccionado)], alignment=ft.MainAxisAlignment.CENTER)
        ]),
        bgcolor="#0f172a",
        padding=10,
        border_radius=8,
        border=ft.border.all(1, "white12")
    )

    # --- FORMULARIO PRINCIPAL ---
    input_cliente = ft.TextField(label="Buscar nombre de cliente...", col={"sm": 12, "md": 5, "lg": 5})
    input_nit = ft.TextField(label="NIT / C.C. (Opcional)", col={"sm": 6, "md": 4, "lg": 4})

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