import flet as ft
import sqlite3
import os

# Puerto dinámico asignado por Render
PORT = int(os.environ.get("PORT", 8080))

def main(page: ft.Page):
    page.title = "INGECTEC V300 - WEB"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 30
    page.scroll = ft.ScrollMode.AUTO

    # Título corporativo
    page.add(
        ft.Text("⚡ INGECTEC SAS - MÓDULO WEB", size=28, weight="bold", color=ft.colors.AMBER)
    )

    # Validar Base de Datos en la Nube
    db_status = "❌ Base de datos no encontrada."
    if os.path.exists("ingectec.db"):
        try:
            db = sqlite3.connect("ingectec.db")
            db.close()
            db_status = "✅ Base de datos SQLite conectada en la nube."
        except Exception as e:
            db_status = f"⚠️ Error al leer DB: {e}"

    page.add(ft.Text(db_status, color=ft.colors.GREEN if "✅" in db_status else ft.colors.RED))

    # Formulario Básico Web
    cliente_input = ft.TextField(label="Nombre del Cliente (Ej: JAVERIANA)", width=400)
    nit_input = ft.TextField(label="NIT / C.C.", width=200)

    def generar_pdf_web(e):
        # Aquí migraremos la lógica del PDF para que se descargue en el navegador
        page.snack_bar = ft.SnackBar(ft.Text(f"¡Cotización para {cliente_input.value} solicitada!"))
        page.snack_bar.open = True
        page.update()

    btn_generar = ft.ElevatedButton(
        "🚀 GENERAR PROPUESTA", 
        on_click=generar_pdf_web, 
        bgcolor=ft.colors.ORANGE, 
        color=ft.colors.BLACK,
        height=50
    )

    page.add(
        ft.Row([cliente_input, nit_input], wrap=True),
        ft.Container(height=20),
        btn_generar
    )

# Render arranca el servidor web en el puerto asignado
ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=PORT, host="0.0.0.0")