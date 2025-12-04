import streamlit as st
import re
from datetime import datetime  # for timestamp in filename
import io
import zipfile

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,  # for images in PDF
    PageBreak,  
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from io import BytesIO
import yaml


# -------------------------------------------------
# 0. LANGUAGE OPTIONS
# -------------------------------------------------
LANGUAGE_OPTIONS = {
    "English": "en",
    "German": "de",
    "French": "fr",
    "Italian": "it",
    "Swedish": "sv",
    "Hindi": "hi",
    "Polish": "pl",
    "Dutch": "nl",
}

# -------------------------------------------------
# 1. HARDCODED CATALOG STRUCTURE
# -------------------------------------------------
CATALOG = {
    "01 Water Cycle": {
        "page_id": "010000_en",
        "sub": {
            "01 Precipitation & Hydrometeorology": {
                "page_id": "010100_en",
                "sub": {}
            },
            "02 Evaporation, Transpiration & ET Processes": {
                "page_id": "010200_en",
                "sub": {}
            },
            "03 Surface Runoff Formation": {
                "page_id": "010300_en",
                "sub": {}
            },
            "04 Soil Water in the Hydrological Cycle": {
                "page_id": "010400_en",
                "sub": {}
            },
            "05 Groundwater Recharge (process-based)": {
                "page_id": "010500_en",
                "sub": {}
            },
        },
    },
    "02 Basic Hydrology": {
        "page_id": "020000_en",
        "sub": {
            "01 Catchment Hydrology & Runoff Generation": {
                "page_id": "020100_en",
                "sub": {}
            },
            "02 Hydrographs & Flow Regimes": {
                "page_id": "020200_en",
                "sub": {}
            },
            "03 Water Balance & Hydrologic Budget": {
                "page_id": "020300_en",
                "sub": {}
            },
            "04 Surface Water – Groundwater Interaction": {
                "page_id": "020400_en",
                "sub": {}
            },
            "05 Hydrological Measurement & Instrumentation": {
                "page_id": "020500_en",
                "sub": {}
            },
        },
    },
    "03 Soil Physics": {
        "page_id": "030000_en",
        "sub": {
            "01 Soil Properties": {
                "page_id": "030100_en",
                "sub": {}
            },
            "02 Soil Water Retention": {
                "page_id": "030200_en",
                "sub": {}
            },
            "03 Unsaturated Flow": {
                "page_id": "030300_en",
                "sub": {}
            },
            "04 Hydraulic Conductivity Functions": {
                "page_id": "030400_en",
                "sub": {}
            },
            "05 Infiltration (Horton, Green–Ampt, Philip)": {
                "page_id": "030500_en",
                "sub": {}
            },
        },
    },
    "04 Basic Hydrogeology": {
        "page_id": "040000_en",
        "sub": {
            "01 Hydrogeological Concepts & Aquifer Types": {
                "page_id": "040100_en",
                "sub": {}
            },
            "02 Hydrogeological Properties": {
                "page_id": "040200_en",
                "sub": {}
            },
            "03 Steady Groundwater Flow": {
                "page_id": "040300_en",
                "sub": {}
            },
            "04 Transient Groundwater Flow": {
                "page_id": "040400_en",
                "sub": {}
            },
            "05 Flow to Wells": {
                "page_id": "040500_en",
                "sub": {}
            },
            "06 Regional Groundwater Flow Systems": {
                "page_id": "040600_en",
                "sub": {}
            },
            "07 Recharge & Discharge Areas (conceptual)": {
                "page_id": "040700_en",
                "sub": {}
            },
            "08 Conceptual Hydrogeological Models": {
                "page_id": "040800_en",
                "sub": {}
            },
        },
    },
    "05 Applied Hydrogeology": {
        "page_id": "050000_en",
        "sub": {
            "01 Groundwater Management": {
                "page_id": "050100_en",
                "sub": {}
            },
            "02 Aquifer Testing": {
                "page_id": "050200_en",
                "sub": {}
            },
            "03 Groundwater in Water Supply (well fields, collector wells, superposition)": {
                "page_id": "050300_en",
                "sub": {}
            },
            "04 Karst Hydrogeology": {
                "page_id": "050400_en",
                "sub": {}
            },
            "05 Freshwater–Saltwater Interaction": {
                "page_id": "050500_en",
                "sub": {}
            },
            "06 Conservative Solute Transport": {
                "page_id": "050600_en",
                "sub": {}
            },
            "07 Reactive Transport": {
                "page_id": "050700_en",
                "sub": {}
            },
            "08 Groundwater Contamination & Remediation": {
                "page_id": "050800_en",
                "sub": {}
            },
            "09 Managed Aquifer Recharge (MAR)": {
                "page_id": "050900_en",
                "sub": {}
            },
            "10 Groundwater–Surface Water Ecology & Dependent Ecosystems": {
                "page_id": "051000_en",
                "sub": {}
            },
            "11 Climate Change Impacts & Groundwater Sustainability": {
                "page_id": "051100_en",
                "sub": {}
            },
            "12 Groundwater Chemistry & Geochemistry": {
                "page_id": "051200_en",
                "sub": {}
            },
            "13 Environmental Tracers & Isotope Hydrogeology": {
                "page_id": "051300_en",
                "sub": {}
            },
            "14 Groundwater Heat Flow & Geothermal Systems": {
                "page_id": "051400_en",
                "sub": {}
            },
            "15 Field & Subsurface Investigation Methods (drilling, logging, geophysics)": {
                "page_id": "051500_en",
                "sub": {}
            },
        },
    },
    "06 Groundwater Modelling": {
        "page_id": "060000_en",
        "sub": {
            "01 Conceptual Model Development": {
                "page_id": "060100_en",
                "sub": {}
            },
            "02 Numerical Schemes (FD, FE, FV)": {
                "page_id": "060200_en",
                "sub": {}
            },
            "03 Flow Modelling": {
                "page_id": "060300_en",
                "sub": {}
            },
            "04 Transport Modelling": {
                "page_id": "060400_en",
                "sub": {}
            },
            "05 Coupled Models (density, heat, CFP)": {
                "page_id": "060500_en",
                "sub": {}
            },
            "06 Parameter Estimation & Calibration": {
                "page_id": "060600_en",
                "sub": {}
            },
            "07 Sensitivity & Uncertainty Analysis": {
                "page_id": "060700_en",
                "sub": {}
            },
            "08 Model Validation & Verification": {
                "page_id": "060800_en",
                "sub": {}
            },
            "09 MODFLOW Packages & Tools": {
                "page_id": "060900_en",
                "sub": {}
            },
            "10 Data-Driven & Machine Learning Approaches": {
                "page_id": "061000_en",
                "sub": {}
            },
            "11 Scenario Analysis & Decision-Support Modelling": {
                "page_id": "061100_en",
                "sub": {}
            },
            "12 Geostatistics & Spatial Variability in Modelling": {
                "page_id": "061200_en",
                "sub": {}
            },
        },
    },
}


