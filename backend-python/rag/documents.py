"""
══════════════════════════════════════════════════════════════════
Chocolates Helena — Documentos de Conocimiento (RAG)
Base de conocimiento que se indexa en FAISS para el retriever.
Incluye: catálogo, FAQs, políticas de entrega, maridajes.
══════════════════════════════════════════════════════════════════
"""
from langchain_core.documents import Document

# ── Catálogo de Productos ─────────────────────────────────────────────────────

CATALOGO_DOCS = [
    Document(
        page_content="""
Trufa Negra Intenso — Precio: $45.000 COP
ID: trufa_negra
Descripción: Joya de la chocolatería helena. Elaborada con cacao peruano de San Martín al 70%,
cubierta con polvo de oro comestible. Notas a frutos secos, cereza y especias.
Ingredientes: Cacao 70% San Martín, manteca de cacao, azúcar mascabado, oro comestible.
Peso: 35g por unidad. Caja de 6 unidades disponible.
Maridaje: Café espresso, vino Malbec, whisky añejo.
Disponibilidad: En stock — 48 unidades.
""",
        metadata={"source": "catalogo", "product_id": "trufa_negra", "precio": 45000}
    ),
    Document(
        page_content="""
Bombón de Maracuyá — Precio: $38.000 COP
ID: bombon_maracuya
Descripción: Explosión tropical peruana. Ganache cremoso de maracuyá amazónico
envuelto en cobertura de chocolate con leche 45%. Fresco, ácido y equilibrado.
Ingredientes: Chocolate leche 45%, pulpa maracuyá amazónico, crema de leche, mantequilla.
Peso: 30g por unidad. Ideal para regalar en verano.
Maridaje: Champagne, té de frutas, jugo de fruta tropical.
Disponibilidad: En stock — 35 unidades.
""",
        metadata={"source": "catalogo", "product_id": "bombon_maracuya", "precio": 38000}
    ),
    Document(
        page_content="""
Tableta de Leche Premium — Precio: $32.000 COP
ID: tableta_leche
Descripción: Clásico renovado. Tableta de chocolate con leche peruano al 45%
con inclusión de caramelo salado artesanal hecho con sal de Maras (Cusco).
Ingredientes: Cacao Tumbes 45%, leche entera, caramelo artesanal, sal de Maras Cusco.
Peso: 80g por tableta. Textura suave y cremosa.
Maridaje: Leche caliente, caramelo, frutas secas.
Disponibilidad: En stock — 60 unidades.
""",
        metadata={"source": "catalogo", "product_id": "tableta_leche", "precio": 32000}
    ),
    Document(
        page_content="""
Chocolate Blanco con Rosa — Precio: $42.000 COP
ID: chocolate_blanco
Descripción: Delicadeza floral. Chocolate blanco peruano infusionado con pétalos de rosa
andina y compota de frambuesa. Único, romántico y sofisticado.
Ingredientes: Manteca cacao premium, leche entera, pétalos de rosa andina, frambuesa liofilizada.
Peso: 40g por unidad. Empaque especial para regalo.
Maridaje: Rosé, té de rosa, champagne blanco.
Disponibilidad: En stock — 22 unidades. Stock limitado.
""",
        metadata={"source": "catalogo", "product_id": "chocolate_blanco", "precio": 42000}
    ),
    Document(
        page_content="""
Caja de Regalo Especial — Precio: $120.000 COP
ID: caja_regalo
Descripción: La experiencia Helena completa. Selección de 20 piezas artesanales
representativas de toda la colección. Empaque de lujo con cinta dorada y tarjeta personalizada.
Contenido: 4 trufas negras, 4 bombones maracuyá, 4 tabletas leche, 4 chocolates blancos, 4 picantes.
Peso total: 600g aprox. Empaque premium regalo.
Maridaje: Champagne, vinos de postre, whisky premium.
Disponibilidad: En stock — 15 unidades. Ideal para cumpleaños, aniversarios y eventos.
""",
        metadata={"source": "catalogo", "product_id": "caja_regalo", "precio": 120000}
    ),
    Document(
        page_content="""
Chocolate Negro Picante — Precio: $36.000 COP
ID: chocolate_picante
Descripción: Para los aventureros del paladar. Cacao oscuro al 75% de Amazonas
con ají amarillo peruano y pimienta de cayena. Picor progresivo e intenso.
Ingredientes: Cacao Amazonas 75%, ají amarillo peruano, cayena, manteca de cacao.
Peso: 45g por unidad. No recomendado para niños.
Maridaje: Mezcal, cerveza artesanal oscura, ron añejo.
Disponibilidad: En stock — 30 unidades.
""",
        metadata={"source": "catalogo", "product_id": "chocolate_picante", "precio": 36000}
    ),
]

