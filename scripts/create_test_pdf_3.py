from fpdf import FPDF

class PDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 10, "Documento de Prueba 3 - Trámites de Tránsito", 0, 1, "C")

    def chapter_title(self, title):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, title, 0, 1, "L")
        self.ln(4)

    def chapter_body(self, body):
        self.set_font("Helvetica", "", 12)
        self.multi_cell(0, 10, body)
        self.ln()

pdf = PDF()
pdf.add_page()

pdf.chapter_title("Guía para el pago de Partes de Tránsito")
pdf.chapter_body("Este documento explica cómo gestionar y pagar los partes de tránsito cursados en la comuna de La Cisterna.")

pdf.chapter_title("¿Cómo consultar un parte?")
pdf.chapter_body("- Puede consultar el estado de sus partes ingresando al portal de consulta del Registro Civil o directamente en nuestra web municipal ingresando su patente.\n- Las notificaciones llegan al domicilio registrado en el Registro Civil.")

pdf.chapter_title("Opciones de Pago")
pdf.chapter_body("- Pago en línea: A través de nuestra plataforma municipal usando tarjeta de crédito o débito.\n- Pago presencial: En el Juzgado de Policía Local, ubicado en Av. Pedro Aguirre Cerda 0101, de lunes a viernes de 08:30 a 14:00 horas.")

pdf.output("/home/aspen/Alcaldia_Practica/data/partes_transito_test.pdf")
print("PDF generado exitosamente en /home/aspen/Alcaldia_Practica/data/partes_transito_test.pdf")
