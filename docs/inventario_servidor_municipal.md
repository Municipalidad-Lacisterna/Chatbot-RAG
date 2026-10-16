---
titulo: "Inventario técnico y de compra — Servidor municipal para Cisternin"
tags:
  - servidor
  - whatsapp
  - produccion
  - municipalidad
fecha: 2026-09-04
estado: pendiente-envio
relacionado:
  - "[[requerimientos]]"
  - "[[dimensionamiento_servidor]]"
  - "[[presentacion_jefes]]"
---

# 📋 Inventario técnico y de compra — Servidor municipal para "Cisternin"

> [!info] Meta del documento
> Confirmar si el servidor de la municipalidad puede alojar el chatbot **Cisternin** (inteligencia artificial local + integración WhatsApp). Requisito de diseño: **soberanía total de datos** — la información municipal nunca sale del servidor.
>
> **Fecha de solicitud:** 4 de septiembre de 2026 · **Solicitado por:** [Nombre / Área] · **Plazo devolución:** [ej. 5 días hábiles — la verificación de Meta tarda 1-14 días]

**4 secciones:** **A)** características del servidor · **B)** accesos y red · **C)** recursos a gestionar/comprar · **D)** resumen de requisitos mínimos.

---

## SECCIÓN A — Características del servidor

| # | Campo | Valor a llenar | Mínimo recomendado | ¿Por qué? |
|---|-------|----------------|---------------------|-----------|
| A1 | **Sistema operativo** | | Linux — Ubuntu 22.04/24.04 LTS o Debian 12 | Ollama, Caddy y los servicios están optimizados para Linux |
| A2 | **GPU (tarjeta gráfica)** | | NVIDIA con **8GB+ VRAM** (ej. RTX 3060 12GB) | Corre Qwen2.5-VL-7B local: respuestas en 1-5s. Sin GPU, Qwen en CPU funciona pero lento (10-30s) |
| A3 | **RAM total** | | **16 GB** (32 GB ideal) | Modelo LLM + ChromaDB + embeddings + servidor web |
| A4 | **CPU** | | 4+ núcleos modernos (Intel i5 / Ryzen 5 o mejor) | Procesamiento de embeddings y consultas RAG |
| A5 | **Disco disponible** | | **50 GB SSD** libres | Modelo Qwen (~5-7 GB) + base vectorial + logs + backups |
| A6 | **¿Es máquina virtual o física?** | | Preferible física o VM con GPU dedicada | Si es VM compartida, el rendimiento varía |
| A7 | **¿Docker disponible?** | | Sí (o instalable) | Facilita el despliegue y aislamiento (opcional) |
| A8 | **Versión de Python** | | 3.10 o superior | Frameworks del bot lo requieren |
| A9 | **¿Ollama instalado?** | | No — se instalará | Es el runtime del modelo local |
| A10 | **¿Actualmente aloja otros servicios?** | | Listar cuáles | Para dimensionar recursos compartidos |

---

## SECCIÓN B — Accesos y red

| # | Campo | Valor a llenar | Mínimo recomendado | ¿Por qué? |
|---|-------|----------------|---------------------|-----------|
| B1 | **¿Acceso SSH?** | | Sí, con usuario **sudo** | Para instalar, actualizar y mantener el servicio |
| B2 | **¿IP pública fija o reenvío de puertos?** | | IP fija, o posibilidad de reenvío 80/443 | El webhook de WhatsApp necesita HTTPS entrante |
| B3 | **¿Salida a internet?** | | Sí | Para llamar a la API de WhatsApp y descargar el modelo |
| B4 | **¿Puertos 80/443 libres?** | | Sí (o posibilidad de abrirlos) | Caddy/Nginx genera el certificado HTTPS automáticamente |
| B5 | **¿Cloudflare tunnel disponible?** | | Sí como alternativa | Si no hay IP pública, se usa túnel saliente (sin abrir puertos) — igual de estable |
| B6 | **¿Firewall corporativo?** | | Con reglas para 80/443 | Meta valida la URL del webhook |
| B7 | **¿Política de backups del servidor?** | | Describir | El historial y la base vectorial deben respaldarse |

---

## SECCIÓN C — Recursos a gestionar / comprar por la municipalidad

| # | Recurso | Cantidad | Costo estimado | Gestión | Prioridad |
|---|---------|----------|----------------|---------|-----------|
| C1 | **Números de WhatsApp nuevos** — chips prepago SIN cuenta WhatsApp vinculada (números limpios) | **2** (1 bot + 1 respaldo/pruebas) | CLP 5.000–15.000 c/u | Comprar y entregar los 2 SIMS | 🔴 URGENTE |
| C2 | **Dominio / subdominio** (ej. `bot.cisterna.cl`) | 1 | Ya existe (según lo conversado) | Pedir acceso para configurar DNS + HTTPS | 🔴 URGENTE |
| C3 | **Verificación de negocio en Meta** | — | $0 | Documentos: RUT, escritura de constitución, boleta de servicios | ⏳ CRÍTICO — **1-14 días hábiles** |
| C4 | **Tarjeta de pago para Meta Billing** | 1 | $0 (solo respaldo de facturación) | Registrar **antes del 30 sep 2026** o se corta la entrega de mensajes | ⏳ CRÍTICO |
| C5 | **Documentos reales del municipio** (PDFs/MD de trámites y normas) | Según existan | $0 | Compartir carpeta Drive o entregar archivos | Alta (después del setup) |

---

## SECCIÓN D — Resumen de requisitos mínimos (checklist rápido)

> [!warning] Requisitos para que el bot funcione
> - [ ] **Linux** (Ubuntu/Debian) o disposición a WSL2/Docker si es Windows
> - [ ] **Acceso SSH** con permisos de instalación (`sudo`)
> - [ ] **Salida a internet** + HTTPS entrante (puertos 80/443) **o** Cloudflare tunnel
> - [ ] **50 GB libres** de disco y **16 GB RAM** recomendado
> - [ ] **GPU 8GB+** deseable (no bloqueante: CPU funciona para el piloto)
> - [ ] **2 números WhatsApp** nuevos y limpios
> - [ ] **Acceso al dominio** existente (DNS)
> - [ ] **Persona responsable** que gestione Meta Business (verificación + tarjeta de pago)

---
