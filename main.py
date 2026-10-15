class PDF(FPDF):  
    def rounded_rect(self, x, y, w, h, r, style='F'):  
        if style == 'F':  
            self.rect(x+r, y, w-2*r, h, style='F')
            self.rect(x, y+r, w, h-2*r, style='F')
            self.ellipse(x, y, 2*r, 2*r, style='F')
            self.ellipse(x+w-2*r, y, 2*r, 2*r, style='F')
            self.ellipse(x, y+h-2*r, 2*r, 2*r, style='F')
            self.ellipse(x+w-2*r, y+h-2*r, 2*r, 2*r, style='F')  
            
    def header(self):
        # 1. Buscamos la ruta absoluta del directorio donde está el script
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        except:
            base_dir = os.getcwd()

        # 2. Todas las combinaciones de rutas absolutas para atrapar el archivo sí o sí
        rutas_logos = [
            os.path.join(base_dir, "assets", "logopl.png"),
            os.path.join(base_dir, "logopl.png"),
            os.path.join(base_dir, "assets", "logo pl.png"),
            os.path.join(base_dir, "logo pl.png"),
            os.path.join(base_dir, "assets", "logo.png"),
            os.path.join(base_dir, "logo.png"),
            "assets/logopl.png", 
            "logopl.png"
        ]
        
        logo_cargado = False
        for ruta in rutas_logos:  
            if os.path.exists(ruta):  
                try: 
                    # w=190 es el ancho que ocupan los logos combinados en el encabezado
                    self.image(ruta, x=10, y=8, w=190)
                    logo_cargado = True
                    break   
                except Exception as e:
                    print(f"Error cargando el logo en la ruta {ruta}: {e}")
        
        # 3. Si no encuentra el logo, pintamos una alerta roja para saber qué está pasando
        if not logo_cargado:
            self.set_y(15)
            self.set_font('helvetica', 'B', 10)
            self.set_text_color(255, 0, 0)
            self.cell(0, 10, "ERROR: NO SE ENCUENTRA EL ARCHIVO DE IMAGEN 'logopl.png'", border=0, align='C')
            self.set_text_color(0, 0, 0) # Restauramos el color negro para el resto del texto

        self.set_y(40)   
        
    def footer(self):  
        self.set_y(-28)  
        if hasattr(self, 'asesor_nombre') and self.asesor_nombre:  
            self.set_font('helvetica', '', 7)
            self.set_text_color(210, 210, 210)
            self.set_x(30)
            self.cell(0, 3, f"Cod. Asesor: {self.asesor_nombre}", border=0, align='L')  
        self.set_y(-25); self.set_font('helvetica', '', 8); self.set_text_color(150, 150, 150); self.set_draw_color(200, 200, 200)  
        self.line(30, self.get_y(), 180, self.get_y()); self.ln(2)  
        self.cell(0, 4, "INGECTEC S.A.S: CALLE 2 N # 4-53 BELALCAZAR CELULAR: 317 504 64 04 - 3172736356", border=0, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)  
        self.cell(0, 4, "comercial@ingectec.com - gerencia@ingectec.com", border=0, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)  
        self.cell(0, 4, "WWW.INGECTEC.COM", border=0, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)  
        self.set_y(-10)
        self.cell(0, 4, f'Página {self.page_no()}', border=0, align='R')