# ── FAQs ──────────────────────────────────────────────────────────────────────

FAQ_DOCS = [
    Document(
        page_content="""
¿Cuánto tiempo tarda la entrega?
El tiempo de entrega varía según la ciudad de destino:
- Lima (Miraflores, San Isidro, Surco, Barranco): 30-60 minutos
- Lima (distritos alejados como SJL, VES, Callao): 60-90 minutos
- Arequipa, Cusco, Trujillo: 24-48 horas (envío refrigerado)
- Otras ciudades del Perú: 48-72 horas
Todos los pedidos incluyen número de tracking en tiempo real.
""",
        metadata={"source": "faq", "tema": "entrega_tiempos"}
    ),
    Document(
        page_content="""
¿Cuál es el costo de envío?
El envío es GRATIS en todos los pedidos sin mínimo de compra.
No existen costos adicionales ni sorpresas. El precio mostrado incluye todo.
Para pedidos fuera de Lima, el envío se realiza en empaque refrigerado especial.
""",
        metadata={"source": "faq", "tema": "costo_envio"}
    ),
    Document(
        page_content="""
¿Qué métodos de pago aceptan?
Aceptamos:
- Tarjetas de crédito: Visa, Mastercard, American Express
- Tarjetas de débito: Visa Débito, Mastercard Débito
- Billeteras digitales: Yape, Plin (próximamente)
Tarjetas de prueba disponibles para demo:
- 4242 4242 4242 4242 → Aprobada siempre
- 4000 0000 0000 0002 → Rechazada (fondos insuficientes)
- 4000 0000 0000 9995 → Rechazada (tarjeta vencida)
""",
        metadata={"source": "faq", "tema": "metodos_pago"}
    ),
    Document(
        page_content="""
¿Los chocolates necesitan refrigeración?
Sí, los chocolates Helena deben conservarse entre 16°C y 20°C.
- Evitar exposición directa al sol o calor
- No refrigerar (el frío puede generar condensación y arruinar el brillo)
- Consumir preferentemente en los siguientes 30 días de la compra
- Mantener en lugar fresco y seco
Nuestros empaques están diseñados para mantener la temperatura óptima durante el delivery.
""",
        metadata={"source": "faq", "tema": "conservacion"}
    ),
    Document(
        page_content="""
¿Hacen pedidos personalizados o por mayor?
Sí, ofrecemos:
- Pedidos corporativos (mínimo 50 unidades): descuento del 15%
- Cajas personalizadas para bodas y eventos: consultar disponibilidad
- Talleres de chocolatería con el maestro chocolatero
- Packs de degustación para empresas
Para pedidos especiales escribir a: eventos@chocolateshelena.com
""",
        metadata={"source": "faq", "tema": "pedidos_especiales"}
    ),
    Document(
        page_content="""
¿Qué pasa si mi pedido llega dañado?
Chocolates Helena garantiza la calidad de todos sus productos.
Si recibes un producto dañado o diferente al pedido:
1. Toma una foto del producto y el empaque
2. Contáctanos en las primeras 2 horas de recibido
3. Enviamos reposición GRATIS el mismo día (si antes de las 5pm)
Correo: soporte@chocolateshelena.com
WhatsApp: +51 987 654 321
""",
        metadata={"source": "faq", "tema": "garantia"}
    ),
    Document(
        page_content="""
¿De dónde viene el cacao de Chocolates Helena?
Trabajamos directamente con familias cacaoteras de:
- San Martín (cacao CCN-51 fino de aroma): notas a frutos rojos y nuez
- Amazonas (cacao nativo): notas a madera, frutas tropicales y especias
- Tumbes (cacao de leche): cremoso, suave, dulce
- Cusco (cacao blanco): floral, delicado, único en el mundo
Trazabilidad garantizada: cada producto indica su origen específico.
Certificación orgánica en proceso (2026).
""",
        metadata={"source": "faq", "tema": "origen_cacao"}
    ),
]

# ── Políticas de Entrega ──────────────────────────────────────────────────────

