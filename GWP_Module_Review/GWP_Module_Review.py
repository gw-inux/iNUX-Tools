import streamlit as st
import re
from datetime import datetime, date
import io
import zipfile
import hashlib
import mimetypes
import csv
from urllib.parse import quote
from pathlib import Path
from io import BytesIO
from xml.sax.saxutils import escape

import yaml
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak,
    KeepTogether,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


# -------------------------------------------------
# 0. REVIEW STANDARD / CONSTANTS
# -------------------------------------------------
APP_TITLE = "Module Review"
PROJECT_TITLE = "The Groundwater Project"
REVIEW_STANDARD = "GWP Educational Module Review"
REVIEW_STANDARD_VERSION = "1.3"
YAML_SCHEMA_VERSION = "1.3"
APP_BUILD = "1.4.2"

LANGUAGE_OPTIONS = [
    "English",
    "Chinese (Simplified)",
    "Hindi",
    "Spanish",
    "French",
    "Arabic",
    "Bengali",
    "Russian",
    "Portuguese",
    "Indonesian",
    "Urdu",
    "German",
    "Japanese",
    "Korean",
    "Vietnamese",
    "Turkish",
    "Italian",
    "Polish",
    "Dutch",
    "Thai",
    "Swedish",
    "Danish",
    "Norwegian / Bokmål",
]
LANGUAGE_SELECTION_OPTIONS = LANGUAGE_OPTIONS

RATING_OPTIONS = [
    "— Select —",
    "Meets standard",
    "Minor revision",
    "Major revision",
    "Not assessed / N.A.",
]

RATING_SHORT = {
    "— Select —": "Not rated",
    "Meets standard": "Meets standard",
    "Minor revision": "Minor revision",
    "Major revision": "Major revision",
    "Not assessed / N.A.": "N.A.",
}

RECOMMENDATION_OPTIONS = [
    "— Select —",
    "Ready for release",
    "Ready after minor revisions",
    "Major revisions and re-review recommended",
    "Unable to provide an overall recommendation",
]

REVIEW_SCOPE_OPTIONS = [
    "Full review",
    "Subject / scientific content review",
    "Educational / pedagogical review",
    "Technical / usability review",
]

CRITERIA = [
    {
        "id": "content_accuracy",
        "group": "Content quality",
        "title": "Content accuracy & scientific quality",
        "statement": "The content is accurate, current, scientifically sound, and appropriately supported by references.",
        "guidance": (
            "Consider factual correctness, terminology, equations, calculations, units, assumptions, figures, "
            "scientific references, and whether claims are appropriately supported."
        ),
    },
    {
        "id": "scope_level",
        "group": "Content quality",
        "title": "Scope & learner level",
        "statement": "The amount, depth, and complexity of the material are appropriate for the intended learners.",
        "guidance": (
            "Consider whether important content is missing, whether unnecessary detail creates overload, whether prerequisites "
            "are reasonable, and whether the level of abstraction is appropriate."
        ),
    },
    {
        "id": "learning_objectives",
        "group": "Learning effectiveness",
        "title": "Learning objectives",
        "statement": "The learning objectives are clear, appropriate, and reflected in the module.",
        "guidance": (
            "Consider whether learners can understand what they should achieve and whether the stated objectives match the "
            "actual content and expected level of learning."
        ),
    },
    {
        "id": "alignment_sequence",
        "group": "Learning effectiveness",
        "title": "Alignment & learning sequence",
        "statement": "Explanations, activities, interactive elements, and assessments support the learning objectives and form a logical learning sequence.",
        "guidance": (
            "Consider the progression from explanation to exploration/application and assessment. Check that important learning "
            "activities contribute to an identified learning objective."
        ),
    },
    {
        "id": "interactive_learning",
        "group": "Learning effectiveness",
        "title": "Interactive learning",
        "statement": "The interactive elements contribute meaningfully to understanding and provide clear, interpretable results or feedback.",
        "guidance": (
            "Consider whether changing parameters or making choices teaches something, whether defaults are meaningful, and "
            "whether learners can interpret the resulting plots, values, or feedback."
        ),
    },
    {
        "id": "clarity_usability",
        "group": "User experience & delivery",
        "title": "Clarity, navigation & visual usability",
        "statement": "The module is easy to understand, navigate, and use, and its visual presentation supports learning.",
        "guidance": (
            "Consider instructions, navigation, terminology, readability, layout, figures, visual consistency, and information density."
        ),
    },
    {
        "id": "technical_functionality",
        "group": "User experience & delivery",
        "title": "Technical functionality",
        "statement": "The module and its interactive components work reliably and behave as expected.",
        "guidance": (
            "Record errors, broken controls or links, implausible results, unexpected resets, very slow calculations, or other "
            "behaviour that affects the learner experience. This is not intended as a full software audit."
        ),
    },
    {
        "id": "accessibility_openness",
        "group": "User experience & delivery",
        "title": "Accessibility, inclusion & openness",
        "statement": "The module appears accessible and inclusive, and sources, external materials, and licensing are handled appropriately.",
        "guidance": (
            "Use a high-level reviewer judgement: readability, use of colour, understandable figures, inclusive language/context, "
            "source attribution, and appropriate handling of reused material. Formal WCAG testing belongs to technical QA."
        ),
    },
]

LANGUAGE_CRITERIA = [
    {
        "id": "language_appropriateness",
        "title": "Meaning & language appropriateness",
        "statement": "The translation conveys the intended meaning accurately and uses language appropriate for the intended learners and educational context.",
        "guidance": (
            "Consider whether the translated text preserves the meaning of the source, uses an appropriate register and level, "
            "and avoids wording that is misleading, culturally awkward, or unsuitable for an educational module."
        ),
    },
    {
        "id": "technical_terminology",
        "title": "Technical terminology",
        "statement": "Technical and hydrogeological terminology is correct, consistent, and appropriate in the selected language.",
        "guidance": (
            "Pay particular attention to groundwater and hydrogeological terms, units, labels, figure text, assessment terminology, "
            "and terms that should be standardized in the project glossary."
        ),
    },
    {
        "id": "fluency_readability",
        "title": "Fluency & readability",
        "statement": "The translated language is fluent, natural, grammatically sound, and easy to understand.",
        "guidance": (
            "Consider sentence structure, grammar, spelling, punctuation, natural phrasing, and whether the text reads like a "
            "well-written original rather than a literal machine translation."
        ),
    },
]

ATTACHMENT_TYPES = ["docx", "pdf", "txt", "md", "png", "jpg", "jpeg"]
REVIEW_COORDINATOR_EMAIL = "treimann@gw-project.org"


