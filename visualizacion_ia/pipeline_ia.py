"""
Visualización animada del pipeline de IA del Chatbot Cisternin.
Muestra las 3 capas de comprensión y el flujo de datos completo.

Correr: manim -pql pipeline_ia.py PipelineCompleto
  (-p = preview, -ql = quality low para rápido, -qm = medium, -qh = high)
"""
from manim import *
import numpy as np


# ── Paleta de colores del proyecto ──
COLOR_FONDO = "#0a0a1a"
COLOR_PRIMARIO = "#25D366"    # Verde WhatsApp / Cisternin
COLOR_SECUNDARIO = "#128C7E"  # Verde oscuro
COLOR_ACENTO = "#FFD700"      # Dorado
COLOR_TEXTO = "#FFFFFF"
COLOR_CAPA1 = "#4FC3F7"       # Azul claro (normalización)
COLOR_CAPA2 = "#FF8A65"       # Naranja (intención)
COLOR_CAPA3 = "#AED581"       # Verde claro (retrieval)
COLOR_LLM = "#CE93D8"         # Lila (LLM)
COLOR_NODO_BASE = "#1E1E2E"   # Gris oscuro
COLOR_FLECHA = "#607D8B"      # Gris azulado


class PipelineCompleto(Scene):
    """
    Escena principal: grafo animado del pipeline de IA.
    Muestra cómo una pregunta del vecino fluye por las 3 capas
    hasta convertirse en una respuesta.
    """
    def construct(self):
        self.camera.background_color = COLOR_FONDO

        # ════════════════════════════════════════════
        # 1. TÍTULO
        # ════════════════════════════════════════════
        titulo = Text("Chatbot Cisternin", font_size=48, color=COLOR_PRIMARIO)
        subtitulo = Text("Pipeline de Comprensión IA", font_size=24, color=COLOR_TEXTO)
        subtitulo.next_to(titulo, DOWN, buff=0.3)

        self.play(Write(titulo), run_time=1.5)
        self.play(FadeIn(subtitulo, shift=UP * 0.3), run_time=0.8)
        self.wait(1)
        self.play(FadeOut(titulo), FadeOut(subtitulo), run_time=0.6)

        # ════════════════════════════════════════════
        # 2. NODOS DEL PIPELINE (de arriba a abajo)
        # ════════════════════════════════════════════

        # --- Fila 0: Entrada ---
        nodo_entrada = self._crear_nodo(
            "💬 Pregunta del Vecino", COLOR_PRIMARIO,
            subtexto='"pa la receta de la farmacia"'
        )
        nodo_entrada.move_to(UP * 3.0)

        # --- Fila 1: Capa 1 ---
        capa1_titulo = Text("CAPA 1", font_size=14, color=COLOR_CAPA1)
        capa1_titulo.move_to(UP * 1.8 + LEFT * 4.5)
        nodo_normalizar = self._crear_nodo(
            "🔤 Normalización", COLOR_CAPA1,
            subtexto="tildes · errores · modismos"
        )
        nodo_normalizar.move_to(UP * 1.8)

        # --- Fila 2: Capa 2 ---
        capa2_titulo = Text("CAPA 2", font_size=14, color=COLOR_CAPA2)
        capa2_titulo.move_to(UP * 0.4 + LEFT * 4.5)
        nodo_intencion = self._crear_nodo(
            "🎯 Detección de Intención", COLOR_CAPA2,
            subtexto="qué quiere + entidades + urgencia"
        )
        nodo_intencion.move_to(UP * 0.4)

        # --- Fila 3: Capa 3 (Retrieval) ---
        capa3_titulo = Text("CAPA 3", font_size=14, color=COLOR_CAPA3)
        capa3_titulo.move_to(DOWN * 1.0 + LEFT * 4.5)
        nodo_retrieval = self._crear_nodo(
            "🔍 Retrieval ChromaDB", COLOR_CAPA3,
            subtexto="183 chunks · embedding semántico"
        )
        nodo_retrieval.move_to(DOWN * 1.0)

        # --- Fila 4: LLM ---
        nodo_llm = self._crear_nodo(
            "🧠 LLM (Qwen/Gemini)", COLOR_LLM,
            subtexto="respuesta estructurada JSON"
        )
        nodo_llm.move_to(DOWN * 2.4)

        # --- Fila 5: Salida ---
        nodo_salida = self._crear_nodo(
            "✅ Respuesta al Vecino", COLOR_PRIMARIO,
            subtexto="un solo bloque · sin alucinaciones"
        )
        nodo_salida.move_to(DOWN * 3.8)

        # ════════════════════════════════════════════
        # 3. FLECHAS ANIMADAS
        # ════════════════════════════════════════════
        flechas = []
        nodos = [nodo_entrada, nodo_normalizar, nodo_intencion,
                 nodo_retrieval, nodo_llm, nodo_salida]

        for i in range(len(nodos) - 1):
            origen = nodos[i].get_bottom()
            destino = nodos[i + 1].get_top()
            flecha = Arrow(
                origen, destino,
                color=COLOR_FLECHA,
                buff=0.15,
                stroke_width=3,
                max_tip_length_to_length_ratio=0.15,
            )
            flechas.append(flecha)

        # ════════════════════════════════════════════
        # 4. BLOQUES LATERALES (cortos-circuitos)
        # ════════════════════════════════════════════
        cortos_circuitos = VGroup(
            Text("⚡ Cortocircuitos:", font_size=14, color=COLOR_ACENTO),
            Text("  Identidad · Sensibles", font_size=12, color=GRAY),
            Text("  Easter Eggs · Despedidas", font_size=12, color=GRAY),
            Text("  Groserías · Rate Limit", font_size=12, color=GRAY),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        cortos_circuitos.move_to(RIGHT * 4.5 + UP * 0.8)

        # Conector de cortocircuitos
        flecha_cc = Arrow(
            nodo_normalizar.get_right() + RIGHT * 0.1,
            cortos_circuitos.get_left() + LEFT * 0.1,
            color=COLOR_ACENTO,
            buff=0.1,
            stroke_width=2,
            stroke_opacity=0.6,
        )

        # ════════════════════════════════════════════
        # 5. ANIMACIÓN SECUENCIAL
        # ════════════════════════════════════════════

        # Aparece la entrada
        self.play(FadeIn(nodo_entrada, shift=DOWN * 0.5), run_time=0.8)
        self.wait(0.5)

        # Capa 1: Normalización
        self.play(
            Create(flechas[0]),
            FadeIn(capa1_titulo, shift=LEFT * 0.5),
            run_time=0.6
        )
        self.play(FadeIn(nodo_normalizar, shift=DOWN * 0.3), run_time=0.8)
        self.wait(0.5)

        # Cortocircuitos aparecen
        self.play(
            Create(flecha_cc),
            FadeIn(cortos_circuitos, shift=RIGHT * 0.3),
            run_time=0.6
        )
        self.wait(0.5)

        # Capa 2: Intención
        self.play(
            Create(flechas[1]),
            FadeIn(capa2_titulo, shift=LEFT * 0.5),
            run_time=0.6
        )
        self.play(FadeIn(nodo_intencion, shift=DOWN * 0.3), run_time=0.8)
        self.wait(0.5)

        # Capa 3: Retrieval
        self.play(
            Create(flechas[2]),
            FadeIn(capa3_titulo, shift=LEFT * 0.5),
            run_time=0.6
        )
        self.play(FadeIn(nodo_retrieval, shift=DOWN * 0.3), run_time=0.8)
        self.wait(0.5)

        # LLM
        self.play(Create(flechas[3]), run_time=0.6)
        self.play(FadeIn(nodo_llm, shift=DOWN * 0.3), run_time=0.8)
        self.wait(0.5)

        # Salida
        self.play(Create(flechas[4]), run_time=0.6)
        self.play(FadeIn(nodo_salida, shift=DOWN * 0.3), run_time=0.8)
        self.wait(1)

        # ════════════════════════════════════════════
        # 6. FLUJO DE DATOS ANIMADO (punto que viaja)
        # ════════════════════════════════════════════
        punto = Dot(color=COLOR_ACENTO, radius=0.12)
        punto.move_to(nodo_entrada.get_bottom())

        self.play(FadeIn(punto), run_time=0.3)

        for flecha in flechas:
            self.play(
                MoveAlongPath(punto, flecha),
                run_time=0.7,
                rate_func=smooth,
            )

        # El punto desaparece en la salida
        self.play(FadeOut(punto), run_time=0.3)
        self.wait(1.5)

        # ════════════════════════════════════════════
        # 7. LIMPIEZA Y ESTADÍSTICAS
        # ════════════════════════════════════════════
        todo = Group(*self.mobjects)
        self.play(FadeOut(todo), run_time=0.8)

        stats = VGroup(
            Text("Resultados", font_size=36, color=COLOR_PRIMARIO),
            Text("3 Capas de Comprensión", font_size=20, color=COLOR_CAPA1),
            Text("20+ Trámites con Sinónimos", font_size=20, color=COLOR_CAPA2),
            Text("183 Chunks Indexados", font_size=20, color=COLOR_CAPA3),
            Text("10/10 Batería de Pruebas", font_size=20, color=COLOR_LLM),
            Text("0 Dependencias Externas", font_size=20, color=COLOR_ACENTO),
        ).arrange(DOWN, buff=0.3)
        stats.move_to(ORIGIN)

        self.play(FadeIn(stats, shift=UP * 0.5), run_time=1)
        self.wait(2)
        self.play(FadeOut(stats), run_time=0.8)

        # ════════════════════════════════════════════
        # 8. CRÉDITOS
        # ════════════════════════════════════════════
        creditos = VGroup(
            Text("Cisternin", font_size=42, color=COLOR_PRIMARIO),
            Text("Municipalidad de La Cisterna", font_size=20, color=COLOR_TEXTO),
            Text("Comprensión IA · Capas 1-2-3", font_size=16, color=GRAY),
        ).arrange(DOWN, buff=0.3)

        self.play(FadeIn(creditos, shift=UP * 0.3), run_time=1)
        self.wait(2)
        self.play(FadeOut(creditos), run_time=0.8)

    def _crear_nodo(self, titulo: str, color: str, subtexto: str = "") -> VGroup:
        """Crea un nodo visual con título y opcionalmente subtexto."""
        rect = RoundedRectangle(
            corner_radius=0.15,
            width=4.5,
            height=0.7 if not subtexto else 0.9,
            fill_color=COLOR_NODO_BASE,
            fill_opacity=0.9,
            stroke_color=color,
            stroke_width=2,
        )
        txt = Text(titulo, font_size=18, color=color)
        txt.move_to(rect.get_center() + UP * 0.15 if subtexto else ORIGIN)

        grupo = VGroup(rect, txt)

        if subtexto:
            sub = Text(subtexto, font_size=11, color=GRAY)
            sub.move_to(rect.get_center() + DOWN * 0.2)
            grupo.add(sub)

        return grupo


class FlujoDatos(Scene):
    """
    Escena corta: animación del grafo de nodos con datos fluyendo.
    Ideal para redes sociales (15-20 segundos).
    """
    def construct(self):
        self.camera.background_color = COLOR_FONDO

        # Título rápido
        title = Text("¿Cómo entiende tu pregunta?", font_size=32, color=COLOR_PRIMARIO)
        title.to_edge(UP, buff=0.5)
        self.play(Write(title), run_time=0.8)

        # 3 columnas: Pregunta → Capas → Respuesta
        col_izq = VGroup(
            Text("💬", font_size=40),
            Text("pa la receta", font_size=16, color=GRAY),
        ).arrange(DOWN, buff=0.2)
        col_izq.move_to(LEFT * 4.5)

        col_center = VGroup(
            Text("A1", font_size=20, color=COLOR_CAPA1),
            Text("pa la receta\nfarmacia comunal\nreceta medica", font_size=11, color=COLOR_CAPA1),
            Text("↓", font_size=16, color=GRAY),
            Text("A2", font_size=20, color=COLOR_CAPA2),
            Text("intención: acceder\nentidad: salud", font_size=11, color=COLOR_CAPA2),
            Text("↓", font_size=16, color=GRAY),
            Text("A3", font_size=20, color=COLOR_CAPA3),
            Text("retrieval: 3 chunks\nrelevantes", font_size=11, color=COLOR_CAPA3),
        ).arrange(DOWN, buff=0.1)

        col_der = VGroup(
            Text("✅", font_size=40),
            Text("Farmacia Comunal\nPedro Aguirre Cerda\nNº0101, 1° piso\nCédula + receta", font_size=13, color=COLOR_PRIMARIO),
        ).arrange(DOWN, buff=0.2)
        col_der.move_to(RIGHT * 4.5)

        # Animar entrada
        self.play(FadeIn(col_izq, shift=LEFT * 0.5), run_time=0.6)
        self.wait(0.3)

        # Flecha izq → centro
        f1 = Arrow(col_izq.get_right(), col_center.get_left() + LEFT * 0.3,
                    color=COLOR_FLECHA, buff=0.2, stroke_width=2)
        self.play(Create(f1), FadeIn(col_center), run_time=1)

        # Flecha centro → der
        f2 = Arrow(col_center.get_right() + RIGHT * 0.3, col_der.get_left(),
                    color=COLOR_FLECHA, buff=0.2, stroke_width=2)
        self.play(Create(f2), FadeIn(col_der, shift=RIGHT * 0.5), run_time=1)

        self.wait(2)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.8)