NEW_CAT_OPTION = "➕ Define new category"
NEW_SUBCAT_OPTION = "➕ Define new subcategory"
NEW_SUBSUB_OPTION = "➕ Define new sub-subcategory"


# -------------------------------------------------
# HELPER FUNCTIONS
# -------------------------------------------------
def slugify(text: str) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "unknown"


def strip_numeric_prefix(label: str) -> str:
    """
    Removes leading numeric prefixes like '01 ' or '03.2 ' from catalog labels.
    Example: '05 Applied Hydrogeology' -> 'Applied Hydrogeology'
    """
    parts = label.split(" ", 1)
    if len(parts) == 2 and parts[0].replace(".", "").isdigit():
        return parts[1]
    return label


def get_categories():
    return sorted(CATALOG.keys())


def get_subcategories(category: str):
    return sorted(CATALOG[category]["sub"].keys())


def get_subsubcategories(category: str, subcategory: str):
    return sorted(CATALOG[category]["sub"][subcategory]["sub"].keys())


def resolve_page(category: str, subcategory_choice: str, subsub_choice: str):
    """
    Decide which catalog page the resource attaches to.
    Returns (page_id, topic_title_for_yaml).
    """
    cat_entry = CATALOG[category]

    # Category homepage
    if subcategory_choice == "(Category homepage)":
        return cat_entry["page_id"], category

    sub_entry = cat_entry["sub"][subcategory_choice]

    # Attach to subcategory homepage
    if not subsub_choice or subsub_choice == "(Attach to subcategory)":
        return sub_entry["page_id"], subcategory_choice

    # Attach to sub-subcategory page (for future use, currently empty in CATALOG)
    subsub_entry = sub_entry["sub"][subsub_choice]
    return subsub_entry["page_id"], subsub_choice


def build_yaml_text(
    topic_title: str,
    resource_title: str,
    resource_type: str,
    access_url: str,
    description_short: str,
    keywords_list,
    time_required: str,
    prerequisites_text: str,
    fit_for_list,
    authors,                     # list of dicts: {name, affiliation}
    multipage_app: bool,
    num_pages: int,
    interactive_plots: bool,
    num_interactive_plots: int,
    assessments_included: bool,
    num_assessment_questions: int,
    videos_included: bool,
    num_videos: int,
    figures_meta=None,           # list of dicts: {id, original_filename, type, caption}
    references_list=None,        # NEW
    catalog_category=None,       # NEW: for YAML header
    catalog_subcategory=None,    # NEW
    catalog_subsubcategory=None, # NEW
):
    """
    Build YAML as a formatted string matching the template + comments.
    """
    # -------- catalog location header (ALWAYS AT TOP) --------
    catalog_category = catalog_category or "—"
    catalog_subcategory = catalog_subcategory or "—"
    catalog_subsubcategory = catalog_subsubcategory or "—"

    catalog_location_yaml = (
        f'catalog_category: "{catalog_category}"\n'
        f'catalog_subcategory: "{catalog_subcategory}"\n'
        f'catalog_subsubcategory: "{catalog_subsubcategory}"\n\n'
    )

    # keywords inline list: [a, b, c] or [] if empty
    if keywords_list:
        keywords_inline = "[{}]".format(", ".join(keywords_list))
    else:
        keywords_inline = "[]"

    # prerequisites as single string (comma-separated)
    prerequisites_value = (prerequisites_text or "").strip()

    # fit_for as YAML list
    if fit_for_list:
        fit_for_block = "fit_for:\n"
        for item in fit_for_list:
            fit_for_block += f"  - {item}\n"
    else:
        fit_for_block = "fit_for: []\n"

    # description block with ">" style
    desc_lines = (description_short or "").strip().splitlines() or [""]

    desc_block = "description_short: >\n"
    for line in desc_lines:
        desc_block += f"  {line.rstrip()}\n"

    # booleans as lowercase YAML
    multipage_str = str(bool(multipage_app)).lower()
    interactive_plots_str = str(bool(interactive_plots)).lower()
    assessments_str = str(bool(assessments_included)).lower()
    videos_str = str(bool(videos_included)).lower()

    # authors block
    authors_clean = [
        {
            "name": (a.get("name") or "").strip(),
            "affiliation": (a.get("affiliation") or "").strip()
            or "TO_BE_FILLED_BY_COURSE_MANAGER",
        }
        for a in authors
        if (a.get("name") or "").strip()
    ]

    if authors_clean:
        authors_block = "authors:\n"
        for a in authors_clean:
            authors_block += f"  - name: {a['name']}\n"
            authors_block += f"    affiliation: {a['affiliation']}\n"
    else:
        authors_block = "authors: []\n"

    # references block
    references_list = references_list or []
    if references_list:
        refs_block = "references:\n"
        for r in references_list:
            refs_block += f"  - {r}\n"
    else:
        refs_block = "references: []\n"

    yaml_str = catalog_location_yaml + f"""# --- RESOURCE IDENTIFICATION AND TOPIC MAPPING ---
# item_id: A unique, simple slug for this item (e.g., aquifer_test_1). 

item_id: TO_BE_FILLED_BY_COURSE_MANAGER
topic: {topic_title} # Must match the title of the parent catalog page.
title: {resource_title}    # The full, descriptive name of the resource.

# --- TYPE AND ACCESS ---
resource_type: {resource_type}            # Required. Options: Streamlit app, Jupyter Notebook, Video, Dataset, Other.
url: {access_url}      # The direct link to launch the app, notebook on Binder, or video on YouTube.
date_released: TO_BE_FILLED_BY_COURSE_MANAGER               # Release date in YYYY-MM-DD format.

# --- CONTENT AND METADATA ---
{desc_block.rstrip()}
keywords: {keywords_inline}
multipage_app: {multipage_str}
num_pages: {num_pages}
interactive_plots: {interactive_plots_str}
num_interactive_plots: {num_interactive_plots}
assessments_included: {assessments_str}
num_assessment_questions: {num_assessment_questions}
videos_included: {videos_str}
num_videos: {num_videos}

# --- EDUCATIONAL FIT ---
time_required: {time_required}             # Estimated time for a student to complete the activity (e.g., 30 minutes, 1.5 hours).
prerequisites: {prerequisites_value}       # Required prior knowledge (e.g., Darcy's Law, Python basics, basic calculus).
{fit_for_block.rstrip()}

# --- AUTHOR AND REFERENCE ---
{authors_block.rstrip()}
{refs_block.rstrip()}                            # List any published papers, DOIs, or source materials related to this resource.
# image_url: Optional path to a screenshot for the catalog page (e.g., /assets/images/resources/flow_tool_screenshot.png)
"""

    # --- FIGURES (OPTIONAL) ---
    figures_meta = figures_meta or []
    if figures_meta:
        yaml_str += "\nfigures:\n"
        for fig in figures_meta:
            fid = fig.get("id")
            orig = fig.get("original_filename", "")
            ftype = (fig.get("type") or "").strip()
            fcap = (fig.get("caption") or "").strip()
            is_cover = fig.get("is_cover")  # NEW: cover flag from the app

            yaml_str += f"  - id: {fid}\n"
            if orig:
                yaml_str += f"    original_filename: {orig}\n"
            if ftype:
                yaml_str += f"    type: {ftype}\n"
            if fcap:
                yaml_str += f"    caption: {fcap}\n"
            if is_cover:                     # NEW: only write if True
                yaml_str += "    is_cover: true\n"
    else:
        yaml_str += "\nfigures: []\n"

    return yaml_str



