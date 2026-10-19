# Términos de Requerimiento Técnico y Financiero
## Adquisición de Servicio de API de Inteligencia Artificial Generativa (LLM) para Atención Vecinal 24/7
### Ilustre Municipalidad de La Cisterna — Proyecto Cisternin

---

| Campo | Detalle |
|---|---|
| **Destinatario** | Administración Municipal / Dirección de Finanzas / Jefatura de Informática |
| **Unidad Técnica** | Equipo de Desarrollo e Innovación Tecnológica (Proyecto Cisternin) |
| **Fecha** | Octubre de 2026 |
| **Objeto Único** | Contratación de consumo de API de Modelo de Lenguaje (LLM) empresarial |

---

## 1. Antecedentes y Estado Operativo del Sistema

La Municipalidad de La Cisterna dispone de la solución integral de Asistente Virtual Ciudadano (**"Cisternin"**), desarrollada y lista para su despliegue en producción. Toda la arquitectura técnica, plataformas de administración y base de conocimiento comunal ya se encuentran completamente construidas e integradas, **sin requerir inversión en desarrollo de software ni compras de equipamiento físico adicional ($0 CLP de desarrollo pendiente)**.

### Componentes ya operativos al 100%:
- **Motor conversacional RAG (FastAPI / Python)** con búsqueda semántica local de alta velocidad.
- **Base de datos vectorial municipal (ChromaDB)** con 583 fragmentos oficiales indexados (trámites, licencias, farmacia, veterinaria, Tarjeta Vecino, aseo, rentas y autoridades).
- **Portal público de atención ciudadana y widget web flotante** para inserción mediante una sola línea de código en `www.cisterna.cl`.
- **Panel de administración (`/admin`), portal de documentación y reportes en Excel (`/docs`)** y canal de derivación oficial a WhatsApp Municipal.
- **Túnel seguro de alta disponibilidad perimetral (Cloudflare Tunnel)**, sin abrir puertos en el firewall municipal.

---

## 2. Definición del Requerimiento: Servicio de Inteligencia Artificial

El **único componente** que se solicita adquirir es el **Servicio de API de Modelo de Lenguaje (LLM de grado empresarial)**, necesario para que el bot genere las respuestas conversacionales a los vecinos de forma ininterrumpida y con tiempo de respuesta inferior a 1,5 segundos.

### Especificaciones técnicas requeridas (Neutralidad Tecnológica - Ley 19.886):
1. **Protocolo de integración:** API estándar RESTful HTTPS (formato JSON entrada/salida).
2. **Capacidad y latencia:** Modelo fundacional optimizado de alta velocidad (Time to First Token < 1,5s).
3. **Ventana de contexto:** Mínimo 128.000 tokens para análisis integral de decretos y ordenanzas comunales.
4. **Privacidad y Seguridad (Ley N° 19.628):** El proveedor debe garantizar contractualmente que las consultas de los vecinos no son almacenadas ni utilizadas para el reentrenamiento de modelos públicos.
5. **Modelo de cobro:** Pago por uso exacto (*Pay-As-You-Go*) con control de gasto máximo mensual (*Budget Cap*).

---

## 3. Modelo de Costos y Presupuesto Solicitado

El costo real de cada interacción vecinal es sumamente bajo debido a la eficiencia del motor RAG municipal, que inyecta únicamente los fragmentos necesarios. El costo directo estimado es de apenas **$0,14 CLP por consulta ciudadana**.

| Concepto Financiero | Monto Mensual (CLP) | Monto Anual (CLP) | Proyección 2 Años (24m) |
|---|---|---|---|
| **Consumo Base Estimado (1.000 consultas/día)** | $4.275 CLP (~$4,50 USD) | $51.300 CLP | $102.600 CLP |
| **Presupuesto Solicitado (Techo Operativo)** | **$100.000 CLP** | **$1.200.000 CLP (1,2 M)** | **$2.400.000 CLP (2,4 M)** |
| **Capacidad de Atención Cubierta** | Hasta 701.750 consultas/mes | Hasta 8,4 Millones/año | Hasta 16,8 Millones |
| **Costo por Consulta Vecinal** | $0,14 CLP / consulta | $0,14 CLP / consulta | $0,14 CLP / consulta |

---

## 4. Justificación de la Asignación de $100.000 CLP/mes ($1,2 Millones/año)

Si el consumo base promedio para 1.000 atenciones diarias representa ~$4.275 CLP mensuales, se justifica solicitar un presupuesto de **$100.000 CLP mensuales ($1.200.000 CLP anuales)** por los siguientes motivos operativos y de gestión pública:

1. **Variabilidad por vecino:** Un vecino no siempre realiza una sola pregunta; comúnmente formula consultas sucesivas (3 a 8 preguntas) para resolver dudas de subsidios, requisitos vehiculares o licencias de conducir.
2. **Picos estacionales de alta demanda:** Durante períodos de alta afluencia (marzo por Permisos de Circulación, mayo por patentes comerciales), el tráfico municipal se multiplica hasta por cinco. El presupuesto asegura capacidad para más de 700.000 consultas mensuales sin interrupción.
3. **Garantía de Cero Caídas (Zero-Downtime):** Un crédito de $100.000 CLP/mes garantiza que el servicio nunca se suspenda por "cuota excedida" o límites de saldo gratuito.
4. **Eficiencia y protección del erario municipal:** Bajo el modelo *Pay-As-You-Go*, el municipio solo paga por las consultas efectivamente realizadas. Si en un mes se consumen $12.000 CLP, los $88.000 CLP restantes no se pierden ni se cobran, quedando resguardados por el límite mensual configurado.

---

## 5. Procedimiento Directo para la Puesta en Marcha

- **Paso 1:** Aprobación del requerimiento presupuestario de $100.000 CLP/mes ($1.200.000 CLP/año) para servicio de API de IA.
- **Paso 2:** Habilitación de la cuenta de nube municipal con límite de gasto (*Budget Cap*) configurado en $100.000 CLP/mes.
- **Paso 3:** Entrega de la credencial API al equipo técnico para su vinculación con el bot (proceso de 5 minutos).
- **Paso 4:** Inserción del widget en `www.cisterna.cl` y habilitación del servicio ciudadano 24/7.

---

**MATHIAS ARRIAGADA**  
Desarrollo e Innovación — Proyecto Cisternin  
Ilustre Municipalidad de La Cisterna