# -------------------------------------------------
# 1. GENERAL HELPERS
# -------------------------------------------------
def slugify(text: str) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "review"


def compute_upload_signature(uploaded_file) -> str:
    if uploaded_file is None:
        return ""
    try:
        return hashlib.md5(uploaded_file.getvalue()).hexdigest()
    except Exception:
        return ""


def parse_uploaded_yaml(uploaded_file) -> dict:
    if uploaded_file is None:
        return {}
    try:
        text = uploaded_file.getvalue().decode("utf-8", errors="replace")
        data = yaml.safe_load(text) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def safe_date_string(value) -> str:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value or "").strip()


def attachment_metadata(uploaded_files):
    meta = []
    for f in uploaded_files or []:
        raw = f.getvalue()
        mime = getattr(f, "type", None) or mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        meta.append(
            {
                "filename": f.name,
                "mime_type": mime,
                "size_bytes": len(raw),
                "md5": hashlib.md5(raw).hexdigest(),
            }
        )
    return meta


def xml_text(value) -> str:
    return escape(str(value if value not in (None, "") else "—")).replace("\n", "<br/>")


def default_state():
    defaults = {
        "start_mode": "new",
        "preview_requested": False,
        "ready_for_final": False,
        "module_title": "",
        "module_url": "",
        "module_version": "",
        "reviewer_name": "",
        "reviewer_affiliation": "",
        "review_scope": REVIEW_SCOPE_OPTIONS[0],
        "review_date": date.today(),
        "language_target": "English",
        "general_comments": "",
        "overall_recommendation": RECOMMENDATION_OPTIONS[0],
        "glossary_count": 1,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    for c in CRITERIA:
        rkey = f"rating_{c['id']}"
        nkey = f"note_{c['id']}"
        if rkey not in st.session_state:
            st.session_state[rkey] = RATING_OPTIONS[0]
        if nkey not in st.session_state:
            st.session_state[nkey] = ""

    for c in LANGUAGE_CRITERIA:
        rkey = f"rating_lang_{c['id']}"
        nkey = f"note_lang_{c['id']}"
        if rkey not in st.session_state:
            st.session_state[rkey] = RATING_OPTIONS[0]
        if nkey not in st.session_state:
            st.session_state[nkey] = ""

    for i in range(int(st.session_state.get("glossary_count", 1))):
        for field in ["source", "note"]:
            key = f"glossary_{field}_{i}"
            if key not in st.session_state:
                st.session_state[key] = ""


def reset_review_fields():
    preserve = {"start_mode"}
    keys = list(st.session_state.keys())
    for key in keys:
        if key not in preserve:
            del st.session_state[key]
    default_state()


# -------------------------------------------------
# 2. YAML BUILD / IMPORT
# -------------------------------------------------
def collect_review_data(status: str, uploaded_files=None) -> dict:
    now_iso = datetime.now().astimezone().isoformat(timespec="seconds")
    selected_language = st.session_state.get("language_target", "English")
    if selected_language not in LANGUAGE_OPTIONS:
        selected_language = "English"
    include_language_review = selected_language != "English"

    criteria_data = []
    for c in CRITERIA:
        rating = st.session_state.get(f"rating_{c['id']}", RATING_OPTIONS[0])
        note = (st.session_state.get(f"note_{c['id']}", "") or "").strip()
        criteria_data.append(
            {
                "id": c["id"],
                "group": c["group"],
                "title": c["title"],
                "statement": c["statement"],
                "rating": None if rating == RATING_OPTIONS[0] else rating,
                "note": note,
            }
        )

    language_criteria_data = []
    glossary_suggestions = []
    if include_language_review:
        for c in LANGUAGE_CRITERIA:
            rating = st.session_state.get(f"rating_lang_{c['id']}", RATING_OPTIONS[0])
            note = (st.session_state.get(f"note_lang_{c['id']}", "") or "").strip()
            language_criteria_data.append(
                {
                    "id": c["id"],
                    "title": c["title"],
                    "statement": c["statement"],
                    "rating": None if rating == RATING_OPTIONS[0] else rating,
                    "note": note,
                }
            )

        for i in range(int(st.session_state.get("glossary_count", 1))):
            entry = {
                "source_term": (st.session_state.get(f"glossary_source_{i}") or "").strip(),
                "note": (st.session_state.get(f"glossary_note_{i}") or "").strip(),
            }
            if any(entry.values()):
                glossary_suggestions.append(entry)

    recommendation = st.session_state.get("overall_recommendation", RECOMMENDATION_OPTIONS[0])

    return {
        "schema_version": YAML_SCHEMA_VERSION,
        "document_type": "educational_module_review",
        "review_standard": {
            "name": REVIEW_STANDARD,
            "version": REVIEW_STANDARD_VERSION,
        },
        "status": status,
        "updated_at": now_iso,
        "module": {
            "title": (st.session_state.get("module_title") or "").strip(),
            "url": (st.session_state.get("module_url") or "").strip(),
            "version": (st.session_state.get("module_version") or "").strip(),
            "language": selected_language,
        },
        "reviewer": {
            "name": (st.session_state.get("reviewer_name") or "").strip(),
            "affiliation": (st.session_state.get("reviewer_affiliation") or "").strip(),
        },
        "review": {
            "date": safe_date_string(st.session_state.get("review_date")),
            "scope": st.session_state.get("review_scope", REVIEW_SCOPE_OPTIONS[0]),
            "criteria": criteria_data,
            "language_review": {
                "enabled": include_language_review,
                "language": (
                    selected_language if include_language_review else None
                ),
                "criteria": language_criteria_data,
                "glossary_suggestions": glossary_suggestions,
            },
            "comments_and_recommendations": (st.session_state.get("general_comments") or "").strip(),
            "overall_recommendation": None if recommendation == RECOMMENDATION_OPTIONS[0] else recommendation,
        },
        "rating_legend": {
            "Meets standard": "No relevant change required.",
            "Minor revision": "Improvement recommended, but not fundamental.",
            "Major revision": "Important issue that should be addressed.",
            "Not assessed / N.A.": "Outside reviewer expertise or not applicable.",
        },
        "attachments": attachment_metadata(uploaded_files),
    }

def build_yaml_text(status: str, uploaded_files=None) -> str:
    data = collect_review_data(status=status, uploaded_files=uploaded_files)
    return yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=1000,
    )