def apply_language_to_prefix(prefix: str, lang_code: str) -> str:
    """
    Ensure the filename prefix clearly shows the language of the submitted resource.
    """
    lang_codes = set(LANGUAGE_OPTIONS.values())
    parts = prefix.split("_")
    if parts and parts[-1] in lang_codes:
        existing_lang = parts[-1]
        core = "_".join(parts[:-1]) if len(parts) > 1 else ""

        if existing_lang == lang_code:
            return prefix
        else:
            if core:
                return f"{core}_{existing_lang}_{lang_code}"
            else:
                return f"{existing_lang}_{lang_code}"
    else:
        return f"{prefix}_{lang_code}"


# YAML → PDF
def yaml_to_pdf_bytes(yaml_text: str, language_label: str, uploaded_figures=None) -> bytes:
    """
    Create a nicely formatted A4 PDF 'resource sheet' from the YAML text.
    Uses a structured layout (sections, tables, figure section).
    """
    data = yaml.safe_load(yaml_text) or {}

    buffer = BytesIO()

    # --- Document setup ---
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    project_style = ParagraphStyle(
        "ProjectHeader",
        parent=styles["Normal"],
        fontSize=11,
        leading=14,
        textColor=colors.black,
        spaceAfter=4,
    )
    title_style = ParagraphStyle(
        "ResourceTitle",
        parent=styles["Heading1"],
        fontSize=18,
        leading=22,
        spaceAfter=8,
    )
    label_style = ParagraphStyle(
        "Label",
        parent=styles["Normal"],
        fontSize=10,
        leading=12,
        textColor=colors.black,
    )
    section_style = ParagraphStyle(
        "SectionTitle",
        parent=styles["Heading2"],
        fontSize=13,
        leading=16,
        spaceBefore=10,
        spaceAfter=4,
    )
    caption_style = ParagraphStyle(
        "FigureCaption",
        parent=styles["Normal"],
        fontSize=9,
        leading=11,
        italic=True,
        alignment=1,   # center
        spaceBefore=2,
        spaceAfter=0,
    )


    def yn(val):
        if val is True:
            return "Yes"
        if val is False:
            return "No"
        if val in (None, "", [], {}):
            return "—"
        return str(val)

    story = []

    # ---------- COVER PAGE ----------
    cover_title_style = ParagraphStyle(
        "CoverTitle",
        parent=styles["Heading1"],
        fontSize=24,
        leading=28,
        alignment=1,        # centered
        spaceAfter=12,
    )
    cover_subtitle_style = ParagraphStyle(
        "CoverSubtitle",
        parent=styles["Heading2"],
        fontSize=14,
        leading=18,
        alignment=1,        # centered
        textColor=colors.black,
        spaceAfter=6,
    )

    # Space down to roughly the middle
    story.append(Spacer(1, 60 * mm))
    story.append(Paragraph("iNUX Groundwater", cover_title_style))
    story.append(Paragraph("An Erasmus+ Project", cover_subtitle_style))
    story.append(Spacer(1, 20 * mm))
    story.append(Paragraph("Resource description sheet", cover_subtitle_style))

    story.append(Image("FIGS/iNUX_wLogo.png", width=40*mm, height=40*mm))
    ##story.append(Image("assets/images/inux_logo.png", width=40*mm, height=40*mm))

    # NOTE: Here you could later add an Image() for the iNUX logo if you have a file path.
    # e.g. story.append(Image("path/to/inux_logo.png", width=40*mm, height=40*mm))

    # Move to next page for the actual content
    story.append(PageBreak())


    # -------- HEADER / TITLE BLOCK --------
    raw_title = data.get("title") or "Untitled resource"
    title = str(raw_title)

    topic = str((data.get("topic") or "—") or "—")
    raw_item_id = (data.get("item_id") or "").strip()
    show_item_id = bool(raw_item_id) and "TO_BE_FILLED" not in raw_item_id.upper()

    story.append(
        Paragraph(
            "iNUX – Interactive Understanding of Groundwater Hydrology and Hydrogeology",
            project_style,
        )
    )
    story.append(Paragraph(title, title_style))
    story.append(Paragraph(f"<b>Topic:</b> {topic}", label_style))
    story.append(Paragraph(f"<b>Language:</b> {language_label}", label_style))
    if show_item_id:
        story.append(Paragraph(f"<b>Item ID:</b> {raw_item_id}", label_style))
    story.append(Spacer(1, 8))

    # -------- 1. BASIC INFORMATION --------
    story.append(Paragraph("1. Basic information", section_style))

    basic_data = [
        ["Resource type", data.get("resource_type", "—")],
        ["URL", data.get("url", "—")],
        ["Date released", data.get("date_released", "TO_BE_FILLED_BY_COURSE_MANAGER")],
        ["Time required", data.get("time_required", "—")],
    ]
    basic_table = Table(basic_data, colWidths=[45 * mm, 115 * mm])
    basic_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("BOX", (0, 0), (-1, -1), 0.25, colors.grey),
                ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
            ]
        )
    )
    story.append(basic_table)
    story.append(Spacer(1, 6))

    # -------- 2. PEDAGOGICAL OVERVIEW --------
    story.append(Paragraph("2. Pedagogical overview", section_style))

    desc = (data.get("description_short") or "").strip()
    if desc:
        story.append(Paragraph("<b>Short description</b>", label_style))
        story.append(Paragraph(desc, styles["Normal"]))
        story.append(Spacer(1, 4))

    keywords = data.get("keywords", [])
    if isinstance(keywords, list) and keywords:
        kw_text = ", ".join(str(k) for k in keywords)
    elif isinstance(keywords, str) and keywords.strip():
        kw_text = keywords
    else:
        kw_text = "—"

    fit_for = data.get("fit_for", [])
    if isinstance(fit_for, list) and fit_for:
        fit_for_text = ", ".join(str(x) for x in fit_for)
    else:
        fit_for_text = "—"

    story.append(Paragraph(f"<b>Keywords:</b> {kw_text}", label_style))
    story.append(Paragraph(f"<b>Best suited for:</b> {fit_for_text}", label_style))
    story.append(Spacer(1, 6))

    # -------- 3. TECHNICAL DETAILS --------
    story.append(Paragraph("3. Technical details", section_style))

    tech_data = []

    # Multipage app
    multipage = data.get("multipage_app")
    num_pages_val = data.get("num_pages")
    if multipage:
        # Only show if True, and combine with number of pages
        pages_str = str(num_pages_val) if num_pages_val not in (None, "", 0) else "unknown"
        tech_data.append(["Multipage app", f" approximately {pages_str} page(s)"])

    # Interactive plots
    interactive = data.get("interactive_plots")
    num_ip_val = data.get("num_interactive_plots")
    if interactive:
        ip_str = str(num_ip_val) if num_ip_val not in (None, "", 0) else "unknown number of"
        tech_data.append(["Interactive plots", f" {ip_str} interactive plot(s)"])

    # Assessments included
    assessments = data.get("assessments_included")
    num_q_val = data.get("num_assessment_questions")
    if assessments:
        q_str = str(num_q_val) if num_q_val not in (None, "", 0) else "unknown number of"
        tech_data.append(["Assessments", f" {q_str} question(s)"])

    # Videos included
    videos = data.get("videos_included")
    num_vid_val = data.get("num_videos")
    if videos:
        v_str = str(num_vid_val) if num_vid_val not in (None, "", 0) else "unknown number of"
        tech_data.append(["Videos", f"{v_str} video(s)"])

    # Fallback row if nothing was reported
    if not tech_data:
        tech_data = [["No additional technical features reported", "—"]]

    tech_table = Table(tech_data, colWidths=[60 * mm, 100 * mm])

    tech_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("BOX", (0, 0), (-1, -1), 0.25, colors.grey),
                ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
            ]
        )
    )
    story.append(tech_table)
    story.append(Spacer(1, 6))

    # -------- 4. EDUCATIONAL FIT --------
    story.append(Paragraph("4. Educational fit", section_style))

    time_required = data.get("time_required", "—")
    prereq = data.get("prerequisites", "—")

    edu_data = [
        ["Time required", time_required],
        ["Prerequisites", prereq],
        ["Best suited for", fit_for_text],
    ]
    edu_table = Table(edu_data, colWidths=[60 * mm, 100 * mm])
    edu_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("BOX", (0, 0), (-1, -1), 0.25, colors.grey),
                ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
            ]
        )
    )
    story.append(edu_table)
    story.append(Spacer(1, 6))

    # -------- 5. AUTHORS & REFERENCES --------
    story.append(Paragraph("5. Authors & references", section_style))

    authors_list = data.get("authors", [])
    if authors_list:
        story.append(Paragraph("<b>Authors</b>", label_style))
        for a in authors_list:
            name = a.get("name", "Unknown")
            aff = a.get("affiliation", "")
            line = name
            if aff:
                line += f" ({aff})"
            story.append(Paragraph(f"• {line}", styles["Normal"]))
        story.append(Spacer(1, 4))
    else:
        story.append(Paragraph("No authors provided.", styles["Normal"]))
        story.append(Spacer(1, 4))

    refs = data.get("references", [])
    story.append(Paragraph("<b>References</b>", label_style))
    if refs:
        for r in refs:
            story.append(Paragraph(f"– {r}", styles["Normal"]))
    else:
        story.append(Paragraph("No references provided.", styles["Normal"]))
    story.append(Spacer(1, 8))

    # -------- 6. FIGURES & ILLUSTRATIONS (OPTIONAL) --------
    figures_info = data.get("figures") or []
    uploaded_figures = uploaded_figures or []

    if uploaded_figures:
        story.append(Paragraph("6. Figures and illustrations", section_style))
        story.append(Spacer(1, 4))

        for idx, fig_file in enumerate(uploaded_figures, start=1):
            info = figures_info[idx - 1] if idx - 1 < len(figures_info) else {}

            ftype = (info.get("type") or "").strip()
            fcap = (info.get("caption") or "").strip()

            # Build nice caption text:
            # Figure 1. Caption text (Screenshot)
            # or Figure 1. Uploaded image 1 (Photo), etc.
            if not fcap:
                base_caption = f"Uploaded image {idx}"
            else:
                base_caption = fcap

            media_suffix = f" ({ftype})" if ftype else ""
            caption_text = f"Figure {idx}. {base_caption}{media_suffix}"

            try:
                img = Image(BytesIO(fig_file.getvalue()))
                img._restrictSize(160 * mm, 90 * mm)  # max width/height


                # Table with 2 rows: [image], [caption]
                fig_table = Table(
                    [[img], [Paragraph(caption_text, caption_style)]],
                    colWidths=[160 * mm],
                )
                fig_table.setStyle(
                    TableStyle(
                        [
                            ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),  # border
                            ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
                            ("ALIGN", (0, 0), (-1, 0), "CENTER"),       # center image
                            ("ALIGN", (0, 1), (-1, 1), "CENTER"),       # center caption
                            ("TOPPADDING", (0, 0), (-1, -1), 4),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ]
                    )
                )

                story.append(fig_table)

            except Exception:
                # If the image cannot be loaded, still show the caption as text
                story.append(Paragraph(caption_text, caption_style))

            story.append(Spacer(1, 10))


    # ---------- HEADER & FOOTER DRAWING FUNCTION ----------
    def add_header_footer(canvas, doc_):
        page_num = canvas.getPageNumber()
        width, height = A4
        margin = 20 * mm

        # No header/footer on the cover page (page 1)
        if page_num == 1:
            return

        # ----- Header (even pages only) -----
        if page_num % 2 == 0:
            header_y = height - 15 * mm
            canvas.setFont("Helvetica", 9)
            header_text = "iNUX Groundwater - An Erasmus+ Project"
            canvas.drawCentredString(width / 2.0, header_y, header_text)
            # thin line under header
            canvas.setLineWidth(0.5)
            canvas.line(margin, header_y - 2 * mm, width - margin, header_y - 2 * mm)

        # ----- Footer (all pages from 2 onward) -----
        footer_y = 15 * mm
        canvas.setFont("Helvetica", 9)

        # Logical page number: start counting content from 1 on physical page 2
        logical_page_num = page_num - 1
        page_label = str(logical_page_num)

        # thin line above footer
        canvas.setLineWidth(0.5)
        canvas.line(margin, footer_y + 3 * mm, width - margin, footer_y + 3 * mm)

        # page number at bottom center
        canvas.drawCentredString(width / 2.0, footer_y, page_label)

    # --- Build PDF with header/footer ---
    doc.build(
        story,
        onFirstPage=add_header_footer,   # will skip header/footer internally for page 1
        onLaterPages=add_header_footer,
    )

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# -------------------------------------------------
# STREAMLIT UI
# -------------------------------------------------
st.set_page_config(page_title="CataLogger", page_icon="📦", layout="centered")