class GrafoConocimiento(Scene):
    """
    Grafo de conocimiento: muestra los trámites como nodos conectados.
    """
    def construct(self):
        self.camera.background_color = COLOR_FONDO

        title = Text("Grafo de Conocimiento Municipal", font_size=32, color=COLOR_PRIMARIO)
        title.to_edge(UP, buff=0.4)
        self.play(Write(title), run_time=0.8)

        # Nodos de trámites (posiciones circulares)
        tramites = [
            ("💊 Farmacia", COLOR_CAPA1),
            ("📋 Ficha Social", COLOR_CAPA1),
            ("🐕 Veterinaria", COLOR_CAPA2),
            ("🚗 Permiso", COLOR_CAPA2),
            ("📄 Licencia", COLOR_CAPA3),
            ("🏠 Edificación", COLOR_CAPA3),
            ("🏪 Patente", COLOR_LLM),
            ("🐛 Plagas", COLOR_LLM),
            ("🌳 Arbolado", COLOR_ACENTO),
            ("📚 Subsidios", COLOR_ACENTO),
        ]

        nodos_grafo = []
        angulo_step = TAU / len(tramites)
        radio = 2.5

        for i, (label, color) in enumerate(tramites):
            angulo = angulo_step * i - PI / 2
            pos = np.array([
                radio * np.cos(angulo),
                radio * np.sin(angulo),
                0
            ])
            nodo = self._crear_nodo_grafo(label, color)
            nodo.move_to(pos)
            nodos_grafo.append(nodo)

        # Conexiones (cada nodo conectado con los 2 más cercanos)
        conexiones = VGroup()
        for i in range(len(nodos_grafo)):
            for j in [i + 1, i + 2]:
                if j < len(nodos_grafo):
                    linea = Line(
                        nodos_grafo[i].get_center(),
                        nodos_grafo[j].get_center(),
                        color=COLOR_FLECHA,
                        stroke_width=1,
                        stroke_opacity=0.3,
                    )
                    conexiones.add(linea)

        # Centro del grafo
        centro = Text("CISTERNIN", font_size=18, color=COLOR_PRIMARIO)
        centro.move_to(ORIGIN)

        # Animar
        self.play(FadeIn(conexiones), run_time=0.8)

        for nodo in nodos_grafo:
            self.play(FadeIn(nodo, scale=0.5), run_time=0.2)

        self.play(FadeIn(centro, scale=1.5), run_time=0.6)
        self.wait(2)

        # Highlight de un nodo (farmacia)
        highlight = SurroundingRectangle(
            nodos_grafo[0], color=COLOR_ACENTO, buff=0.15, stroke_width=3
        )
        self.play(Create(highlight), run_time=0.5)
        self.wait(1)
        self.play(FadeOut(highlight), run_time=0.3)

        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.8)

    def _crear_nodo_grafo(self, label: str, color: str) -> VGroup:
        rect = RoundedRectangle(
            corner_radius=0.1,
            width=2.2,
            height=0.6,
            fill_color=COLOR_NODO_BASE,
            fill_opacity=0.9,
            stroke_color=color,
            stroke_width=2,
        )
        txt = Text(label, font_size=13, color=color)
        txt.move_to(rect)
        return VGroup(rect, txt)