def glossary_entries_from_data(data: dict) -> list[dict]:
    """Return non-empty glossary entries in the current two-field format."""
    review = data.get("review") if isinstance(data, dict) else {}
    review = review if isinstance(review, dict) else {}
    language_review = review.get("language_review")
    language_review = language_review if isinstance(language_review, dict) else {}

    entries = []
    for item in language_review.get("glossary_suggestions") or []:
        if not isinstance(item, dict):
            continue
        source_term = str(item.get("source_term") or "").strip()
        note = str(item.get("note") or "").strip()
        if source_term or note:
            entries.append({"source_term": source_term, "note": note})
    return entries


def glossary_to_csv_bytes(data: dict) -> bytes:
    """Create an Excel-friendly UTF-8 CSV with source term and note only."""
    entries = glossary_entries_from_data(data)
    if not entries:
        return b""

    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=["source_term", "note"])
    writer.writeheader()
    writer.writerows(entries)

    # UTF-8 BOM improves direct opening of multilingual glossary files in Excel.
    return ("\ufeff" + output.getvalue()).encode("utf-8")


def prefill_from_yaml(data: dict):
    if not data:
        return

    module = data.get("module") if isinstance(data.get("module"), dict) else {}
    reviewer = data.get("reviewer") if isinstance(data.get("reviewer"), dict) else {}
    review = data.get("review") if isinstance(data.get("review"), dict) else {}

    st.session_state["module_title"] = str(module.get("title") or "")
    st.session_state["module_url"] = str(module.get("url") or "")
    st.session_state["module_version"] = str(module.get("version") or "")
    st.session_state["reviewer_name"] = str(reviewer.get("name") or "")
    st.session_state["reviewer_affiliation"] = str(reviewer.get("affiliation") or "")

    scope = str(review.get("scope") or REVIEW_SCOPE_OPTIONS[0])
    st.session_state["review_scope"] = scope if scope in REVIEW_SCOPE_OPTIONS else REVIEW_SCOPE_OPTIONS[0]

    review_date_raw = review.get("date")
    try:
        st.session_state["review_date"] = date.fromisoformat(str(review_date_raw))
    except Exception:
        st.session_state["review_date"] = date.today()

    st.session_state["general_comments"] = str(review.get("comments_and_recommendations") or "")
    rec = review.get("overall_recommendation")
    st.session_state["overall_recommendation"] = rec if rec in RECOMMENDATION_OPTIONS else RECOMMENDATION_OPTIONS[0]

    criterion_map = {}
    for item in review.get("criteria") or []:
        if isinstance(item, dict) and item.get("id"):
            criterion_map[str(item["id"])] = item

    for c in CRITERIA:
        item = criterion_map.get(c["id"], {})
        rating = item.get("rating")
        st.session_state[f"rating_{c['id']}"] = rating if rating in RATING_OPTIONS else RATING_OPTIONS[0]
        st.session_state[f"note_{c['id']}"] = str(item.get("note") or "")

    language_review = review.get("language_review") if isinstance(review.get("language_review"), dict) else {}
    # v1.2 stores the reviewed module/app language under module.language.
    # For v1.1 files, fall back to the former language_review.language field.
    target = str(module.get("language") or language_review.get("language") or "English")
    st.session_state["language_target"] = target if target in LANGUAGE_OPTIONS else "English"

    language_criterion_map = {}
    for item in language_review.get("criteria") or []:
        if isinstance(item, dict) and item.get("id"):
            language_criterion_map[str(item["id"])] = item

    for c in LANGUAGE_CRITERIA:
        item = language_criterion_map.get(c["id"], {})
        rating = item.get("rating")
        st.session_state[f"rating_lang_{c['id']}"] = rating if rating in RATING_OPTIONS else RATING_OPTIONS[0]
        st.session_state[f"note_lang_{c['id']}"] = str(item.get("note") or "")

    # Clear any existing glossary widget state before restoring the imported list.
    # Legacy v1.1/v1.2 current/preferred translation widget keys are also cleared.
    for key in list(st.session_state.keys()):
        if (
            key.startswith("glossary_source_")
            or key.startswith("glossary_current_")
            or key.startswith("glossary_preferred_")
            or key.startswith("glossary_note_")
        ):
            st.session_state.pop(key, None)

    glossary = [x for x in (language_review.get("glossary_suggestions") or []) if isinstance(x, dict)]
    st.session_state["glossary_count"] = max(1, min(50, len(glossary) or 1))
    for i in range(st.session_state["glossary_count"]):
        item = glossary[i] if i < len(glossary) else {}
        st.session_state[f"glossary_source_{i}"] = str(item.get("source_term") or "")

        # Backward compatibility with v1.1/v1.2: ignore the former current translation,
        # but preserve a former preferred translation by folding it into the free note.
        legacy_preferred = str(item.get("preferred_translation") or "").strip()
        note = str(item.get("note") or "").strip()
        if legacy_preferred:
            legacy_line = f"Suggested translation: {legacy_preferred}"
            note = f"{legacy_line}; {note}" if note else legacy_line
        st.session_state[f"glossary_note_{i}"] = note

    st.session_state["preview_requested"] = False
    st.session_state["ready_for_final"] = False
    st.session_state["imported_attachment_meta"] = data.get("attachments") or []


# -------------------------------------------------
# 3. PDF GENERATION
# -------------------------------------------------
def find_optional_logo() -> str | None:
    candidates = [
        Path("FIGS/GWP_logo.png"),
        Path("FIGS/gwp_logo.png"),
        Path("assets/images/gwp_logo.png"),
    ]
    for p in candidates:
        if p.exists() and p.is_file():
            return str(p)
    return None