st.title("Cata:green[Logger] 📦")
st.subheader(
    "iNUX Resource YAML Generator ➤ Register Interactive Documents for the iNUX Catalog",
    divider="rainbow",
)

st.markdown(
    """
    Use this form to propose a new **teaching resource** for the iNUX catalog. The subsequent mask collects all required information.
    
    At the end, you can download a YAML (txt) file that contains all data, and send it to the catalog editors for further processing.
    """
)

# --- initialise session_state flags -----------------------------------
if "form_done" not in st.session_state:
    st.session_state["form_done"] = False
if "ready_for_download" not in st.session_state:
    st.session_state["ready_for_download"] = False
if "show_preview_flag" not in st.session_state:
    st.session_state["show_preview_flag"] = True
if "authors_count" not in st.session_state:
    st.session_state["authors_count"] = 1   # start with 1 author by default

# -------------------------------------------------
# LANGUAGE DROPDOWN
# -------------------------------------------------
st.header("🌐 Language of the resource")
language_label = st.selectbox(
    "Select the main language of this resource",
    list(LANGUAGE_OPTIONS.keys()),
    index=0,  # default: English
)
lang_code = LANGUAGE_OPTIONS[language_label]

# --------- 1. LOCATION IN THE CATALOG (PROGRESSIVE) -------------------
st.header("1️⃣ Choose the topic area")

