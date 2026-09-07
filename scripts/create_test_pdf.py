from fpdf import FPDF

class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, "Documento de Prueba - Municipalidad de La Cisterna", 0, 1, "C")

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

pdf.chapter_title("Reglamento de Becas Municipales 2026")
pdf.chapter_body("Este documento establece los lineamientos para la postulación a las becas de educación superior de la Ilustre Municipalidad de La Cisterna para el año 2026.")

pdf.chapter_title("Requisitos de Postulación")
pdf.chapter_body("- Residir en la comuna de La Cisterna (acreditado con certificado de domicilio).\n- Estar matriculado en una institución de educación superior reconocida por el Ministerio de Educación.\n- Tener un Registro Social de Hogares (RSH) con un tramo no superior al 70%.")

pdf.chapter_title("Documentación Necesaria")
pdf.chapter_body("- Certificado de alumno regular vigente.\n- Copia de la cédula de identidad.\n- Cartola del Registro Social de Hogares.")

pdf.chapter_title("Plazos")
pdf.chapter_body("El proceso de postulación se abre el 1 de marzo de 2026 y cierra el 30 de marzo de 2026, a las 14:00 horas.")

pdf.output("/home/aspen/Alcaldia_Practica/data/beca_test.pdf")
print("PDF generado exitosamente en /home/aspen/Alcaldia_Practica/data/beca_test.pdf")
