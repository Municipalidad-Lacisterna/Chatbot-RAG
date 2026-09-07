from fpdf import FPDF

class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, "Documento de Prueba 2 - Municipalidad de La Cisterna", 0, 1, "C")

    def chapter_title(self, title):
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, title, 0, 1, "L")
        self.ln(4)

    def chapter_body(self, body):
        self.set_font("Arial", "", 12)
        self.multi_cell(0, 10, body)
        self.ln()

pdf = PDF()
pdf.add_page()

pdf.chapter_title("Política de Privacidad y Atención al Ciudadano 2026")
pdf.chapter_body("Este documento rige cómo la municipalidad gestiona los datos personales de los ciudadanos.")

pdf.chapter_title("Canales de Atención")
pdf.chapter_body("- Atención Virtual: Videollamada a través del sitio web oficial.\n- Oficina Presencial: Pedro Aguirre Cerda Nº 0101, 1er piso.")

pdf.chapter_title("Compromiso de Privacidad")
pdf.chapter_body("Toda información entregada a través de nuestros canales digitales será tratada con confidencialidad absoluta.")

pdf.output("/home/aspen/Alcaldia_Practica/data/privacidad_test.pdf")
print("PDF generado exitosamente en /home/aspen/Alcaldia_Practica/data/privacidad_test.pdf")