categories = get_categories()
category_options = categories + [NEW_CAT_OPTION]
category_choice = st.selectbox("Category", category_options)

# Flags + names for new elements
new_category_mode = category_choice == NEW_CAT_OPTION
new_category_name = ""
new_subcategory_under_newcat = ""
new_subsub_under_newcat = ""

new_subcategory_mode = False
new_subcategory_name = ""
new_subsub_under_newsub = ""

new_subsub_existing_mode = False
new_subsub_under_existing = ""

subcategory_choice = "(Category homepage)"
subsub_choice = ""

if new_category_mode:
    # Completely new category path
    new_category_name = st.text_input("Name of new category", "")

    define_sub_for_new_cat = st.checkbox(
        "Also define a subcategory for this new category?", value=False
    )
    if define_sub_for_new_cat:
        new_subcategory_under_newcat = st.text_input(
            "Name of new subcategory", ""
        )
        define_subsub_for_new_cat = st.checkbox(
            "Also define a sub-subcategory under this new subcategory?", value=False
        )
        if define_subsub_for_new_cat:
            new_subsub_under_newcat = st.text_input(
                "Name of new sub-subcategory", ""
            )

else:
    # Existing category workflow
    category = category_choice  # just rename for clarity
    sub_keys = get_subcategories(category)

    if sub_keys:
        subcat_options = ["(Category homepage)"] + sub_keys + [NEW_SUBCAT_OPTION]
        subcategory_choice_raw = st.selectbox("Subcategory", subcat_options)

        if subcategory_choice_raw == NEW_SUBCAT_OPTION:
            new_subcategory_mode = True
            subcategory_choice = "(Category homepage)"  # backend attach
            new_subcategory_name = st.text_input("Name of new subcategory", "")
            define_subsub_for_new_sub = st.checkbox(
                "Also define a new sub-subcategory under this new subcategory?",
                value=False,
            )
            if define_subsub_for_new_sub:
                new_subsub_under_newsub = st.text_input(
                    "Name of new sub-subcategory", ""
                )
        else:
            subcategory_choice = subcategory_choice_raw
    else:
        # No subcategories exist yet
        st.info("This category has no subcategories yet. You can define one below.")
        new_subcategory_mode = True
        subcategory_choice = "(Category homepage)"
        new_subcategory_name = st.text_input("Name of new subcategory", "")
        define_subsub_for_new_sub = st.checkbox(
            "Also define a new sub-subcategory under this new subcategory?",
            value=False,
        )
        if define_subsub_for_new_sub:
            new_subsub_under_newsub = st.text_input(
                "Name of new sub-subcategory", ""
            )

    # Sub-subcategory selection when using an existing subcategory
    if (not new_subcategory_mode) and (subcategory_choice not in ["(Category homepage)"]):
        subsub_keys = get_subsubcategories(category, subcategory_choice)
        subsub_options = ["(Attach to subcategory)"] + subsub_keys + [NEW_SUBSUB_OPTION]

        subsub_choice_raw = st.selectbox("Sub-subcategory (optional)", subsub_options)
        if subsub_choice_raw == NEW_SUBSUB_OPTION:
            new_subsub_existing_mode = True
            subsub_choice = "(Attach to subcategory)"  # backend attach
            new_subsub_under_existing = st.text_input(
                "Name of new sub-subcategory", ""
            )
        else:
            subsub_choice = subsub_choice_raw