def yaml_to_pdf_bytes(yaml_text: str, uploaded_files=None) -> bytes:
    data = yaml.safe_load(yaml_text) or {}
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title=f"{PROJECT_TITLE} - Educational Module Review",
        author=str((data.get("reviewer") or {}).get("name") or ""),
    )

    styles = getSampleStyleSheet()
    project_style = ParagraphStyle(
        "ProjectHeader",
        parent=styles["Normal"],
        fontSize=11,
        leading=14,
        textColor=colors.black,
        spaceAfter=4,
    )
    title_style = ParagraphStyle(
        "ReviewTitle",
        parent=styles["Heading1"],
        fontSize=18,
        leading=22,
        spaceAfter=8,
    )
    section_style = ParagraphStyle(
        "SectionTitle",
        parent=styles["Heading2"],
        fontSize=13,
        leading=16,
        spaceBefore=10,
        spaceAfter=5,
    )
    label_style = ParagraphStyle(
        "Label",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=12,
    )
    small_style = ParagraphStyle(
        "Small",
        parent=styles["Normal"],
        fontSize=8.5,
        leading=10.5,
    )
    criterion_style = ParagraphStyle(
        "Criterion",
        parent=styles["Normal"],
        fontSize=9,
        leading=11,
    )
    cover_title_style = ParagraphStyle(
        "CoverTitle",
        parent=styles["Heading1"],
        fontSize=24,
        leading=28,
        alignment=1,
        spaceAfter=12,
    )
    cover_subtitle_style = ParagraphStyle(
        "CoverSubtitle",
        parent=styles["Heading2"],
        fontSize=14,
        leading=18,
        alignment=1,
        textColor=colors.black,
        spaceAfter=6,
    )

    def P(value, style=label_style, bold=False):
        text = xml_text(value)
        if bold:
            text = f"<b>{text}</b>"
        return Paragraph(text, style)

    def add_rating_table(items, grouped=False):
        if not items:
            return

        if grouped:
            grouped_items = {}
            for item in items:
                grouped_items.setdefault(item.get("group") or "Review", []).append(item)
            groups = list(grouped_items.items())
        else:
            groups = [(None, items)]

        for group, group_items in groups:
            if group:
                story.append(Paragraph(xml_text(group), section_style))

            rows = [[P("Standard", small_style, True), P("Rating", small_style, True)]]
            note_rows = []
            for item in group_items:
                left = Paragraph(
                    f"<b>{xml_text(item.get('title'))}</b><br/>{xml_text(item.get('statement'))}",
                    criterion_style,
                )
                rating = item.get("rating") or "Not rated"
                rows.append([left, P(rating, criterion_style)])
                note = (item.get("note") or "").strip()
                if note:
                    rows.append([
                        Paragraph(f"<i>Reviewer note:</i> {xml_text(note)}", small_style),
                        "",
                    ])
                    note_rows.append(len(rows) - 1)

            table = Table(rows, colWidths=[122 * mm, 38 * mm], repeatRows=1)
            style_commands = [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("BOX", (0, 0), (-1, -1), 0.25, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
            for row_idx in note_rows:
                style_commands.extend([
                    ("SPAN", (0, row_idx), (1, row_idx)),
                    ("BACKGROUND", (0, row_idx), (1, row_idx), colors.whitesmoke),
                ])
            table.setStyle(TableStyle(style_commands))
            story.append(table)
            story.append(Spacer(1, 5))

    story = []

    module = data.get("module") or {}
    reviewer = data.get("reviewer") or {}
    review = data.get("review") or {}
    module_language = str(module.get("language") or "English")
    language_review = review.get("language_review") if isinstance(review.get("language_review"), dict) else {}
    include_language_review = bool(language_review.get("enabled")) and module_language != "English"
    language_review_has_content = include_language_review and (
        any((item.get("rating") or item.get("note")) for item in (language_review.get("criteria") or []) if isinstance(item, dict))
        or bool(language_review.get("glossary_suggestions"))
    )

    # ---------- COVER PAGE ----------
    story.append(Spacer(1, 55 * mm))
    story.append(Paragraph(PROJECT_TITLE, cover_title_style))
    story.append(Paragraph("Educational Module Review", cover_subtitle_style))
    story.append(Spacer(1, 14 * mm))

    module_title = module.get("title") or "Untitled module"
    story.append(Paragraph(xml_text(module_title), cover_subtitle_style))
    if module_language != "English":
        story.append(Spacer(1, 3 * mm))
        story.append(Paragraph(f"Module/app language: {xml_text(module_language)}", cover_subtitle_style))

    logo_path = find_optional_logo()
    if logo_path:
        story.append(Spacer(1, 10 * mm))
        try:
            logo = Image(logo_path)
            logo._restrictSize(42 * mm, 42 * mm)
            logo.hAlign = "CENTER"
            story.append(logo)
        except Exception:
            pass

    story.append(PageBreak())

    # ---------- HEADER / TITLE BLOCK ----------
    story.append(Paragraph(f"{PROJECT_TITLE} – Educational Module Review", project_style))
    story.append(Paragraph(xml_text(module.get("title") or "Untitled module"), title_style))
    story.append(P(f"Review standard: {REVIEW_STANDARD} v{REVIEW_STANDARD_VERSION}", small_style))
    story.append(Spacer(1, 5))

    # ---------- 1. REVIEW INFORMATION ----------
    story.append(Paragraph("1. Review information", section_style))
    info_rows = [
        [P("Module title", small_style, True), P(module.get("title"), small_style)],
        [P("Module URL", small_style, True), P(module.get("url"), small_style)],
        [P("Module version", small_style, True), P(module.get("version"), small_style)],
        [P("Reviewer", small_style, True), P(reviewer.get("name"), small_style)],
        [P("Affiliation", small_style, True), P(reviewer.get("affiliation"), small_style)],
        [P("Review date", small_style, True), P(review.get("date"), small_style)],
        [P("Review scope", small_style, True), P(review.get("scope"), small_style)],
        [P("Module/app language", small_style, True), P(module_language, small_style)],
    ]

    info_table = Table(info_rows, colWidths=[42 * mm, 118 * mm])
    info_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("BOX", (0, 0), (-1, -1), 0.25, colors.grey),
                ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(info_table)

    section_num = 2

    # ---------- MODULE QUALITY REVIEW ----------
    story.append(Paragraph(f"{section_num}. Quick quality review", section_style))
    story.append(
        P(
            "Ratings indicate whether each standard is met, requires minor or major revision, or was not assessed. "
            "Criterion notes are included only when provided.",
            small_style,
        )
    )
    story.append(Spacer(1, 5))
    add_rating_table(review.get("criteria") or [], grouped=True)
    section_num += 1

    # ---------- COMMENTS ----------
    story.append(Paragraph(f"{section_num}. Comments and recommendations", section_style))
    comments = (review.get("comments_and_recommendations") or "").strip()
    if comments:
        story.append(Paragraph(xml_text(comments), styles["Normal"]))
    else:
        story.append(P("No additional comments provided.", styles["Normal"]))
    section_num += 1

    # ---------- OVERALL RECOMMENDATION ----------
    story.append(Paragraph(f"{section_num}. Overall recommendation", section_style))
    recommendation = review.get("overall_recommendation") or "Not provided"
    rec_table = Table(
        [[P("Recommendation", small_style, True), P(recommendation, small_style)]],
        colWidths=[42 * mm, 118 * mm],
    )
    rec_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(rec_table)
    section_num += 1

    # ---------- OPTIONAL LANGUAGE REVIEW ----------
    # Included in the PDF only when the reviewer actually entered language-review content.
    if language_review_has_content:
        story.append(Paragraph(f"{section_num}. Optional language review", section_style))
        story.append(P(f"Module/app language reviewed: {module_language}", small_style, True))
        story.append(Spacer(1, 4))
        add_rating_table(language_review.get("criteria") or [], grouped=False)

        story.append(Paragraph("Glossary suggestions", section_style))
        glossary = language_review.get("glossary_suggestions") or []
        if glossary:
            glossary_rows = [[
                P("Source term", small_style, True),
                P("Note / suggested translations", small_style, True),
            ]]
            for item in glossary:
                glossary_rows.append([
                    P(item.get("source_term"), small_style),
                    P(item.get("note"), small_style),
                ])
            glossary_table = Table(glossary_rows, colWidths=[48 * mm, 112 * mm], repeatRows=1)
            glossary_table.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
                        ("BOX", (0, 0), (-1, -1), 0.25, colors.grey),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                        ("LEFTPADDING", (0, 0), (-1, -1), 3),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            story.append(glossary_table)
        else:
            story.append(P("No glossary suggestions provided.", styles["Normal"]))
        section_num += 1

    # ---------- ATTACHMENTS ----------
    attachments = data.get("attachments") or []
    if attachments:
        story.append(Paragraph(f"{section_num}. Review attachments", section_style))
        att_rows = [[P("File", small_style, True), P("Type", small_style, True), P("Size", small_style, True)]]
        for a in attachments:
            size_kb = (a.get("size_bytes") or 0) / 1024.0
            att_rows.append([
                P(a.get("filename"), small_style),
                P(a.get("mime_type"), small_style),
                P(f"{size_kb:.1f} kB", small_style),
            ])
        att_table = Table(att_rows, colWidths=[86 * mm, 50 * mm, 24 * mm], repeatRows=1)
        att_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("BOX", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(att_table)

        # Preserve the useful image-preview behaviour from the CataLogger PDF.
        image_uploads = []
        for f in uploaded_files or []:
            ext = Path(f.name).suffix.lower()
            if ext in {".png", ".jpg", ".jpeg"}:
                image_uploads.append(f)

        if image_uploads:
            story.append(Paragraph("Attached images", section_style))
            for idx, f in enumerate(image_uploads, start=1):
                try:
                    img = Image(BytesIO(f.getvalue()))
                    img._restrictSize(155 * mm, 90 * mm)
                    cap = Paragraph(f"Attachment image {idx}: {xml_text(f.name)}", small_style)
                    story.append(KeepTogether([img, Spacer(1, 2), cap, Spacer(1, 8)]))
                except Exception:
                    story.append(P(f"Image attachment could not be rendered: {f.name}", small_style))

    # ---------- HEADER & FOOTER ----------
    def add_header_footer(canvas, doc_):
        page_num = canvas.getPageNumber()
        width, height = A4
        margin = 20 * mm

        if page_num == 1:
            return

        if page_num % 2 == 0:
            header_y = height - 15 * mm
            canvas.setFont("Helvetica", 9)
            canvas.drawCentredString(width / 2.0, header_y, f"{PROJECT_TITLE} - Educational Module Review")
            canvas.setLineWidth(0.5)
            canvas.line(margin, header_y - 2 * mm, width - margin, header_y - 2 * mm)

        footer_y = 15 * mm
        canvas.setFont("Helvetica", 9)
        canvas.setLineWidth(0.5)
        canvas.line(margin, footer_y + 3 * mm, width - margin, footer_y + 3 * mm)
        canvas.drawCentredString(width / 2.0, footer_y, str(page_num - 1))

    doc.build(story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# -------------------------------------------------
# 4. VALIDATION / PREVIEW HELPERS
# -------------------------------------------------
def validation_issues():
    issues = []
    if not (st.session_state.get("module_title") or "").strip():
        issues.append("Module title is missing.")
    if not (st.session_state.get("reviewer_name") or "").strip():
        issues.append("Reviewer name is missing.")

    unrated = [c["title"] for c in CRITERIA if st.session_state.get(f"rating_{c['id']}") == RATING_OPTIONS[0]]
    if unrated:
        issues.append(f"{len(unrated)} module review standard(s) have not been rated.")

    # The language review is deliberately optional. Selecting a non-English module language
    # makes the block available, but incomplete language ratings never block final generation.

    if st.session_state.get("overall_recommendation") == RECOMMENDATION_OPTIONS[0]:
        issues.append("Overall recommendation is missing.")
    return issues


def rating_summary(criteria_kind="module"):
    counts = {k: 0 for k in RATING_OPTIONS[1:]}
    counts["Not rated"] = 0

    if criteria_kind == "language":
        criteria = LANGUAGE_CRITERIA
        key_prefix = "rating_lang_"
    else:
        criteria = CRITERIA
        key_prefix = "rating_"

    for c in criteria:
        r = st.session_state.get(f"{key_prefix}{c['id']}", RATING_OPTIONS[0])
        if r == RATING_OPTIONS[0]:
            counts["Not rated"] += 1
        else:
            counts[r] += 1
    return counts


# -------------------------------------------------
# 5. STREAMLIT UI
# -------------------------------------------------
st.set_page_config(page_title=APP_TITLE, page_icon="✅", layout="centered")
default_state()

st.title("Module :green[Review] ✅")
st.subheader(
    "The Groundwater Project ➤ Compact quality and language review for interactive educational modules ",
    divider="rainbow",
)
st.caption(f"App build {APP_BUILD} · preview toggle · optional YAML progress save · PDF-first completion")
st.markdown(
    """
Use this form to review an educational module using a compact set of quality standards. For multilingual modules, select the **module/app language** in the review information; an optional language-review section will then be available for non-English versions.

Detailed feedback can be entered in the general comments field or provided as an annotated attachment. You can also save the current state of your review as a **YAML file** and resume it later.
"""
)
st.info(
    "**Important:** This form does **not automatically submit or send your review**. "
    "After completing the review, the app generates a formatted **PDF review report**. "
    "Please download the PDF and send it by email to the Groundwater Project review coordinator. "
    "The app can optionally prepare a pre-populated email for you, but the PDF must still be attached manually."
)

# ---------- Start / resume ----------
col_resume, col_new = st.columns(2)
with col_resume:
    if st.button("⬆️ Resume from YAML", use_container_width=True):
        st.session_state["start_mode"] = "upload"
        st.session_state.pop("last_import_sig", None)
        st.session_state["preview_requested"] = False
        st.session_state["ready_for_final"] = False
        st.rerun()
with col_new:
    if st.button("🆕 Start new review", use_container_width=True):
        reset_review_fields()
        st.session_state["start_mode"] = "new"
        st.rerun()

if st.session_state.get("start_mode") == "upload":
    uploaded_yaml = st.file_uploader(
        "Upload a review YAML to continue working",
        type=["yaml", "yml"],
        key="resume_yaml_upload",
        help="Attachments themselves are not stored in YAML and must be uploaded again if needed.",
    )
    if uploaded_yaml is not None:
        sig = compute_upload_signature(uploaded_yaml)
        if sig and sig != st.session_state.get("last_import_sig"):
            data = parse_uploaded_yaml(uploaded_yaml)
            if not data or data.get("document_type") != "educational_module_review":
                st.error("This file is empty, invalid, or is not a compatible educational module review YAML.")
            else:
                st.session_state["last_import_sig"] = sig
                prefill_from_yaml(data)
                st.success("Review YAML imported. Please check the fields and continue the review.")
                st.rerun()

imported_meta = st.session_state.get("imported_attachment_meta") or []
if imported_meta:
    st.info(
        f"The imported YAML references {len(imported_meta)} attachment(s). Files are not embedded in YAML, so re-upload them below if they should be included in the final package."
    )

st.divider()

# ---------- 1. Review information ----------
st.header("1️⃣ Review information")
st.text_input("Module title", key="module_title")
st.text_input("Module URL (optional)", key="module_url")

c1, c2 = st.columns(2)
with c1:
    st.text_input("Module version / revision (optional)", key="module_version")
with c2:
    st.date_input("Review date", key="review_date")

st.text_input("Reviewer name", key="reviewer_name")
st.text_input("Reviewer affiliation (optional)", key="reviewer_affiliation")
st.selectbox("Review scope", REVIEW_SCOPE_OPTIONS, key="review_scope")

# Keep language selection within the normal review information rather than creating a separate review mode.
st.selectbox(
    "Module/app language reviewed",
    LANGUAGE_SELECTION_OPTIONS,
    key="language_target",
    help="Select the language version of the module/app that you are reviewing. English is the default.",
)
selected_language = st.session_state.get("language_target", "English")
include_language_review = selected_language in LANGUAGE_OPTIONS and selected_language != "English"

if include_language_review:
    st.info(
        f"You selected **{selected_language}**. An optional language-review section is available at the end of the form. "
        "It asks only about meaning/language appropriateness, technical terminology, and fluency/readability. "
        "You can also record source terms with notes or alternative translations to help develop the project glossary."
    )

# ---------- Dynamic numbering for the remaining sections ----------
ui_section = 2

# ---------- General module review ----------
st.header(f"{ui_section}️⃣ Quick quality review")
ui_section += 1
st.caption(
    "Choose one rating per standard. Detailed guidance is available from the ⓘ help icon. "
    "A short note appears only when a revision is requested."
)

current_group = None
for c in CRITERIA:
    if c["group"] != current_group:
        current_group = c["group"]
        st.markdown(f"#### {current_group}")

    left, right = st.columns([2.25, 1])
    with left:
        st.markdown(f"**{c['title']}**")
        st.caption(c["statement"])
    with right:
        st.selectbox(
            f"Rating — {c['title']}",
            RATING_OPTIONS,
            key=f"rating_{c['id']}",
            help=c["guidance"],
            label_visibility="collapsed",
        )

    selected = st.session_state.get(f"rating_{c['id']}")
    if selected in {"Minor revision", "Major revision"}:
        st.text_area(
            f"Short note for {c['title']} (optional)",
            key=f"note_{c['id']}",
            height=80,
            placeholder="Briefly identify the issue or suggested change…",
        )

# ---------- Comments / attachments ----------
st.header(f"{ui_section}️⃣ Comments and supporting material")
ui_section += 1
comments_placeholder = "Paste or write detailed review notes here. Notes prepared in another document can also be attached below."
st.text_area(
    "Comments and recommendations",
    key="general_comments",
    height=220,
    placeholder=comments_placeholder,
)

uploaded_attachments = st.file_uploader(
    "Optional review attachment(s)",
    type=ATTACHMENT_TYPES,
    accept_multiple_files=True,
    key="review_attachments",
    help="Examples: annotated Word document, PDF, Markdown/text notes, or screenshots.",
)
if uploaded_attachments:
    st.caption("Attachments will be listed in the PDF and included as original files in the final ZIP package.")
    for f in uploaded_attachments:
        st.write(f"• {f.name} ({len(f.getvalue()) / 1024:.1f} kB)")

# ---------- Overall recommendation ----------
st.header(f"{ui_section}️⃣ Overall recommendation")
ui_section += 1
st.selectbox("Overall recommendation", RECOMMENDATION_OPTIONS, key="overall_recommendation")

# ---------- Optional language review (non-English modules only) ----------
if include_language_review:
    st.header(f"{ui_section}️⃣ Optional language review")
    ui_section += 1
    st.caption(
        f"Reviewing the **{selected_language}** version. This section is optional and does not block final submission. "
        "Use it when you can assess the quality of the translation."
    )

    for c in LANGUAGE_CRITERIA:
        left, right = st.columns([2.25, 1])
        with left:
            st.markdown(f"**{c['title']}**")
            st.caption(c["statement"])
        with right:
            st.selectbox(
                f"Language rating — {c['title']}",
                RATING_OPTIONS,
                key=f"rating_lang_{c['id']}",
                help=c["guidance"],
                label_visibility="collapsed",
            )

        selected = st.session_state.get(f"rating_lang_{c['id']}")
        if selected in {"Minor revision", "Major revision"}:
            st.text_area(
                f"Short language note for {c['title']} (optional)",
                key=f"note_lang_{c['id']}",
                height=80,
                placeholder="Briefly identify the language issue or suggested change…",
            )

    with st.expander("📘 Terminology / glossary suggestions (optional)", expanded=False):
        st.caption(
            "Record terminology that should be standardized for future translations. "
            "Use the note for a recommended translation, alternative translations, context, or other terminology guidance."
        )

        header_source, header_note = st.columns([1.2, 3.0])
        with header_source:
            st.markdown("**Source term**")
        with header_note:
            st.markdown("**Note / suggested translations**")

        glossary_count = int(st.session_state.get("glossary_count", 1))
        for i in range(glossary_count):
            g1, g2 = st.columns([1.2, 3.0])
            with g1:
                st.text_input(
                    f"Source term {i + 1}",
                    key=f"glossary_source_{i}",
                    label_visibility="collapsed",
                    placeholder="Source term",
                )
            with g2:
                st.text_input(
                    f"Note / suggested translations {i + 1}",
                    key=f"glossary_note_{i}",
                    label_visibility="collapsed",
                    placeholder="Recommended or alternative translation(s), context, notes…",
                )

        add_col, remove_col = st.columns(2)
        with add_col:
            if st.button("➕ Add glossary term", use_container_width=True):
                if st.session_state["glossary_count"] < 50:
                    st.session_state["glossary_count"] += 1
                    new_i = st.session_state["glossary_count"] - 1
                    for field in ["source", "note"]:
                        st.session_state.setdefault(f"glossary_{field}_{new_i}", "")
                    st.rerun()
        with remove_col:
            if st.button(
                "➖ Remove last term",
                use_container_width=True,
                disabled=st.session_state.get("glossary_count", 1) <= 1,
            ):
                if st.session_state["glossary_count"] > 1:
                    remove_i = st.session_state["glossary_count"] - 1
                    st.session_state["glossary_count"] -= 1
                    for field in ["source", "note"]:
                        st.session_state.pop(f"glossary_{field}_{remove_i}", None)
                    st.rerun()

# ---------- Save progress / optional preview / complete review ----------
st.header(f"{ui_section}️⃣ Save progress and complete review")
ui_section += 1
draft_yaml = build_yaml_text(status="draft", uploaded_files=uploaded_attachments)
module_slug = slugify(st.session_state.get("module_title") or "module")
reviewer_slug = slugify(st.session_state.get("reviewer_name") or "reviewer")
draft_filename = f"module-review_{module_slug}_{reviewer_slug}_draft.yaml"

# Preview is the first control in this section. It can be used at any time,
# including while the review is still incomplete.
st.toggle(
    "🔍 Preview review",
    key="preview_requested",
    help="Show or hide a preview of the current review below.",
)

st.markdown(
    "**Save your progress (optional):** If you want to stop and continue later, "
    "you can download the current review as a YAML file. Upload that YAML file at "
    "the top of the app to resume the review later."
)

with st.expander("💾 Save progress as YAML (optional)", expanded=False):
    st.download_button(
        "⬇️ Download intermediate YAML",
        data=draft_yaml,
        file_name=draft_filename,
        mime="text/yaml",
        use_container_width=True,
        help="Use this to save the current review state and resume it later.",
    )
    show_current_yaml = st.checkbox(
        "Show current YAML",
        value=False,
        key="show_current_yaml",
        help="Display the current YAML in the app.",
    )
    if show_current_yaml:
        st.code(draft_yaml, language="yaml")

issues_now = validation_issues()
review_ready = not issues_now

# If a previously completed review becomes incomplete after an edit,
# hide the final-output section again until the required information is restored.
if not review_ready:
    st.session_state["ready_for_final"] = False

if issues_now:
    st.caption(
        "The PDF can be generated once all required information and ratings are complete. "
        "You can still preview the review or save your progress as YAML."
    )
else:
    st.success("The required review information is complete. The PDF report is ready to generate.")

# Keep the final action visually inactive until the required review information is complete.
# The primary button is styled green once enabled.
st.markdown(
    """
    <style>
    div[data-testid="stButton"] button[kind="primary"],
    div[data-testid="stButton"] button[data-testid="stBaseButton-primary"] {
        background-color: #2e7d32 !important;
        border-color: #2e7d32 !important;
        color: white !important;
    }
    div[data-testid="stButton"] button[kind="primary"]:hover,
    div[data-testid="stButton"] button[data-testid="stBaseButton-primary"]:hover {
        background-color: #256628 !important;
        border-color: #256628 !important;
        color: white !important;
    }
    div[data-testid="stButton"] button:disabled {
        background-color: #e0e0e0 !important;
        border-color: #bdbdbd !important;
        color: #757575 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

complete_clicked = st.button(
    "✅ Complete review and generate PDF",
    use_container_width=True,
    type="primary" if review_ready else "secondary",
    disabled=not review_ready,
    key="generate_pdf_button",
    help=(
        "Generate the final PDF review report."
        if review_ready
        else "Complete all required information and ratings to enable PDF generation."
    ),
)

if complete_clicked:
    # Re-check immediately before finalization in case state changed during the rerun.
    issues = validation_issues()
    if issues:
        st.session_state["ready_for_final"] = False
        st.error(
            "Please complete the following before generating the final PDF:\n\n"
            + "\n".join(f"- {x}" for x in issues)
        )
    else:
        st.session_state["ready_for_final"] = True

if st.session_state.get("preview_requested"):
    st.header(f"{ui_section}️⃣ Preview")

    issues = validation_issues()
    if issues:
        st.warning(
            "The review can still be saved as a draft, but the following should normally be completed before final PDF generation:\n\n"
            + "\n".join(f"- {x}" for x in issues)
        )

    st.markdown("#### Review overview")
    p1, p2 = st.columns(2)
    with p1:
        st.markdown(f"**Module:** {st.session_state.get('module_title') or '—'}")
        st.markdown(f"**Version:** {st.session_state.get('module_version') or '—'}")
        st.markdown(f"**Reviewer:** {st.session_state.get('reviewer_name') or '—'}")
    with p2:
        st.markdown(f"**Scope:** {st.session_state.get('review_scope') or '—'}")
        language_display = st.session_state.get("language_target", "English")
        st.markdown(f"**Module/app language:** {language_display if language_display in LANGUAGE_OPTIONS else 'English'}")
        st.markdown(f"**Date:** {safe_date_string(st.session_state.get('review_date')) or '—'}")
        st.markdown(f"**Recommendation:** {st.session_state.get('overall_recommendation') or '—'}")

    counts = rating_summary("module")
    st.markdown("#### Module quality rating summary")
    st.markdown(
        f"**Meets:** {counts['Meets standard']} &nbsp;&nbsp; | &nbsp;&nbsp; "
        f"**Minor:** {counts['Minor revision']} &nbsp;&nbsp; | &nbsp;&nbsp; "
        f"**Major:** {counts['Major revision']} &nbsp;&nbsp; | &nbsp;&nbsp; "
        f"**N.A.:** {counts['Not assessed / N.A.']} &nbsp;&nbsp; | &nbsp;&nbsp; "
        f"**Not rated:** {counts['Not rated']}"
    )

    st.markdown("#### Module standards")
    for c in CRITERIA:
        rating = st.session_state.get(f"rating_{c['id']}", RATING_OPTIONS[0])
        st.markdown(f"- **{c['title']}:** {RATING_SHORT.get(rating, rating)}")
        note = (st.session_state.get(f"note_{c['id']}") or "").strip()
        if note:
            st.caption(f"  Note: {note}")

    if include_language_review:
        counts = rating_summary("language")
        st.markdown("#### Optional language review")
        st.caption(f"Module/app language reviewed: **{selected_language}**")
        st.markdown("##### Language rating summary")
        st.markdown(
            f"**Meets:** {counts['Meets standard']} &nbsp;&nbsp; | &nbsp;&nbsp; "
            f"**Minor:** {counts['Minor revision']} &nbsp;&nbsp; | &nbsp;&nbsp; "
            f"**Major:** {counts['Major revision']} &nbsp;&nbsp; | &nbsp;&nbsp; "
            f"**N.A.:** {counts['Not assessed / N.A.']} &nbsp;&nbsp; | &nbsp;&nbsp; "
            f"**Not rated:** {counts['Not rated']}"
        )

        st.markdown("##### Language standards")
        for c in LANGUAGE_CRITERIA:
            rating = st.session_state.get(f"rating_lang_{c['id']}", RATING_OPTIONS[0])
            st.markdown(f"- **{c['title']}:** {RATING_SHORT.get(rating, rating)}")
            note = (st.session_state.get(f"note_lang_{c['id']}") or "").strip()
            if note:
                st.caption(f"  Note: {note}")

        glossary_preview = []
        for i in range(int(st.session_state.get("glossary_count", 1))):
            entry = {
                "source": (st.session_state.get(f"glossary_source_{i}") or "").strip(),
                "note": (st.session_state.get(f"glossary_note_{i}") or "").strip(),
            }
            if any(entry.values()):
                glossary_preview.append(entry)

        if glossary_preview:
            st.markdown("##### Glossary suggestions")
            for item in glossary_preview:
                source = item["source"] or "—"
                note = item["note"] or "—"
                st.markdown(f"- **{source}** — {note}")

    comments = (st.session_state.get("general_comments") or "").strip()
    if comments:
        st.markdown("#### Comments and recommendations")
        st.write(comments)

    if uploaded_attachments:
        st.markdown("#### Attachments")
        for f in uploaded_attachments:
            st.markdown(f"- {f.name}")

    if not issues:
        st.caption("Preview complete. Use **Complete review and generate PDF** above when you are ready.")

# ---------- Final files ----------
if st.session_state.get("ready_for_final"):
    st.header(f"{ui_section + 1}️⃣ Review report")

    final_yaml = build_yaml_text(status="final", uploaded_files=uploaded_attachments)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"module-review_{module_slug}_{reviewer_slug}_{timestamp}"
    yaml_filename = f"{base_name}.yaml"
    pdf_filename = f"{base_name}.pdf"

    final_data = yaml.safe_load(final_yaml) or {}
    glossary_csv = glossary_to_csv_bytes(final_data)
    language_slug = slugify((final_data.get("module") or {}).get("language") or "language")
    glossary_csv_filename = f"{base_name}_glossary_{language_slug}.csv"

    try:
        pdf_bytes = yaml_to_pdf_bytes(final_yaml, uploaded_files=uploaded_attachments)
    except Exception as exc:
        st.error("The PDF could not be generated.")
        st.exception(exc)
        st.stop()

    st.success(
        "**Your review report is ready.** The review has not been submitted automatically. "
        "Please download the PDF below and send it by email to the Groundwater Project review coordinator."
    )

    st.download_button(
        f"⬇️ Download PDF review ({pdf_filename})",
        data=pdf_bytes,
        file_name=pdf_filename,
        mime="application/pdf",
        use_container_width=True,
        type="primary",
    )

    st.markdown("#### Send your review")
    st.caption(
        "After downloading the PDF, you can optionally open a pre-populated email. "
        "For security reasons, the browser cannot attach the generated PDF automatically, so please attach the downloaded PDF before sending."
    )

    module_title_email = (st.session_state.get("module_title") or "Educational module").strip()
    reviewer_name_email = (st.session_state.get("reviewer_name") or "").strip()
    email_subject = f"GWP Module Review – {module_title_email}"
    email_body = (
        "Dear Thomas,\n\n"
        f"Please find attached my review of the module \"{module_title_email}\".\n\n"
        "Thank you and best regards,\n"
        f"{reviewer_name_email}"
    )
    mailto_url = (
        f"mailto:{REVIEW_COORDINATOR_EMAIL}"
        f"?subject={quote(email_subject)}"
        f"&body={quote(email_body)}"
    )
    st.link_button(
        f"✉️ Prepare email to {REVIEW_COORDINATOR_EMAIL}",
        mailto_url,
        use_container_width=True,
    )

    if uploaded_attachments:
        st.info(
            "You included additional review attachments. Please also attach those files to your email, "
            "or use the optional ZIP package below to keep the review materials together."
        )

    with st.expander("Additional downloads (optional)", expanded=False):
        st.download_button(
            f"⬇️ Download final YAML ({yaml_filename})",
            data=final_yaml,
            file_name=yaml_filename,
            mime="text/yaml",
            use_container_width=True,
            help="Machine-readable copy of the final review; mainly useful for archiving or resuming structured processing.",
        )

        if glossary_csv:
            st.download_button(
                f"⬇️ Download glossary CSV ({glossary_csv_filename})",
                data=glossary_csv,
                file_name=glossary_csv_filename,
                mime="text/csv",
                use_container_width=True,
                help="Contains the glossary source term and note columns in UTF-8 format.",
            )

        if uploaded_attachments:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(yaml_filename, final_yaml)
                zf.writestr(pdf_filename, pdf_bytes)
                if glossary_csv:
                    zf.writestr(glossary_csv_filename, glossary_csv)
                used_names = set()
                for idx, f in enumerate(uploaded_attachments, start=1):
                    original = Path(f.name).name
                    safe_name = original
                    if safe_name in used_names:
                        safe_name = f"{idx}_{safe_name}"
                    used_names.add(safe_name)
                    zf.writestr(f"attachments/{safe_name}", f.getvalue())
            zip_buffer.seek(0)

            st.download_button(
                f"⬇️ Download complete ZIP package ({base_name}.zip)",
                data=zip_buffer.getvalue(),
                file_name=f"{base_name}.zip",
                mime="application/zip",
                use_container_width=True,
                help="Contains the PDF, YAML, glossary CSV (if present), and uploaded review attachments.",
            )

