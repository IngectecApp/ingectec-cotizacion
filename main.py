import flet as ft
import os

PORT = int(os.environ.get("PORT", 8080))

def main(page: ft.Page):
    page.title = "INGECTEC V300 - PREMIUM"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO
    page.bgcolor = "#1E2024" # Color de fondo oscuro similar al tuyo

    # --- 1. Título ---
    page.add(
        ft.Row([ft.Text("⚡ INGECTEC SAS", size=24, weight="bold", color=ft.colors.AMBER)], alignment=ft.MainAxisAlignment.CENTER)
    )

    # --- 2. Botones Superiores ---
    botones_top = ft.Row([
        ft.ElevatedButton("➕ AÑADIR ÍTEM", bgcolor=ft.colors.TEAL, color=ft.colors.WHITE),
        ft.ElevatedButton("📦 BODEGA", bgcolor=ft.colors.BLUE_700, color=ft.colors.WHITE),
        ft.ElevatedButton("👥 CLIENTES", bgcolor=ft.colors.BLUE_700, color=ft.colors.WHITE),
        ft.ElevatedButton("🔍 HISTORIAL", bgcolor=ft.colors.BLUE_700, color=ft.colors.WHITE),
        ft.ElevatedButton("✏️ EDITAR", bgcolor=ft.colors.GREY_700, color=ft.colors.WHITE),
        ft.ElevatedButton("🧹 LIMPIAR", bgcolor=ft.colors.RED_700, color=ft.colors.WHITE),
        ft.ElevatedButton("💾 BACKUPS", bgcolor=ft.colors.GREY_700, color=ft.colors.WHITE),
    ], alignment=ft.MainAxisAlignment.CENTER, wrap=True)
    page.add(botones_top)

    # --- 3. Tabla de Propuesta (Estructura Visual) ---
    tabla_contenedor = ft.Container(
        content=ft.Column([
            ft.Row([ft.Text("PROPUESTA ING 161", weight="bold", color=ft.colors.AMBER)], alignment=ft.MainAxisAlignment.CENTER),
            ft.Divider(color=ft.colors.WHITE24),
            ft.Row([
                ft.Text("DESCRIPCIÓN", weight="bold", color=ft.colors.AMBER, expand=True, text_align=ft.TextAlign.CENTER),
                ft.Text("CANTIDAD", weight="bold", color=ft.colors.AMBER, width=150, text_align=ft.TextAlign.CENTER),
                ft.Text("TOTAL", weight="bold", color=ft.colors.AMBER, width=150, text_align=ft.TextAlign.CENTER),
            ]),
            # Aquí luego inyectaremos los datos de la base de datos
            ft.Container(height=150) 
        ]),
        border=ft.border.all(1, ft.colors.WHITE38),
        border_radius=8,
        padding=15,
        bgcolor="#25282F"
    )
    page.add(tabla_contenedor)

    # Botón Quitar
    page.add(ft.Row([ft.TextButton("❌ QUITAR SELECCIONADO", icon_color=ft.colors.RED, style=ft.ButtonStyle(color=ft.colors.RED))], alignment=ft.MainAxisAlignment.CENTER))

    # --- 4. Formulario de Datos ---
    formulario = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.TextField(label="Buscar nombre de cliente...", expand=True, height=45),
                ft.TextField(label="NIT / C.C. (Opcional)", width=200, height=45),
                ft.TextField(value="Yumbo", width=200, height=45),
            ]),
            ft.Row([
                ft.TextField(label="Atención a: (Ej. ING. OSCAR MERA)", expand=True, height=45),
                ft.TextField(value="30 DIAS", width=200, height=45),
                ft.TextField(value="15 DIAS", width=200, height=45),
            ]),
            ft.Row([
                ft.TextField(label="Escribe la REFERENCIA aquí...", expand=True, height=45),
                ft.Dropdown(options=[ft.dropdown.Option("YEISON FABIAN RESTREPO")], value="YEISON FABIAN RESTREPO", width=300, height=45)
            ]),
            # Configuración AIU
            ft.Row([
                ft.Icon(ft.icons.SETTINGS, size=20),
                ft.Text("Config. AIU (Global):", weight="bold"),
                ft.Text("Imprev %:"), ft.TextField(value="2", width=60, height=40, content_padding=5, text_align=ft.TextAlign.CENTER),
                ft.Text("Util %:"), ft.TextField(value="8", width=60, height=40, content_padding=5, text_align=ft.TextAlign.CENTER),
                ft.Text("IVA s/Util %:"), ft.TextField(value="19", width=60, height=40, content_padding=5, text_align=ft.TextAlign.CENTER),
            ], alignment=ft.MainAxisAlignment.START)
        ]),
        padding=ft.padding.only(top=10, bottom=10)
    )
    page.add(formulario)

    # --- 5. Botón Generar ---
    btn_generar = ft.ElevatedButton(
        "🚀 GENERAR PROPUESTA PROFESIONAL", 
        bgcolor=ft.colors.AMBER_600, 
        color=ft.colors.BLACK,
        height=50,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=25))
    )
    page.add(ft.Row([btn_generar], alignment=ft.MainAxisAlignment.CENTER))

ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=PORT, host="0.0.0.0")