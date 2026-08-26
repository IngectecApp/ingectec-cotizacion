import flet as ft
import os

PORT = int(os.environ.get("PORT", 8080))

def main(page: ft.Page):
    # Configuraciones principales de la ventana
    page.title = "INGECTEC V300 - PREMIUM"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#1e293b" # Tu fondo original
    page.padding = 15
    page.scroll = ft.ScrollMode.AUTO # Clave para poder bajar con el dedo en el celular

    # --- 1. ENCABEZADO ---
    header = ft.Container(
        content=ft.Text("⚡ INGECTEC SAS", size=22, weight="bold", color="#fbbf24"),
        alignment=ft.alignment.center,
        padding=5
    )

    # --- 2. BOTONES SUPERIORES (Wrap para que se acomoden solos en móvil) ---
    botones_top = ft.Row([
        ft.ElevatedButton("➕ AÑADIR ÍTEM", bgcolor="#10b981", color="white"),
        ft.ElevatedButton("📦 BODEGA", bgcolor="#2563eb", color="white"),
        ft.ElevatedButton("👥 CLIENTES", bgcolor="#2563eb", color="white"),
        ft.ElevatedButton("🔍 HISTORIAL", bgcolor="#2563eb", color="white"),
        ft.ElevatedButton("✏️ EDITAR", bgcolor="#475569", color="white"),
        ft.ElevatedButton("🧹 LIMPIAR", bgcolor="#ef4444", color="white"),
    ], wrap=True, alignment=ft.MainAxisAlignment.CENTER)

    # --- 3. TABLA DE PROPUESTA (Responsiva) ---
    tabla = ft.Container(
        content=ft.Column([
            ft.Row([ft.Text("PROPUESTA ING 161", weight="bold", color="#fbbf24", size=16)], alignment=ft.MainAxisAlignment.CENTER),
            ft.Divider(color="white24"),
            ft.ResponsiveRow([
                ft.Text("DESCRIPCIÓN", weight="bold", color="#fbbf24", col={"sm": 6, "md": 6, "lg": 6}),
                ft.Text("CANT", weight="bold", color="#fbbf24", col={"sm": 3, "md": 3, "lg": 3}, text_align="center"),
                ft.Text("TOTAL", weight="bold", color="#fbbf24", col={"sm": 3, "md": 3, "lg": 3}, text_align="right"),
            ]),
            ft.Container(height=80), # Espacio temporal para los ítems
            ft.Row([ft.TextButton("❌ QUITAR SELECCIONADO", icon_color="#ef4444", style=ft.ButtonStyle(color="#ef4444"))], alignment=ft.MainAxisAlignment.CENTER)
        ]),
        bgcolor="#0f172a",
        padding=10,
        border_radius=8,
        border=ft.border.all(1, "white12")
    )

    # --- 4. FORMULARIO CLIENTE (100% Responsivo a 12 columnas) ---
    f_cli = ft.ResponsiveRow([
        ft.TextField(label="Buscar nombre de cliente...", col={"sm": 12, "md": 5, "lg": 5}),
        ft.TextField(label="NIT / C.C.", col={"sm": 6, "md": 4, "lg": 4}),
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

    # --- 6. BOTÓN GENERAR ---
    btn_generar = ft.Container(
        content=ft.ElevatedButton(
            "🚀 GENERAR PROPUESTA PROFESIONAL",
            bgcolor="#f59e0b",
            color="black",
            height=50,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=25))
        ),
        alignment=ft.alignment.center,
        padding=ft.padding.only(top=10, bottom=20)
    )

    # Cargar todo a la pantalla
    page.add(header, botones_top, tabla, f_cli, f_aiu, btn_generar)

ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=PORT, host="0.0.0.0")