"""Generate the synthetic sample packages for the CDF 2025 call.

    uv run python scripts/make_cdf_samples.py
    uv run python scripts/make_cdf_samples.py --with-oversize   # adds the >4 MB case

Every package is written from one base proposal plus a single named mutation, so
the only difference between `good/` and any `broken-*/` is the defect itself. If
two things differed, a failing test would not tell you which one caused it.

NOTHING HERE IS REAL. The people, the institutions and the project do not exist,
and every generated page carries a banner saying so. A real application is
personal data and never enters this repository — see .gitignore and manual §4.

The oracle (expected_findings.json) is written from the same mutation table that
produces the PDFs, so the two cannot drift apart.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import pymupdf
from reportlab import rl_config
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

rl_config.invariant = 1          # fixed PDF ids and dates: regenerating is a no-op in git

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "samples" / "cdf-2025"

BANNER = (
    "DOCUMENTO SINTÉTICO — datos ficticios generados para pruebas automatizadas. "
    "No corresponde a ninguna persona, institución ni proyecto real."
)

# Caps from Convocatoria §III. Duplicated here only so the generator can assert
# that `good` really is inside them; the rule pack remains the single source.
CAPS = {
    "Individual": {"total": 1_250_000, "etapas": [250_000, 500_000, 500_000]},
    "Grupo de investigación": {"total": 2_000_000, "etapas": [400_000, 800_000, 800_000]},
}

RESUMEN_POOL = [
    ("El proyecto estudia la dinámica de los ensambles microbianos del suelo en zonas "
    "semiáridas sometidas a estrés hídrico recurrente."),
    ("Se plantea caracterizar la composición taxonómica y funcional de dichos ensambles "
    "mediante secuenciación de marcadores ribosomales y metagenómica dirigida."),
    ("La metodología combina muestreo estacional en tres sitios contrastantes, "
    "experimentos de exclusión de lluvia y análisis de redes de coocurrencia."),
    ("La relevancia del trabajo radica en que los suelos semiáridos cubren una fracción "
    "considerable del territorio nacional y su respuesta a la sequía permanece poco descrita."),
    ("Los resultados esperados incluyen un catálogo de taxones indicadores y un modelo "
    "predictivo de la pérdida de función microbiana ante escenarios de menor "
    "precipitación."),
    ("El proyecto se articula con las capacidades instaladas de la institución beneficiaria "
    "y con la formación de personal especializado en ecología microbiana."),
]

PROTOCOLO_POOL = [
    ("Los suelos semiáridos del norte del país sostienen comunidades microbianas cuya "
    "estructura responde de manera no lineal a la disponibilidad de agua."),
    ("Trabajos previos han documentado desplazamientos en la abundancia relativa de "
    "Actinobacteria y Proteobacteria bajo regímenes de sequía prolongada."),
    ("Sin embargo, la relación entre esos desplazamientos y la pérdida de funciones "
    "edáficas concretas no ha sido establecida para los sitios considerados."),
    ("El presente protocolo describe el diseño experimental, los procedimientos de "
    "muestreo y los análisis estadísticos previstos para cada una de las etapas."),
    ("Se detallan asimismo los riesgos identificados y las estrategias de prevención "
    "correspondientes, así como los criterios de calidad aplicables a las secuencias obtenidas."),
]


def exactly_n_words(pool: list[str], n: int) -> str:
    """A paragraph of exactly n words. The count is what the fixture is for."""
    words: list[str] = []
    i = 0
    while len(words) < n:
        words.extend(pool[i % len(pool)].split())
        i += 1
    text = " ".join(words[:n])
    return text.rstrip(".,;") + "."


# --------------------------------------------------------------------------
# The base proposal. Everything below is a mutation of this.
# --------------------------------------------------------------------------

def base_proposal() -> dict:
    return {
        "numero": "CDF-2025-004112",
        "titulo": (
            "Dinámica de ensambles microbianos en suelos semiáridos del norte de México "
            "bajo estrés hídrico recurrente"
        ),
        "area": "2. Biología y Química",
        "modalidad": "Individual",
        "finalizada": "22 de abril de 2025, 18:42 horas (Ciudad de México)",
        "estado_solicitud": "FINALIZADA",
        "institucion": "Universidad Autónoma del Norte Semiárido (UANS)",
        "resumen_words": 468,
        "responsable_tecnica": {
            "nombre": "Dra. Rosalba Argüelles Mendieta",
            "cvu": "118204",
            "adscripcion": "Universidad Autónoma del Norte Semiárido (UANS)",
        },
        "responsable_administrativa": {
            "nombre": "Mtro. Joaquín Rentería Padilla",
            "cvu": "204117",
            "adscripcion": "Universidad Autónoma del Norte Semiárido (UANS)",
        },
        "representante_legal": {
            "nombre": "Dr. Efraín Castellanos Ibarra",
            "cvu": "090512",
            "cargo": "Secretario de Investigación y Posgrado, UANS",
        },
        "participantes": [
            {
                "nombre": "Dra. Rosalba Argüelles Mendieta",
                "cvu": "118204",
                "adscripcion": "Universidad Autónoma del Norte Semiárido (UANS)",
            },
            {
                "nombre": "Dr. Ignacio Peralta Vázquez",
                "cvu": "133902",
                "adscripcion": "Universidad Autónoma del Norte Semiárido (UANS)",
            },
        ],
        "etapas": [
            {"numero": 1, "ejercicio": 2025, "meta":
             "Establecimiento de los tres sitios de muestreo y obtención de la línea "
             "base microbiana (al menos 120 muestras procesadas)."},
            {"numero": 2, "ejercicio": 2026, "meta":
             "Secuenciación y ensamblaje de 240 bibliotecas; entrega del catálogo "
             "preliminar de taxones indicadores."},
            {"numero": 3, "ejercicio": 2027, "meta":
             "Modelo predictivo validado con los datos de exclusión de lluvia; envío "
             "de un artículo a revista mexicana de acceso abierto."},
        ],
        "presupuesto": [
            # rubro, etapa1, etapa2, etapa3
            ("Honorarios por servicios profesionales", 120_000, 120_000, 120_000),
            ("Materiales y suministros de laboratorio", 68_000, 142_000, 139_000),
            ("Trabajo de campo", 34_000, 86_000, 81_000),
            ("Pasajes y viáticos nacionales", 16_000, 47_000, 44_000),
            ("Equipo de laboratorio (gasto de inversión)", 0, 92_000, 96_000),
            ("Impresión y elaboración de material informativo", 10_000, 8_000, 12_000),
        ],
        "presupuesto_desglosado": True,
        "entregables": {
            "articulo":
                "Un artículo publicado o aceptado en la revista mexicana de acceso "
                "abierto Revista Latinoamericana de Ecología del Suelo.",
            "difusion":
                "Una actividad de difusión: ponencia en el Congreso Nacional de "
                "Ciencias del Suelo.",
            "divulgacion":
                "Una actividad de divulgación dirigida a bachillerato, con lenguaje "
                "incluyente y no estereotipado.",
            "formacion_hcti":
                "Formación de dos personas en capacidades HCTI a nivel maestría.",
        },
        "evaluadores": [
            {"nombre": "Dra. Amparo Quintanilla Ocampo",
             "adscripcion": "Instituto Regional de Ciencias Biológicas (IRCB)"},
            {"nombre": "Dr. Serafín Olmedo Rivas",
             "adscripcion": "Centro de Estudios del Altiplano (CEA)"},
            {"nombre": "Dra. Leticia Bustamante Arocha",
             "adscripcion": "Universidad del Golfo Oriental (UGO)"},
        ],
        "documents": ["solicitud", "protocolo", "carta_postulacion"],
        "protocolo_encabezado": True,     # header carries número + título
        "protocolo_pages": 6,
        "protocolo_padding_kb": 0,
    }


# --------------------------------------------------------------------------
# Mutations. One package, one defect, one list of rule ids it should raise.
# --------------------------------------------------------------------------

def m_resumen_largo(p):
    p["resumen_words"] = 612


def m_sin_carta(p):
    p["documents"].remove("carta_postulacion")


def m_sin_protocolo(p):
    p["documents"].remove("protocolo")


def m_protocolo_sin_encabezado(p):
    p["protocolo_encabezado"] = False


def m_sin_hcti(p):
    del p["entregables"]["formacion_hcti"]


def m_articulo_internacional(p):
    p["entregables"]["articulo"] = (
        "Un artículo publicado o aceptado en la revista internacional Soil Biology & "
        "Biochemistry (Elsevier)."
    )


def m_cronograma_incompleto(p):
    p["etapas"][2]["meta"] = ""


def m_presupuesto_sin_desglose(p):
    p["presupuesto_desglosado"] = False


def m_en_captura(p):
    p["estado_solicitud"] = "EN CAPTURA"
    p["finalizada"] = "— (la solicitud no ha sido finalizada)"


def m_protocolo_pesado(p):
    p["protocolo_padding_kb"] = 4_400


def m_mala(p):
    """The realistic disaster: a group proposal with twelve things wrong."""
    p["numero"] = "CDF-2025-007431"
    p["modalidad"] = "Grupo de investigación"
    p["titulo"] = (
        "Red interinstitucional para el estudio de la degradación de suelos agrícolas "
        "en el altiplano"
    )
    p["institucion"] = "Instituto Regional de Ciencias Biológicas (IRCB)"
    p["responsable_tecnica"] = {
        "nombre": "Dr. Fausto Villaseñor Lugo",
        "cvu": "221806",
        "adscripcion": "Instituto Regional de Ciencias Biológicas (IRCB)",
    }
    # R-CDF-RA-DISTINTA-RT: the same person in both roles.
    p["responsable_administrativa"] = dict(p["responsable_tecnica"])
    # R-CDF-GRUPO-MIN-3 and R-CDF-GRUPO-DOS-INSTITUCIONES: two people, one institution.
    p["participantes"] = [
        {"nombre": "Dr. Fausto Villaseñor Lugo", "cvu": "221806",
         "adscripcion": "Instituto Regional de Ciencias Biológicas (IRCB)"},
        {"nombre": "Dra. Hortensia Maldonado Sierra", "cvu": "198430",
         "adscripcion": "Instituto Regional de Ciencias Biológicas (IRCB)"},
    ]
    # R-CDF-RESUMEN-500
    p["resumen_words"] = 612
    # R-CDF-EVALUADORES-MIN-3 and R-CDF-EVALUADORES-SIN-ADSCRIPCION
    p["evaluadores"] = [
        {"nombre": "Dra. Amparo Quintanilla Ocampo",
         "adscripcion": "Instituto Regional de Ciencias Biológicas (IRCB)"},
        {"nombre": "Dr. Serafín Olmedo Rivas",
         "adscripcion": "Centro de Estudios del Altiplano (CEA)"},
    ]
    # R-CDF-MONTO-MAXIMO (2,160,000 > 2,000,000), R-CDF-MONTO-POR-ETAPA
    # (etapa 1 = 610,000 > 400,000 — and ONLY etapa 1, so every rule in this
    # package fires exactly once and the oracle can be compared as a multiset),
    # R-CDF-HONORARIOS-30 (36.6%), R-CDF-RUBROS-NO-FINANCIABLES.
    p["presupuesto"] = [
        ("Honorarios por servicios profesionales", 240_000, 280_000, 270_000),
        ("Sueldos y salarios del personal académico participante", 90_000, 90_000, 90_000),
        ("Materiales y suministros de laboratorio", 180_000, 205_000, 190_000),
        ("Trabajo de campo", 60_000, 115_000, 105_000),
        ("Equipo de laboratorio (gasto de inversión)", 40_000, 100_000, 95_000),
    ]
    # R-CDF-ENTREGABLES-MINIMOS and R-CDF-ARTICULO-NACIONAL
    del p["entregables"]["formacion_hcti"]
    p["entregables"]["articulo"] = (
        "Dos artículos enviados a revistas internacionales indizadas en el Journal "
        "Citation Reports."
    )
    # R-CDF-CARTA-POSTULACION
    p["documents"].remove("carta_postulacion")


PACKAGES: list[tuple[str, str, object, list[str]]] = [
    ("good", "Individual, correcta. Debe producir cero hallazgos.", None, []),
    ("bad", "Grupo de investigación con doce defectos simultáneos.", m_mala, [
        "R-CDF-RESUMEN-500",
        "R-CDF-ENTREGABLES-MINIMOS",
        "R-CDF-ARTICULO-NACIONAL",
        "R-CDF-GRUPO-MIN-3",
        "R-CDF-GRUPO-DOS-INSTITUCIONES",
        "R-CDF-RA-DISTINTA-RT",
        "R-CDF-EVALUADORES-MIN-3",
        "R-CDF-EVALUADORES-SIN-ADSCRIPCION",
        "R-CDF-MONTO-MAXIMO",
        "R-CDF-MONTO-POR-ETAPA",
        "R-CDF-HONORARIOS-30",
        "R-CDF-RUBROS-NO-FINANCIABLES",
        "R-CDF-CARTA-POSTULACION",
    ]),
    ("broken-resumen", "Resumen ejecutivo de 612 palabras; el límite es 500.",
     m_resumen_largo, ["R-CDF-RESUMEN-500"]),
    ("broken-sin-carta", "Falta la Carta Oficial de Postulación.",
     m_sin_carta, ["R-CDF-CARTA-POSTULACION"]),
    ("broken-sin-protocolo", "Falta el Protocolo de investigación.",
     m_sin_protocolo, ["R-CDF-PROTOCOLO-PRESENTE"]),
    ("broken-protocolo-encabezado", "El encabezado del protocolo no lleva el número de propuesta.",
     m_protocolo_sin_encabezado, ["R-CDF-PROTOCOLO-ENCABEZADO"]),
    ("broken-entregables", "No se compromete la formación de personas en capacidades HCTI.",
     m_sin_hcti, ["R-CDF-ENTREGABLES-MINIMOS"]),
    ("broken-articulo", "El único artículo comprometido es en revista internacional.",
     m_articulo_internacional, ["R-CDF-ARTICULO-NACIONAL"]),
    ("broken-cronograma", "La etapa 3 no declara meta.",
     m_cronograma_incompleto, ["R-CDF-CRONOGRAMA-METAS"]),
    ("broken-presupuesto-desglose",
     "Presupuesto presentado como monto único, sin desglose por etapa y rubro.",
     m_presupuesto_sin_desglose, ["R-CDF-PRESUPUESTO-DESGLOSE"]),
    ("broken-en-captura", "La solicitud no fue finalizada antes del cierre.",
     m_en_captura, ["R-CDF-PAQUETE-COMPLETO"]),
]

OVERSIZE = ("broken-protocolo-tamano",
            "Protocolo de investigación de más de 4 MB.",
            m_protocolo_pesado, ["R-CDF-PROTOCOLO-TAMANO"])


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

def styles():
    ss = getSampleStyleSheet()
    return {
        "banner": ParagraphStyle("banner", parent=ss["Normal"], fontSize=7.5,
                                 textColor="#8a6d1f", spaceAfter=10, leading=9),
        "h1": ParagraphStyle("h1", parent=ss["Heading1"], fontSize=13, spaceAfter=8),
        "h2": ParagraphStyle("h2", parent=ss["Heading2"], fontSize=10.5, spaceBefore=10,
                             spaceAfter=4),
        "body": ParagraphStyle("body", parent=ss["Normal"], fontSize=9, leading=12.5,
                               alignment=TA_JUSTIFY, spaceAfter=5),
        "field": ParagraphStyle("field", parent=ss["Normal"], fontSize=9, leading=12.5,
                                spaceAfter=2),
    }


def money(n: int) -> str:
    return f"${n:,.2f}"


def render_solicitud(p: dict, path: Path) -> None:
    s = styles()
    flow = [Paragraph(BANNER, s["banner"]),
            Paragraph("Secretaría de Ciencia, Humanidades, Tecnología e Innovación", s["body"]),
            Paragraph("SALSA Proyectos — Solicitud de apoyo", s["h1"]),
            Paragraph("Convocatoria: Ciencia Básica y de Frontera 2025", s["field"]),
            Paragraph(f"Número de propuesta: {p['numero']}", s["field"]),
            Paragraph(f"Estado de la solicitud: {p['estado_solicitud']}", s["field"]),
            Paragraph(f"Fecha de finalización: {p['finalizada']}", s["field"]),
            Spacer(1, 6)]

    flow += [Paragraph("1. DATOS GENERALES DEL PROYECTO", s["h2"]),
             Paragraph(f"1.a Título: {p['titulo']}", s["field"]),
             Paragraph(f"1.b Área del conocimiento: {p['area']}", s["field"]),
             Paragraph(f"1.b.1 Modalidad: {p['modalidad']}", s["field"]),
             Paragraph(f"1.b.2 Número de etapas: {len(p['etapas'])} "
                       f"({', '.join(str(e['ejercicio']) for e in p['etapas'])})", s["field"]),
             Paragraph("1.c Resumen ejecutivo", s["h2"]),
             Paragraph(exactly_n_words(RESUMEN_POOL, p["resumen_words"]), s["body"]),
             Paragraph(f"1.d Institución Beneficiaria: {p['institucion']}", s["field"])]

    rt = p["responsable_tecnica"]
    flow += [Paragraph("1.e Persona responsable técnica", s["h2"]),
             Paragraph(f"Nombre: {rt['nombre']}", s["field"]),
             Paragraph(f"CVU / Rizoma: {rt['cvu']}", s["field"]),
             Paragraph(f"Adscripción: {rt['adscripcion']}", s["field"])]

    flow += [Paragraph("1.f Personas participantes", s["h2"])]
    for i, q in enumerate(p["participantes"], 1):
        flow.append(Paragraph(
            f"Participante {i}: {q['nombre']} — CVU / Rizoma: {q['cvu']} — "
            f"Adscripción: {q['adscripcion']}", s["field"]))

    flow += [PageBreak(),
             Paragraph(BANNER, s["banner"]),
             Paragraph("2. INTRODUCCIÓN, OBJETIVOS, METODOLOGÍA Y PLAN DE TRABAJO", s["h2"]),
             Paragraph(exactly_n_words(PROTOCOLO_POOL, 150), s["body"]),
             Paragraph("2.d Cronograma y metas por etapa", s["h2"])]
    for e in p["etapas"]:
        meta = e["meta"] or "— (no se declara meta para esta etapa)"
        flow.append(Paragraph(f"Etapa {e['numero']} ({e['ejercicio']}): {meta}", s["field"]))

    flow += [Paragraph("3. RESULTADOS ESPERADOS E IMPACTO", s["h2"]),
             Paragraph(exactly_n_words(RESUMEN_POOL, 110), s["body"]),
             Paragraph("4. PRODUCTOS ENTREGABLES COMPROMETIDOS", s["h2"])]
    labels = {"articulo": "4.a Artículo",
              "difusion": "4.b Difusión",
              "divulgacion": "4.c Divulgación",
              "formacion_hcti": "4.d Formación de capacidades HCTI"}
    for key, label in labels.items():
        if key in p["entregables"]:
            flow.append(Paragraph(f"{label}: {p['entregables'][key]}", s["field"]))

    flow += [PageBreak(), Paragraph(BANNER, s["banner"]),
             Paragraph("5. PRESUPUESTO DETALLADO", s["h2"])]
    cols = len(p["etapas"])
    total = sum(sum(row[1:1 + cols]) for row in p["presupuesto"])
    if p["presupuesto_desglosado"]:
        for row in p["presupuesto"]:
            rubro, montos = row[0], row[1:1 + cols]
            per = "   ".join(f"Etapa {i + 1}: {money(m)}" for i, m in enumerate(montos))
            flow.append(Paragraph(f"Rubro: {rubro}", s["field"]))
            flow.append(Paragraph(f"&nbsp;&nbsp;&nbsp;{per}   Subtotal: {money(sum(montos))}",
                                  s["field"]))
        for i in range(cols):
            flow.append(Paragraph(
                f"Total etapa {i + 1}: {money(sum(row[1 + i] for row in p['presupuesto']))}",
                s["field"]))
    else:
        flow.append(Paragraph(
            "El presupuesto se presenta como monto único para la totalidad del proyecto; "
            "el desglose por etapa y por rubro se entregará posteriormente.", s["body"]))
    flow.append(Paragraph(f"Monto total solicitado: {money(total)}", s["field"]))

    flow += [Paragraph("6. PROPUESTA DE EVALUADORAS Y EVALUADORES", s["h2"])]
    for i, ev in enumerate(p["evaluadores"], 1):
        flow.append(Paragraph(
            f"Evaluador {i}: {ev['nombre']} — Adscripción: {ev['adscripcion']}", s["field"]))

    ra, rl = p["responsable_administrativa"], p["representante_legal"]
    flow += [Paragraph("7. CARTA OFICIAL DE POSTULACIÓN", s["h2"]),
             Paragraph(f"7.a Representante Legal: {rl['nombre']} — {rl['cargo']}", s["field"]),
             Paragraph(f"7.c Persona responsable administrativa: {ra['nombre']} — "
                       f"CVU / Rizoma: {ra['cvu']} — Adscripción: {ra['adscripcion']}",
                       s["field"]),
             Paragraph(
                 "7.d Estado de la carta: "
                 + ("adjunta y firmada electrónicamente"
                    if "carta_postulacion" in p["documents"]
                    else "pendiente de firma del Representante Legal"), s["field"])]

    SimpleDocTemplate(str(path), pagesize=LETTER, title="Solicitud CDF 2025",
                      author="fixture", subject="synthetic test data",
                      leftMargin=2.2 * cm, rightMargin=2.2 * cm,
                      topMargin=2 * cm, bottomMargin=2 * cm).build(flow)


def render_protocolo(p: dict, path: Path) -> None:
    s = styles()
    header = (f"Propuesta {p['numero']} — {p['titulo']}"
              if p["protocolo_encabezado"]
              else p["titulo"])
    flow = [Paragraph(BANNER, s["banner"]),
            Paragraph(header, s["h1"]),
            Paragraph("Protocolo de investigación", s["h2"])]
    for n in range(p["protocolo_pages"]):
        flow.append(Paragraph(f"{n + 1}. Sección del protocolo", s["h2"]))
        flow.append(Paragraph(exactly_n_words(PROTOCOLO_POOL, 260), s["body"]))
        if n < p["protocolo_pages"] - 1:
            flow += [PageBreak(), Paragraph(BANNER, s["banner"]), Paragraph(header, s["field"])]
    SimpleDocTemplate(str(path), pagesize=LETTER, title="Protocolo CDF 2025",
                      author="fixture", subject="synthetic test data",
                      leftMargin=2.2 * cm, rightMargin=2.2 * cm,
                      topMargin=2 * cm, bottomMargin=2 * cm).build(flow)

    if p["protocolo_padding_kb"]:
        _pad_to(path, p["protocolo_padding_kb"])


def _pad_to(path: Path, kb: int) -> None:
    """Grow a PDF past a size threshold without changing what it says.

    An embedded, incompressible image is how a real protocol reaches 4 MB —
    someone pastes a microscope photograph in at full sensor resolution. Random
    pixels stand in for it because they do not deflate, so the size is
    predictable; a real photograph would behave the same way.

    PyMuPDF refuses a non-incremental save over the file it opened, hence the
    temporary path.
    """
    import os
    import random

    random.seed(20250425)
    side = 1 + int(((kb * 1024) / 3) ** 0.5)          # w*h*3 bytes of RGB
    raw = random.randbytes(side * side * 3)
    pix = pymupdf.Pixmap(pymupdf.csRGB, side, side, raw, False)

    tmp = path.with_suffix(".tmp.pdf")
    with pymupdf.open(path) as doc:
        doc[0].insert_image(pymupdf.Rect(380, 660, 520, 760), pixmap=pix)
        doc.save(tmp, garbage=0, deflate_images=False)
    os.replace(tmp, path)


def render_carta(p: dict, path: Path) -> None:
    s = styles()
    rl, rt = p["representante_legal"], p["responsable_tecnica"]
    ra = p["responsable_administrativa"]
    flow = [
        Paragraph(BANNER, s["banner"]),
        Paragraph(p["institucion"], s["h1"]),
        Paragraph("Carta Oficial de Postulación", s["h2"]),
        Paragraph("Secretaría de Ciencia, Humanidades, Tecnología e Innovación<br/>Presente.",
                  s["body"]),
        Paragraph(
            f"Por este conducto, la institución que represento postula la propuesta "
            f"{p['numero']}, intitulada «{p['titulo']}», presentada a la Convocatoria "
            f"Ciencia Básica y de Frontera 2025 en la modalidad {p['modalidad']}.", s["body"]),
        Paragraph(
            "La institución se compromete a brindar el apoyo y la infraestructura "
            "necesarios para el desarrollo del proyecto, a validar la propuesta presentada "
            "y a formalizar los acuerdos con las instituciones corresponsables cuando "
            "corresponda.", s["body"]),
        Paragraph(
            f"Se designa como persona responsable técnica a {rt['nombre']} y como persona "
            f"responsable administrativa a {ra['nombre']}, distinta de la anterior conforme "
            f"a los Términos de Referencia.", s["body"]),
        Paragraph(
            "Asimismo se declara, bajo protesta de decir verdad, que la institución no "
            "presenta adeudos ni irregularidades derivados de apoyos previos y que la "
            "propuesta no se encuentra duplicada en otros programas o convocatorias.",
            s["body"]),
        Spacer(1, 18),
        Paragraph(f"{rl['nombre']}", s["field"]),
        Paragraph(f"{rl['cargo']}", s["field"]),
        Paragraph("Representante Legal — Firmado electrónicamente en SALSA Proyectos",
                  s["field"]),
    ]
    SimpleDocTemplate(str(path), pagesize=LETTER, title="Carta de postulación CDF 2025",
                      author="fixture", subject="synthetic test data",
                      leftMargin=2.5 * cm, rightMargin=2.5 * cm,
                      topMargin=2.5 * cm, bottomMargin=2.5 * cm).build(flow)


RENDERERS = {
    "solicitud": ("solicitud.pdf", render_solicitud),
    "protocolo": ("protocolo.pdf", render_protocolo),
    "carta_postulacion": ("carta-postulacion.pdf", render_carta),
}


def build(name: str, description: str, mutate, expected: list[str]) -> dict:
    p = base_proposal()
    if mutate:
        mutate(p)

    if name == "good":
        # `good` must satisfy the pack, not merely be intended to. Asserting it
        # here means a careless edit to the budget fails the build rather than
        # quietly turning the no-findings test into a test of nothing.
        cap = CAPS[p["modalidad"]]
        cols = len(p["etapas"])
        total = sum(sum(r[1:1 + cols]) for r in p["presupuesto"])
        honorarios = sum(sum(r[1:1 + cols]) for r in p["presupuesto"]
                         if r[0].startswith("Honorarios"))
        assert total <= cap["total"], f"good is over the total cap: {total}"
        for i in range(cols):
            etapa = sum(r[1 + i] for r in p["presupuesto"])
            assert etapa <= cap["etapas"][i], f"good breaks the etapa {i + 1} cap: {etapa}"
        assert honorarios / total <= 0.30, "good breaks the 30% honorarios cap"
        assert p["resumen_words"] < 500
        assert 2 <= cols <= 3
        assert set(p["entregables"]) == {"articulo", "difusion", "divulgacion",
                                         "formacion_hcti"}
        assert len(p["evaluadores"]) >= 3
        participating = {p["institucion"]} | {q["adscripcion"] for q in p["participantes"]}
        assert not participating & {e["adscripcion"] for e in p["evaluadores"]}

    pkg = OUT / name
    if pkg.exists():
        shutil.rmtree(pkg)
    pkg.mkdir(parents=True)

    documents = []
    for doc_type in p["documents"]:
        filename, render = RENDERERS[doc_type]
        path = pkg / filename
        render(p, path)
        with pymupdf.open(path) as d:
            pages = d.page_count
        documents.append({
            "doc_id": doc_type,
            "filename": filename,
            "doc_type": doc_type,
            "page_count": pages,
            "size_bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })

    manifest = {
        "call_id": "secihti-cdf-2025",
        "rule_pack_version": "2026-10-b",
        "case_id": f"cdf-2025-{name}",
        "numero_propuesta": p["numero"],
        "modalidad": p["modalidad"],
        "synthetic": True,
        "documents": documents,
    }
    (pkg / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return {"package": name, "description": description, "expected_rule_ids": expected,
            "documents": [d["filename"] for d in documents]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--with-oversize", action="store_true",
                    help="also build broken-protocolo-tamano (>4 MB, gitignored)")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    specs = list(PACKAGES) + ([OVERSIZE] if args.with_oversize else [])
    oracle = [build(*spec) for spec in specs]

    (OUT / "expected_findings.json").write_text(
        json.dumps({
            "call_id": "secihti-cdf-2025",
            "rule_pack_version": "2026-10-b",
            "note": "Generated by scripts/make_cdf_samples.py. Do not edit by hand.",
            "packages": [o for o in oracle if o["package"] != OVERSIZE[0]],
        }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    for o in oracle:
        n = len(o["expected_rule_ids"])
        print(f"  {o['package']:<30} {len(o['documents'])} docs, "
              f"{n} expected finding{'' if n == 1 else 's'}")
    print(f"\n{len(oracle)} packages written to {OUT}")


if __name__ == "__main__":
    main()