# --------- 2. RESOURCE DETAILS ---------------------------------------
st.header("2️⃣ Describe your submission")

# Title (outside form is fine)
resource_title = st.text_input("Title of the resource", "")

# Submission type – OUTSIDE form so it updates immediately
submission_type = st.selectbox(
    "Submission type",
    [
        "Streamlit app",
        "Jupyter Notebook",
        "Other",
    ],
)

# ----- Streamlit-specific questions (conditional, directly under type) -----
multipage_app = False
num_pages = 0
interactive_plots = False
num_interactive_plots = 0
assessments_included = False
num_assessment_questions = 0
videos_included = False
num_videos = 0

if submission_type == "Streamlit app":
    st.markdown("#### Additional details for Streamlit app")

    multipage_app = st.checkbox("Is this a multipage Streamlit app?", value=False)
    if multipage_app:
        num_pages = st.number_input(
            "Approximate number of pages",
            min_value=1,
            step=1,
            value=2,
        )

    interactive_plots = st.checkbox(
        "Does the app contain interactive plots?",
        value=False,
    )
    if interactive_plots:
        num_interactive_plots = st.number_input(
            "Approximate number of interactive plots",
            min_value=1,
            step=1,
            value=1,
        )

    assessments_included = st.checkbox(
        "Does the app include assessments (questions)?",
        value=False,
    )
    if assessments_included:
        num_assessment_questions = st.number_input(
            "Approximate number of assessment questions",
            min_value=1,
            step=1,
            value=1,
        )

    videos_included = st.checkbox(
        "Does the app include embedded video / tutorials?",
        value=False,
    )
    if videos_included:
        num_videos = st.number_input(
            "Approximate number of videos",
            min_value=1,
            step=1,
            value=1,
        )

# --------- AUTHORS (MULTI-AUTHOR SUPPORT) -----------------------------
st.subheader("Author(s)")

authors = []
for i in range(st.session_state["authors_count"]):
    idx = i + 1
    name = st.text_input(f"Author {idx} name", key=f"author_name_{i}")
    affiliation = st.text_input(
        f"Author {idx} affiliation",
        key=f"author_aff_{i}",
        help="Institute / organisation (can be the same for multiple authors).",
    )
    authors.append({"name": name, "affiliation": affiliation})

col_add, col_remove, spacer1, spacer2 = st.columns([1, 1, 1, 1])

with col_add:
    if st.button("➕ Add author", help="Click to insert another author row"):
        if st.session_state["authors_count"] < 10:
            st.session_state["authors_count"] += 1
            st.rerun()

with col_remove:
    remove_disabled = st.session_state["authors_count"] <= 1
    if st.button("➖ Remove author", disabled=remove_disabled,
                 help="Remove the last author row"):
        if st.session_state["authors_count"] > 1:
            st.session_state["authors_count"] -= 1
            last_idx = st.session_state["authors_count"]
            st.session_state.pop(f"author_name_{last_idx}", None)
            st.session_state.pop(f"author_aff_{last_idx}", None)
            st.rerun()

# --------- 3. OTHER DETAILS (NO FORM) --------------------------------
st.header("3️⃣ Resource details")

# Access URL
access_url = st.text_input(
    "Access link (URL)",
    help="Link to the Streamlit app, notebook repository, shared drive folder, video, etc.",
)

# Estimated time required
time_presets = [
    "5–15 min",
    "15–30 minutes",
    "30–45 minutes",
    "1 hour",
    "1.5 hours",
    "2 hours",
    "Custom",
]
time_choice = st.selectbox("Estimated time required", time_presets, index=1)
if time_choice == "Custom":
    time_required = st.text_input("Custom time description", "")
else:
    time_required = time_choice

# Short description
description_short = st.text_area(
    "Short description (1–2 paragraphs)",
    height=150,
)

# Keywords (comma-separated)
keywords_text = st.text_input(
    "Keywords (comma-separated)",
    "",
    help="Example: groundwater, solute transport, advection",
)

# Best suited for
fit_for_options = [
    "classroom teaching",
    "online teaching",
    "self learning",
    "exam preparation",
]
fit_for = st.multiselect(
    "Best suited for",
    fit_for_options,
    default=["self learning"],
)

# Prerequisites (comma-separated)
prereq_text = st.text_input(
    "Prerequisites (comma-separated, optional)",
    "",
    help="Example: Darcy's law, Python basics",
)

# References (one per line)
references_text = st.text_area(
    "References (one per line, optional)",
    "",
    help="Include DOIs, papers, datasets, or other materials related to this resource.",
)


# --------- 4. FIGURES UPLOAD + METADATA (AT THE END) -----------------
uploaded_figures = st.file_uploader(
    "Optional figures (PNG/JPG) that will be bundled with the YAML and included in the PDF. You may upload multiple files.",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True,
)