POLITICAS_DOCS = [
    Document(
        page_content="""
Política de Devoluciones y Reembolsos:
- Cambios y devoluciones aceptados en las primeras 24 horas
- El producto debe estar sin abrir y en su empaque original
- Reembolso completo por error nuestro (producto incorrecto o dañado)
- Reembolso del 80% si el cliente decide no querer el producto
- No se aceptan devoluciones de productos personalizados
El proceso de reembolso tarda 3-5 días hábiles en la tarjeta original.
""",
        metadata={"source": "politicas", "tema": "devoluciones"}
    ),
    Document(
        page_content="""
Cobertura de Entrega:
Zona 1 (Lima Moderna): Miraflores, San Isidro, Surco, Barranco, La Molina, San Borja
- Entrega: 30-60 minutos | Costo: GRATIS

Zona 2 (Lima Norte/Sur): SJL, Los Olivos, Villa El Salvador, Chorrillos, Callao
- Entrega: 60-90 minutos | Costo: GRATIS

Zona 3 (Lima Provincias): Huacho, Cañete, Huaral
- Entrega: 2-3 horas | Costo: GRATIS (con empaque especial)

Zona 4 (Principales ciudades del Perú): Arequipa, Cusco, Trujillo, Piura, Chiclayo
- Entrega: 24-48 horas (servicio courier refrigerado) | Costo: GRATIS
""",
        metadata={"source": "politicas", "tema": "cobertura"}
    ),
    Document(
        page_content="""
Política de Privacidad y Seguridad de Datos:
- Datos del cliente cifrados con SSL/TLS 256 bits
- No almacenamos datos de tarjetas de crédito (tokenización)
- Datos de envío eliminados tras 90 días
- No compartimos información con terceros sin consentimiento
- Cumplimiento con Ley de Protección de Datos Personales del Perú (Ley 29733)
Para solicitar eliminación de datos: privacidad@chocolateshelena.com
""",
        metadata={"source": "politicas", "tema": "privacidad"}
    ),
]

# ── Maridajes y Experiencia ───────────────────────────────────────────────────

MARIDAJE_DOCS = [
    Document(
        page_content="""
Guía de Maridajes Chocolates Helena:

Chocolate Negro Intenso (70%+ cacao):
- Vinos tintos: Malbec, Cabernet Sauvignon, Shiraz
- Destilados: Whisky ahumado (Islay Scotch), Bourbon, Mezcal
- Cafés: Espresso, cold brew sin azúcar

Chocolate con Leche (40-55% cacao):
- Vinos: Pinot Noir joven, Rosé espumante
- Cervezas: Ale roja, Porter suave
- Infusiones: Chai latte, té negro con leche

Chocolate Blanco y Frutas:
- Vinos: Moscato, Riesling dulce, Champagne Blanc de Blancs
- Cocktails: Aperol Spritz, Bellini de durazno
- Tés: Rosa, jazmín, frutos rojos

Chocolate Picante:
- Mezcal añejo, Tequila reposado
- Cerveza artesanal IPA o Porter oscura
- Ron añejo con hielo
""",
        metadata={"source": "maridaje", "tema": "guia_maridaje"}
    ),
    Document(
        page_content="""
Historia y Filosofía de Chocolates Helena:
Fundada en 2018 en el corazón de Miraflores, Lima, por la maestra chocolatera
Elena Vargas Quispe, formada en Bélgica y apasionada por el cacao peruano.

Misión: Llevar el extraordinario cacao peruano al mundo, respetando a los
productores y utilizando técnicas artesanales que preservan la esencia del fruto.

Valores:
- Trazabilidad total: conocemos el nombre del agricultor detrás de cada tableta
- Comercio justo: pagamos 30% sobre el precio de mercado a nuestros cacaoteros
- Sin aditivos: nunca usamos grasas vegetales ni saborizantes artificiales
- Educación: talleres mensuales de chocolatería para el público

Premio Nacional de Gastronomía 2022 — Mejor Chocolatería Artesanal del Perú.
""",
        metadata={"source": "historia", "tema": "sobre_helena"}
    ),
]

# ── Consolidar todos los documentos ──────────────────────────────────────────

ALL_DOCUMENTS: list[Document] = (
    CATALOGO_DOCS
    + FAQ_DOCS
    + POLITICAS_DOCS
    + MARIDAJE_DOCS
)

def get_all_documents() -> list[Document]:
    """Retorna todos los documentos del knowledge base."""
    return ALL_DOCUMENTS

def get_documents_by_source(source: str) -> list[Document]:
    """Filtra documentos por fuente (catalogo, faq, politicas, maridaje, historia)."""
    return [doc for doc in ALL_DOCUMENTS if doc.metadata.get("source") == source]
