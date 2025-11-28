import streamlit as st
import re
from datetime import datetime  # for timestamp in filename
import io
import zipfile

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
        "sub": {}
    },
    "02 Basic Hydrology": {
        "page_id": "020000_en",
        "sub": {}
    },
    "03 Soil Physics": {
        "page_id": "030000_en",
        "sub": {
            "01 Soil Properties": {"page_id": "030100_en", "sub": {}},
            "02 Soil moisture retention": {"page_id": "030200_en", "sub": {}},
            "03 Unsaturated Flow": {"page_id": "030300_en", "sub": {}},
        },
    },
    "04 Basic Hydrogeology": {
        "page_id": "040000_en",
        "sub": {
            "01 Hydrogeological concepts": {"page_id": "040100_en", "sub": {}},
            "02 Hydrogeological properties": {"page_id": "040200_en", "sub": {}},
            "03 Steady Groundwater movement": {"page_id": "040300_en", "sub": {}},
            "04 Transient Groundwater Movement": {"page_id": "040400_en", "sub": {}},
            "05 Flow to wells": {"page_id": "040500_en", "sub": {}},
        },
    },
    "05 Applied Hydrogeology": {
        "page_id": "050000_en",
        "sub": {
            "01 Groundwater Management": {"page_id": "050100_en", "sub": {}},
            "02 Karst Hydrology": {"page_id": "050200_en", "sub": {}},
            "03 Aquifer Testing": {"page_id": "050300_en", "sub": {}},
            "04 Conservative Transport": {"page_id": "050400_en", "sub": {}},
            "05 Reactive Transport": {"page_id": "050500_en", "sub": {}},
            "06 Freshwater-Saltwater Interaction": {"page_id": "050600_en", "sub": {}},
        },
    },
    "06 Ground Water Modelling": {
        "page_id": "060000_en",
        "sub": {
            "01 Concepts": {"page_id": "060100_en", "sub": {}},
            "02 Numerical Schemes": {"page_id": "060200_en", "sub": {}},
            "03 Flow Modelling": {"page_id": "060300_en", "sub": {}},
            "04 Transport Modelling": {"page_id": "060400_en", "sub": {}},
            "05 Coupled Models": {"page_id": "060500_en", "sub": {}},
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
    author: str,
    author_institute: str,
    multipage_app: bool,
    num_pages: int,
    interactive_plots: bool,
    num_interactive_plots: int,
    assessments_included: bool,
    num_assessment_questions: int,
    videos_included: bool,
    num_videos: int,
):
    """
    Build YAML as a formatted string matching the template + comments.
    """
    # keywords inline list: [a, b, c] or [] if empty
    if keywords_list:
        keywords_inline = "[{}]".format(", ".join(keywords_list))
    else:
        keywords_inline = "[]"

    # prerequisites as single string (comma-separated)
    prerequisites_value = prerequisites_text.strip()

    # fit_for as YAML list
    if fit_for_list:
        fit_for_block = "fit_for:\n"
        for item in fit_for_list:
            fit_for_block += f"  - {item}\n"
    else:
        fit_for_block = "fit_for: []\n"

    # description block with ">" style
    desc_lines = description_short.strip().splitlines() or [""]
    desc_block = "description_short: >\n"
    for line in desc_lines:
        desc_block += f"  {line.rstrip()}\n"

    # author institute: allow empty but still emit line
    author_institute_value = author_institute.strip() or "TO_BE_FILLED_BY_COURSE_MANAGER"

    # booleans as lowercase YAML
    multipage_str = str(multipage_app).lower()
    interactive_plots_str = str(interactive_plots).lower()
    assessments_str = str(assessments_included).lower()
    videos_str = str(videos_included).lower()

    yaml_str = f"""# --- RESOURCE IDENTIFICATION AND TOPIC MAPPING ---
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
author: {author}
author_institute: {author_institute_value}
references: []                            # List any published papers, DOIs, or source materials related to this resource.
# image_url: Optional path to a screenshot for the catalog page (e.g., /assets/images/resources/flow_tool_screenshot.png)
"""
    return yaml_str


def apply_language_to_prefix(prefix: str, lang_code: str) -> str:
    """
    Ensure the filename prefix clearly shows the language of the submitted resource.

    Rules:
    - If prefix already ends with a language code:
        - same as lang_code  -> keep one (en stays en, not en_en)
        - different          -> keep both (en_fr, de_en, etc.)
    - If prefix has no language -> append _{lang_code}
    """
    lang_codes = set(LANGUAGE_OPTIONS.values())
    parts = prefix.split("_")
    if parts and parts[-1] in lang_codes:
        existing_lang = parts[-1]
        core = "_".join(parts[:-1]) if len(parts) > 1 else ""

        if existing_lang == lang_code:
            # en_en -> en, de_de -> de, etc.
            return prefix
        else:
            # en_fr, de_en, etc.
            if core:
                return f"{core}_{existing_lang}_{lang_code}"
            else:
                # edge case: prefix was just "en"
                return f"{existing_lang}_{lang_code}"
    else:
        return f"{prefix}_{lang_code}"


# -------------------------------------------------
# STREAMLIT UI
# -------------------------------------------------
st.title("📦 CataLogger ")
st.subheader("iNUX Resource YAML Generator - Register Interactive Documents for the iNUX Catalog", divider="rainbow")

st.markdown(
    """
    Use this form to propose a new **teaching resource** for the iNUX catalog. The subsequent mask collect all required information.
    
    At the end, you can download a YAML (txt) file that contains all data, and send it to the catalog editors for further processing.
    """
)

# --- initialise session_state flags -----------------------------------
if "form_done" not in st.session_state:
    st.session_state["form_done"] = False
if "ready_for_download" not in st.session_state:
    st.session_state["ready_for_download"] = False

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

# ---- Rest of the inputs in a form (to keep preview + submit flow) ----
with st.form("resource_form"):
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

    # Author
    # ToDo: We should account for several authors; for the moment, a dropdown list will make our life much easier (same principle as categories)
    # We need to account also the different institutions. The optimum solution would be to associate known authors with their institution. Then, the next field for institution is only required for new authors. In the final file (PDF/Catalog) we can write authors/institutions like in all our Apps
    
    author = st.text_input("Name of the author/co-authors", "")
    author_institute = st.text_input("Affiliation (optional)", "")

    # Optional figure upload (multiple files allowed)
    # ToDo can we implement an option to take a screenshot/part of the screen? Or use copy-paste? That would make our life easier.
    uploaded_figures = st.file_uploader(
        "Optional figures (PNG/JPG) to bundle with the YAML",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
    )

    # ---- Preview toggle + submit, side by side ----
    col_btn1, col_btn2 = st.columns([2, 3])
    with col_btn1:
        show_preview = st.checkbox(
            "🔍 Show preview after submit",
            value=True,
            help="If checked, a summary of your entry will appear before the download is created.",
        )
    with col_btn2:
        submitted = st.form_submit_button("Submit/Generate YAML")

    if submitted:
        st.session_state["form_done"] = True
        st.session_state["ready_for_download"] = not show_preview

# TODO We need an option for restart/reset

if not st.session_state["form_done"]:
    st.stop()

# --------- 3. BUILD YAML STRING & FILENAME PREFIX --------------------

# Process keywords for inline list
keywords_list = [k.strip() for k in keywords_text.split(",") if k.strip()]

# Decide topic_title and hierarchy_base (for filename) according to your rules
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
        page_id, topic_title = resolve_page(category_name, "(Category homepage)", "")
        cat_prefix = CATALOG[category_name]["page_id"][:2]  # e.g. "050000_en" -> "05"
        parts = [cat_prefix, slugify(new_subcategory_name or "new-subcategory")]
        if new_subsub_under_newsub.strip():
            parts.append(slugify(new_subsub_under_newsub))
        hierarchy_base = "_".join(parts)

    elif new_subsub_existing_mode:
        # C. Existing category + existing subcategory, new sub-sub
        page_id, topic_title = resolve_page(
            category_name, subcategory_choice, "(Attach to subcategory)"
        )
        sub_prefix = CATALOG[category_name]["sub"][subcategory_choice]["page_id"][
            :4
        ]  # e.g. "050400_en" -> "0504"
        parts = [sub_prefix, slugify(new_subsub_under_existing or "new-sub-subcategory")]
        hierarchy_base = "_".join(parts)

    else:
        # A. All existing (category / subcategory / sub-subcategory)
        page_id, topic_title = resolve_page(
            category_name, subcategory_choice, subsub_choice
        )
        hierarchy_base = page_id  # e.g. "050400_en"

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
    author=author,
    author_institute=author_institute,
    multipage_app=multipage_app if submission_type == "Streamlit app" else False,
    num_pages=int(num_pages) if submission_type == "Streamlit app" else 0,
    interactive_plots=interactive_plots if submission_type == "Streamlit app" else False,
    num_interactive_plots=int(num_interactive_plots)
    if submission_type == "Streamlit app"
    else 0,
    assessments_included=assessments_included
    if submission_type == "Streamlit app"
    else False,
    num_assessment_questions=int(num_assessment_questions)
    if submission_type == "Streamlit app"
    else 0,
    videos_included=videos_included if submission_type == "Streamlit app" else False,
    num_videos=int(num_videos) if submission_type == "Streamlit app" else 0,
)