figure_inputs = []
if uploaded_figures:
    st.markdown("##### Figure details (optional)")
    st.caption(
        "For each uploaded image, you can optionally specify the type and a short caption. "
        "If you leave these empty, the PDF will still include the images with generic labels."
    )

    FIGURE_TYPE_OPTIONS = [
        "(not specified)",
        "Schematic / Diagram / Illustration",
        "Screenshot",
        "Photo",
        "Other",
    ]

    for i, fig in enumerate(uploaded_figures, start=1):
        st.markdown(f"**Image {i}:** `{fig.name}`")
        fig_type = st.selectbox(
            f"Type for image {i}",
            FIGURE_TYPE_OPTIONS,
            index=0,
            key=f"fig_type_{i}",
        )
        fig_caption = st.text_input(
            f"Caption for image {i} (optional)",
            key=f"fig_caption_{i}",
        )

         # NEW: let the user mark this image as the cover for the catalog page
        fig_is_cover = st.checkbox(
            f"Use image {i} as cover image for the catalog page",
            key=f"fig_is_cover_{i}",
            help="If multiple are checked, the generator will use the first one."
        )

        figure_inputs.append(
            {
                "id": i,
                "original_filename": fig.name,
                "type": fig_type if fig_type != "(not specified)" else "",
                "caption": fig_caption.strip(),
                 "is_cover": fig_is_cover,
            }
        )

# --------- 5. PREVIEW TOGGLE + SUBMIT BUTTON (BOTTOM) ----------------
st.header("4️⃣ Preview and generate")

show_preview = st.checkbox(
    "🔍 Show preview before download",
    value=st.session_state["show_preview_flag"],
    help="If checked, a summary of your entry will appear before the download is created.",
)
submit_clicked = st.button("Submit / Generate YAML")

if submit_clicked:
    st.session_state["form_done"] = True
    st.session_state["show_preview_flag"] = show_preview
    st.session_state["ready_for_download"] = not show_preview

# If user hasn't submitted yet, stop here
if not st.session_state["form_done"]:
    st.stop()

# --------- 6. BUILD YAML STRING & FILENAME PREFIX --------------------

# Process keywords for inline list
keywords_list = [k.strip() for k in keywords_text.split(",") if k.strip()]

# Process references (one per line)
references_list = [r.strip() for r in references_text.splitlines() if r.strip()]


# Decide topic_title and hierarchy_base (for filename)
if new_category_mode:
    # D. Completely new category
    topic_title = (new_category_name or "TO_BE_FILLED_BY_COURSE_MANAGER").strip()
    cat_slug = slugify(new_category_name or "new-category")
    parts = [cat_slug]
    if new_subcategory_under_newcat.strip():
        parts.append(slugify(new_subcategory_under_newcat))
        if new_subsub_under_newcat.strip():
            parts.append(slugify(new_subsub_under_newcat))
    hierarchy_base = "_".join(parts)

else:
    # Existing category path
    category_name = category_choice  # existing

    if new_subcategory_mode:
        # B. Existing category, new subcategory (+ optional new sub-sub)
        # keep page_id resolution for potential future use; topic_title should be the new subcategory
        page_id, _ = resolve_page(category_name, "(Category homepage)", "")
        topic_title = (new_subcategory_name or "TO_BE_FILLED_BY_COURSE_MANAGER").strip()
        cat_prefix = CATALOG[category_name]["page_id"][:2]  # e.g. "050000_en" -> "05"
        parts = [cat_prefix, slugify(new_subcategory_name or "new-subcategory")]
        if new_subsub_under_newsub.strip():
            parts.append(slugify(new_subsub_under_newsub))
        hierarchy_base = "_".join(parts)

    elif new_subsub_existing_mode:
        # C. Existing category + existing subcategory, new sub-sub
        page_id, _ = resolve_page(
            category_name, subcategory_choice, "(Attach to subcategory)"
        )
        topic_title = (new_subsub_under_existing or "TO_BE_FILLED_BY_COURSE_MANAGER").strip()
        sub_prefix = CATALOG[category_name]["sub"][subcategory_choice]["page_id"][:4]
        parts = [sub_prefix, slugify(new_subsub_under_existing or "new-sub-subcategory")]
        hierarchy_base = "_".join(parts)

    else:
        # A. All existing (category / subcategory / sub-subcategory)
        page_id, topic_title = resolve_page(
            category_name, subcategory_choice, subsub_choice
        )
        hierarchy_base = page_id  # e.g. "050400_en"

# --- compute catalog labels for YAML (same logic as preview) ---
if new_category_mode:
    catalog_category = (
        f"{new_category_name} (proposed)" if (new_category_name or "").strip() else "—"
    )
    if (new_subcategory_under_newcat or "").strip():
        catalog_subcategory = f"{new_subcategory_under_newcat} (proposed)"
    else:
        catalog_subcategory = "—"
    if (new_subsub_under_newcat or "").strip():
        catalog_subsubcategory = f"{new_subsub_under_newcat} (proposed)"
    else:
        catalog_subsubcategory = "—"
else:
    catalog_category = category_name
    if new_subcategory_mode and (new_subcategory_name or "").strip():
        catalog_subcategory = f"{new_subcategory_name} (proposed)"
    else:
        catalog_subcategory = subcategory_choice

    if new_subsub_existing_mode and (new_subsub_under_existing or "").strip():
        catalog_subsubcategory = f"{new_subsub_under_existing} (proposed)"
    elif (new_subsub_under_newsub or "").strip():
        catalog_subsubcategory = f"{new_subsub_under_newsub} (proposed)"
    else:
        catalog_subsubcategory = subsub_choice or "—"
    
    

yaml_text = build_yaml_text(
    topic_title=strip_numeric_prefix(topic_title),
    resource_title=resource_title,
    resource_type=submission_type,
    access_url=access_url,
    description_short=description_short,
    keywords_list=keywords_list,
    time_required=time_required,
    prerequisites_text=prereq_text,
    fit_for_list=fit_for,
    authors=authors,
    multipage_app=multipage_app if submission_type == "Streamlit app" else False,
    num_pages=int(num_pages) if submission_type == "Streamlit app" else 0,
    interactive_plots=interactive_plots if submission_type == "Streamlit app" else False,
    num_interactive_plots=int(num_interactive_plots)
    if submission_type == "Streamlit app"
    else 0,
    assessments_included=assessments_included if submission_type == "Streamlit app" else False,
    num_assessment_questions=int(num_assessment_questions) if submission_type == "Streamlit app" else 0,
    videos_included=videos_included if submission_type == "Streamlit app" else False,
    num_videos=int(num_videos) if submission_type == "Streamlit app" else 0,
    figures_meta=figure_inputs,
    references_list=references_list,   # NEW
    catalog_category=catalog_category,
    catalog_subcategory=catalog_subcategory,
    catalog_subsubcategory=catalog_subsubcategory,
)