# Apply language logic to hierarchy_base
prefix_with_lang = apply_language_to_prefix(hierarchy_base, lang_code)

# Final filename
author_slug = slugify(author)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
base_name = f"{prefix_with_lang}_{author_slug}_{timestamp}"
filename = f"{base_name}.yaml"

# --------- 3️⃣ PREVIEW SECTION (if requested) ------------------------
if show_preview:
    st.header("3️⃣ Preview your entry")

    # --- compute display labels for catalog location (proposed) ---
    if new_category_mode:
        display_category = (
            f"{new_category_name} (proposed)" if new_category_name.strip() else "—"
        )
        if new_subcategory_under_newcat.strip():
            display_subcategory = f"{new_subcategory_under_newcat} (proposed)"
        else:
            display_subcategory = "—"
        if new_subsub_under_newcat.strip():
            display_subsub = f"{new_subsub_under_newcat} (proposed)"
        else:
            display_subsub = "—"
    else:
        display_category = category_name
        if new_subcategory_mode and new_subcategory_name.strip():
            display_subcategory = f"{new_subcategory_name} (proposed)"
        else:
            display_subcategory = subcategory_choice

        if new_subsub_existing_mode and new_subsub_under_existing.strip():
            display_subsub = f"{new_subsub_under_existing} (proposed)"
        elif new_subsub_under_newsub.strip():
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
        if description_short.strip():
            st.write(description_short)
        else:
            st.caption("No description provided yet.")

        st.markdown("#### Keywords")
        pretty_keywords = ", ".join(keywords_list) if keywords_list else "—"
        st.markdown(f"{pretty_keywords}")

        st.markdown("#### Author")
        st.markdown(
            f"""
- **Name:** {author or '—'}  
- **Affiliation:** {author_institute or '—'}
"""
        )

        if uploaded_figures:
            st.markdown("#### Figure preview")
            for i, fig in enumerate(uploaded_figures, start=1):
                st.image(
                    fig,
                    caption=f"Uploaded figure {i}: {fig.name}",
                    use_container_width=True,
                )

    st.info(
        "If everything looks correct, click the button below to create the downloadable file. "
        "If you need to change something, edit the form above and click **Generate YAML** again."
    )

    if st.button("✅ Looks good – create download file"):
        st.session_state["ready_for_download"] = True

    if not st.session_state["ready_for_download"]:
        st.stop()

# --------- 4️⃣ YAML & DOWNLOAD ---------------------------------------
st.header("4️⃣ Generated YAML & download")
st.code(yaml_text, language="yaml")

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

st.success("File created. Please download it and send it to the course manager for review.")