# Apply language logic to hierarchy_base
prefix_with_lang = apply_language_to_prefix(hierarchy_base, lang_code)

# Final filename
first_author_name = next((a["name"] for a in authors if (a["name"] or "").strip()), "")
author_slug = slugify(first_author_name or "unknown")
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
base_name = f"{prefix_with_lang}_{author_slug}_{timestamp}"
filename = f"{base_name}.yaml"

# --------- 7. PREVIEW SECTION (IF ENABLED) ---------------------------
if st.session_state["show_preview_flag"]:
    st.header("5️⃣ Preview your entry")

    # --- compute display labels for catalog location (proposed) ---
    if new_category_mode:
        display_category = (
            f"{new_category_name} (proposed)" if (new_category_name or "").strip() else "—"
        )
        if (new_subcategory_under_newcat or "").strip():
            display_subcategory = f"{new_subcategory_under_newcat} (proposed)"
        else:
            display_subcategory = "—"
        if (new_subsub_under_newcat or "").strip():
            display_subsub = f"{new_subsub_under_newcat} (proposed)"
        else:
            display_subsub = "—"
    else:
        display_category = category_name
        if new_subcategory_mode and (new_subcategory_name or "").strip():
            display_subcategory = f"{new_subcategory_name} (proposed)"
        else:
            display_subcategory = subcategory_choice

        if new_subsub_existing_mode and (new_subsub_under_existing or "").strip():
            display_subsub = f"{new_subsub_under_existing} (proposed)"
        elif (new_subsub_under_newsub or "").strip():
            display_subsub = f"{new_subsub_under_newsub} (proposed)"
        else:
            display_subsub = subsub_choice or "—"

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Catalog location")
        st.markdown(
            f"""
- **Category:** {display_category}  
- **Subcategory:** {display_subcategory}  
- **Sub-subcategory:** {display_subsub}
"""
        )

        st.markdown("#### Resource overview")
        st.markdown(
            f"""
- **Language:** {language_label} ({lang_code})  
- **Title:** {resource_title or '—'}  
- **Type:** {submission_type}  
- **Access URL:** {access_url or '—'}  
- **Estimated time:** {time_required or '—'}
"""
        )

        if submission_type == "Streamlit app":
            st.markdown("#### Streamlit app details")
            st.markdown(
                f"""
- **Multipage app:** {"yes" if multipage_app else "no"}  
- **Number of pages:** {int(num_pages) if multipage_app else "—"}  
- **Interactive plots:** {"yes" if interactive_plots else "no"}  
- **Number of interactive plots:** {int(num_interactive_plots) if interactive_plots else "—"}  
- **Assessments included:** {"yes" if assessments_included else "no"}  
- **Number of assessment questions:** {int(num_assessment_questions) if assessments_included else "—"}  
- **Videos included:** {"yes" if videos_included else "no"}  
- **Number of videos:** {int(num_videos) if videos_included else "—"}
"""
            )

        st.markdown("#### Educational fit")
        pretty_fit_for = ", ".join(fit_for) if fit_for else "—"
        st.markdown(
            f"""
- **Best suited for:** {pretty_fit_for}  
- **Prerequisites:** {prereq_text or 'None specified'}
"""
        )

    with col2:
        st.markdown("#### Description")
        if (description_short or "").strip():
            st.write(description_short)
        else:
            st.caption("No description provided yet.")

        st.markdown("#### Keywords")
        pretty_keywords = ", ".join(keywords_list) if keywords_list else "—"
        st.markdown(f"{pretty_keywords}")

        st.markdown("#### Authors")
        if any((a["name"] or "").strip() for a in authors):
            for a in authors:
                if (a["name"] or "").strip():
                    st.markdown(
                        f"- **Name:** {a['name']}  \n"
                        f"  **Affiliation:** {a['affiliation'] or '—'}"
                    )
        else:
            st.markdown("—")

        
        st.markdown("#### References")
        if references_list:
            for ref in references_list:
                st.markdown(f"- {ref}")
        else:
            st.markdown("—")


        if uploaded_figures:
            st.markdown("#### Figure preview (uploaded)")
            for i, fig in enumerate(uploaded_figures, start=1):
                st.image(
                    fig,
                    caption=f"Uploaded figure {i}: {fig.name}",
                    use_container_width=True,
                )

    st.info(
        "If everything looks correct, click the button below to create the downloadable file. "
        "If you need to change something, edit the fields above and click **Submit / Generate YAML** again."
    )

    if st.button("✅ Looks good – create download file"):
        st.session_state["ready_for_download"] = True

    if not st.session_state["ready_for_download"]:
        st.stop()

# --------- 8. YAML & PDF DOWNLOAD -----------------------------------
st.header("6️⃣ Generated YAML & download")
st.code(yaml_text, language="yaml")

# Build PDF bytes (figures included if any)
pdf_bytes = yaml_to_pdf_bytes(yaml_text, language_label, uploaded_figures)
pdf_filename = filename.replace(".yaml", ".pdf")

if uploaded_figures:
    # Create ZIP in memory with YAML + all figures
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add YAML
        zf.writestr(filename, yaml_text)

        # Add figures with systematic names based on base_name
        for i, fig in enumerate(uploaded_figures, start=1):
            fig_ext = fig.name.split(".")[-1].lower()
            fig_filename = f"{base_name}_fig{i}.{fig_ext}"
            zf.writestr(fig_filename, fig.getvalue())

    zip_buffer.seek(0)

    st.download_button(
        label=f"⬇️ Download ZIP (YAML + {len(uploaded_figures)} figure(s)) as {base_name}.zip",
        data=zip_buffer,
        file_name=f"{base_name}.zip",
        mime="application/zip",
    )
else:
    # Fallback: only YAML
    st.download_button(
        label=f"⬇️ Download YAML as {filename}",
        data=yaml_text,
        file_name=filename,
        mime="text/yaml",
    )

# PDF download button (always available)
st.download_button(
    label=f"⬇️ Download PDF as {pdf_filename}",
    data=pdf_bytes,
    file_name=pdf_filename,
    mime="application/pdf",
)

st.success("File created. Please download it and send it to the course manager for review.")
