import io
import os
import re
import csv
import time
import zipfile
import hashlib
from pathlib import Path
from typing import List, Tuple, Dict

import streamlit as st
from openai import OpenAI


APP_TITLE = "Efficient Markdown Translator"


LANGUAGES = {
    "German": {"label": "German", "suffix": "de", "native": "Deutsch"},
    "English": {"label": "English", "suffix": "en", "native": "English"},
    "French": {"label": "French", "suffix": "fr", "native": "français"},
    "Spanish": {"label": "Spanish", "suffix": "es", "native": "español"},
    "Italian": {"label": "Italian", "suffix": "it", "native": "italiano"},
    "Portuguese": {"label": "Portuguese", "suffix": "pt", "native": "português"},
    "Chinese": {"label": "Chinese", "suffix": "zh", "native": "中文"},
    "Dutch": {"label": "Dutch", "suffix": "nl", "native": "Nederlands"},
    "Polish": {"label": "Polish", "suffix": "pl", "native": "polski"},
    "Czech": {"label": "Czech", "suffix": "cs", "native": "čeština"},
}


# ============================================================
# API key handling
# ============================================================
def get_openai_api_key(api_key_input: str) -> str:
    """
    Safely get the OpenAI API key.

    Priority:
    1. Sidebar input
    2. Environment variable OPENAI_API_KEY
    3. Streamlit secrets, only if available

    Never hard-code API keys in this file.
    """
    if api_key_input:
        return api_key_input.strip()

    env_key = os.getenv("OPENAI_API_KEY", "").strip()
    if env_key:
        return env_key

    try:
        return st.secrets.get("OPENAI_API_KEY", "").strip()
    except Exception:
        return ""


def get_client(api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key)


# ============================================================
# File handling
# ============================================================
def read_glossary(uploaded_csv) -> List[Tuple[str, str]]:
    """
    Reads an optional two-column CSV glossary.
    First column: source term
    Second column: target-language term

    If the glossary is missing, malformed, or empty, return [].
    """
    if uploaded_csv is None:
        return []

    try:
        raw = uploaded_csv.getvalue().decode("utf-8-sig", errors="replace")
        rows = list(csv.reader(io.StringIO(raw)))
    except Exception:
        return []

    glossary = []

    header_like = {
        "english", "en", "source", "source term", "term", "original",
        "target", "translation", "translated term",
        "german", "de", "french", "fr", "spanish", "es",
        "italian", "it", "portuguese", "pt", "chinese", "zh"
    }

    for row in rows:
        if len(row) < 2:
            continue

        src = row[0].strip()
        tgt = row[1].strip()

        if not src or not tgt:
            continue

        if src.lower() in header_like:
            continue

        glossary.append((src, tgt))

    glossary.sort(key=lambda x: len(x[0]), reverse=True)
    return glossary


def extract_md_files(uploaded_zip) -> Dict[str, str]:
    files = {}
    with zipfile.ZipFile(io.BytesIO(uploaded_zip.getvalue()), "r") as z:
        for name in sorted(z.namelist()):
            if name.endswith("/"):
                continue
            if name.lower().endswith(".md"):
                files[name] = z.read(name).decode("utf-8", errors="replace")
    return files


def make_output_zip(translated_files: Dict[str, str], suffix: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, content in translated_files.items():
            p = Path(name)
            
            if suffix:
                new_name = f"{p.stem}_{suffix}{p.suffix}"
            else:
                new_name = f"{p.stem}{p.suffix}"
            
            out_name = str(p.with_name(new_name))
            z.writestr(out_name, content.encode("utf-8"))
    return buffer.getvalue()


# ============================================================
# Markdown splitting
# ============================================================
def split_markdown_safely(md: str, max_chars: int = 12000) -> List[str]:
    """
    Split Markdown into chunks.
    Keeps fenced code blocks intact.
    Prefers splits at headings and blank lines.
    """
    lines = md.splitlines(keepends=True)

    chunks = []
    current = []
    current_len = 0
    in_fence = False

    def flush():
        nonlocal current, current_len
        if current:
            chunks.append("".join(current))
            current = []
            current_len = 0

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence

        is_heading = bool(re.match(r"^\s{0,3}#{1,6}\s+", line))

        if (not in_fence) and is_heading and current_len > max_chars * 0.55:
            flush()

        if (not in_fence) and current_len > max_chars and stripped == "":
            current.append(line)
            flush()
            continue

        current.append(line)
        current_len += len(line)

    flush()
    return chunks


# ============================================================
# Token-saving glossary handling
# ============================================================
def normalize_for_search(text: str) -> str:
    return text.lower()


def term_occurs(term: str, text_lower: str) -> bool:
    """
    Efficient and safe-ish occurrence check.

    For multi-word terms, substring matching is usually best.
    For single-word terms, use word boundaries to avoid many false positives.
    """
    term_clean = term.strip().lower()
    if not term_clean:
        return False

    if " " in term_clean or "-" in term_clean:
        return term_clean in text_lower

    pattern = r"\b" + re.escape(term_clean) + r"\b"
    return re.search(pattern, text_lower) is not None


def filter_relevant_glossary(
    glossary: List[Tuple[str, str]],
    chunk: str,
    max_terms: int = 80,
) -> List[Tuple[str, str]]:
    """
    Only send glossary entries whose source term occurs in the current chunk.
    This avoids sending hundreds of irrelevant terms to the API.
    """
    if not glossary:
        return []

    text_lower = normalize_for_search(chunk)
    relevant = [(src, tgt) for src, tgt in glossary if term_occurs(src, text_lower)]

    # longer entries first; cap to avoid oversized prompts
    relevant.sort(key=lambda x: len(x[0]), reverse=True)
    return relevant[:max_terms]


def glossary_as_markdown(glossary: List[Tuple[str, str]], target_language: str) -> str:
    if not glossary:
        return ""

    lines = [
        f"Use the following glossary entries only if the target terms fit {target_language}.",
        "If an entry appears to be in the wrong target language, ignore only that entry.",
        "",
        "| Source term | Preferred target-language term |",
        "|---|---|",
    ]

    for src, tgt in glossary:
        src = src.replace("|", "\\|")
        tgt = tgt.replace("|", "\\|")
        lines.append(f"| {src} | {tgt} |")

    return "\n".join(lines)


# ============================================================
# Translation memory
# ============================================================
def cache_key(model: str, target_language: str, chunk: str, relevant_glossary: List[Tuple[str, str]]) -> str:
    h = hashlib.sha256()
    h.update(model.encode("utf-8"))
    h.update(target_language.encode("utf-8"))
    h.update(chunk.encode("utf-8"))
    for src, tgt in relevant_glossary:
        h.update(src.encode("utf-8"))
        h.update(tgt.encode("utf-8"))
    return h.hexdigest()


def get_translation_memory() -> Dict[str, str]:
    if "translation_memory" not in st.session_state:
        st.session_state.translation_memory = {}
    return st.session_state.translation_memory


# ============================================================
# Translation
# ============================================================
def translate_chunk(
    client: OpenAI,
    model: str,
    chunk: str,
    target_language: str,
    relevant_glossary: List[Tuple[str, str]],
    filename: str,
    chunk_index: int,
    total_chunks: int,
    max_retries: int = 3,
) -> str:
    """
    Translate one Markdown chunk.

    Efficiency:
    - Only relevant glossary entries are sent.
    - Identical chunks are cached in session memory.
    - No temperature parameter is sent, because current GPT-5 models may reject it.
    """
    memory = get_translation_memory()
    key = cache_key(model, target_language, chunk, relevant_glossary)

    if key in memory:
        return memory[key]

    glossary_md = glossary_as_markdown(relevant_glossary, target_language)

    if glossary_md:
        glossary_instruction = f"""
Relevant glossary entries for this chunk:
{glossary_md}
""".strip()
    else:
        glossary_instruction = "No relevant usable glossary entries were found for this chunk."

    instructions = f"""
You are a professional translator for hydrogeology and educational Markdown modules.

Translate the supplied Markdown content into {target_language}.

Critical rules:
- Return ONLY the translated Markdown chunk.
- Do not add explanations, comments, or code fences.
- Preserve Markdown structure exactly.
- Preserve headings, lists, tables, links, image references, HTML, YAML/front matter, LaTeX, inline math, and code blocks.
- Do not translate variable names, file names, URLs, Markdown anchors, code, or equations.
- Translate only human-readable natural language.
- Preserve emoji and Markdown symbols.
- Preserve paragraph breaks.
- Use clear academic language suitable for graduate students and professionals.

File: {filename}
Chunk: {chunk_index} of {total_chunks}

{glossary_instruction}
""".strip()

    user_input = chunk

    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            response = client.responses.create(
                model=model,
                instructions=instructions,
                input=user_input,
            )
            translated = response.output_text
            memory[key] = translated
            return translated

        except Exception as e:
            last_error = e
            time.sleep(2 ** attempt)

    raise RuntimeError(f"Translation failed after {max_retries} attempts: {last_error}")


# ============================================================
# Streamlit UI
# ============================================================
st.set_page_config(page_title=APP_TITLE, layout="wide")
st.title(APP_TITLE)

st.markdown(
    """
Upload a ZIP file containing Markdown files. Optionally upload a CSV terminology glossary.
The app translates the Markdown files into the selected language and returns a ZIP with translated `.md` files.
"""
)

with st.sidebar:
    st.header("Settings")

    api_key_input = st.text_input(
        "OpenAI API key",
        value="",
        type="password",
        help="Recommended: paste your key here or set OPENAI_API_KEY as an environment variable.",
    )

    target_language_name = st.selectbox(
        "Target language",
        options=list(LANGUAGES.keys()),
        index=0,
    )
    target_language = LANGUAGES[target_language_name]["label"]
    suffix_default = LANGUAGES[target_language_name]["suffix"]

    output_suffix = st.text_input(
        "Output filename suffix",
        value=suffix_default,
        help="Leave empty to keep the original filename.",
    ).strip()

    model = st.selectbox(
        "Model",
        options=[
            "gpt-5.5",
            "gpt-5",
            "gpt-4.1",
        ],
        index=0,
        help="For highest translation quality use gpt-5.5. For lower cost, test gpt-5.",
    )

    max_chars = st.slider(
        "Max characters per chunk",
        min_value=4000,
        max_value=20000,
        value=12000,
        step=1000,
        help="Smaller chunks are safer; larger chunks are faster and often cheaper.",
    )

    max_glossary_terms = st.slider(
        "Maximum glossary terms per chunk",
        min_value=10,
        max_value=200,
        value=80,
        step=10,
        help="Only glossary terms occurring in the current chunk are sent.",
    )

    max_files = st.number_input(
        "Maximum files to translate",
        min_value=1,
        max_value=500,
        value=50,
        help="Useful for testing with only a few files first.",
    )

zip_upload = st.file_uploader("ZIP containing Markdown files", type=["zip"])
glossary_upload = st.file_uploader("Optional terminology glossary CSV", type=["csv"])

api_key = get_openai_api_key(api_key_input)

if zip_upload:
    md_files = extract_md_files(zip_upload)
    glossary = read_glossary(glossary_upload)

    if glossary_upload is None:
        st.info("No glossary uploaded. The app will translate without glossary constraints.")
    elif glossary:
        st.success(f"Loaded {len(glossary)} glossary entries. Only entries found in each chunk will be sent to the API.")
    else:
        st.warning("The uploaded glossary could not be read as a usable two-column CSV. It will be ignored.")

    st.success(f"Found {len(md_files)} Markdown files.")

    with st.expander("Preview files"):
        for name in list(md_files.keys())[:100]:
            st.write(name)

    if glossary:
        with st.expander("Preview glossary"):
            st.dataframe(
                [{"source": src, "target": tgt} for src, tgt in glossary[:200]],
                use_container_width=True,
            )

    if not api_key:
        st.warning("Please provide an OpenAI API key in the sidebar, environment variable, or Streamlit secrets.")

    col1, col2 = st.columns(2)
    with col1:
        start = st.button("Translate Markdown files", disabled=not bool(api_key))
    with col2:
        if st.button("Clear translation memory"):
            st.session_state.translation_memory = {}
            st.success("Translation memory cleared.")

    if start:
        client = get_client(api_key)
        translated_files = {}
        selected_items = list(md_files.items())[: int(max_files)]

        progress = st.progress(0)
        status = st.empty()
        log_box = st.empty()

        logs = []
        total_steps = 0
        file_chunks = {}

        for name, text in selected_items:
            chunks = split_markdown_safely(text, max_chars=max_chars)
            file_chunks[name] = chunks
            total_steps += len(chunks)

        done_steps = 0

        total_relevant_terms_sent = 0

        for file_index, (name, original_text) in enumerate(selected_items, start=1):
            chunks = file_chunks[name]
            translated_chunks = []

            logs.append(f"Translating {name} ({file_index}/{len(selected_items)}), {len(chunks)} chunk(s)")
            log_box.text("\n".join(logs[-20:]))

            for i, chunk in enumerate(chunks, start=1):
                relevant_glossary = filter_relevant_glossary(
                    glossary,
                    chunk,
                    max_terms=int(max_glossary_terms),
                )
                total_relevant_terms_sent += len(relevant_glossary)

                status.info(
                    f"Translating {name} into {target_language} — "
                    f"chunk {i}/{len(chunks)} — "
                    f"{len(relevant_glossary)} glossary term(s)"
                )

                translated = translate_chunk(
                    client=client,
                    model=model,
                    chunk=chunk,
                    target_language=target_language,
                    relevant_glossary=relevant_glossary,
                    filename=name,
                    chunk_index=i,
                    total_chunks=len(chunks),
                )

                translated_chunks.append(translated)
                done_steps += 1
                progress.progress(done_steps / total_steps)

            translated_files[name] = "".join(translated_chunks)

        zip_bytes = make_output_zip(translated_files, output_suffix)

        st.success(
            f"Translation finished. Sent {total_relevant_terms_sent} relevant glossary entries in total "
            f"instead of sending the full glossary with every chunk."
        )

        st.download_button(
            label="Download translated Markdown ZIP",
            data=zip_bytes,
            file_name=f"translated_markdown_{output_suffix}.zip",
            mime="application/zip",
        )

        with st.expander("Translated file list"):
            for name in translated_files:
                p = Path(name)
                st.write(str(p.with_name(p.stem + f"_{output_suffix}" + p.suffix)))

else:
    st.info("Please upload a ZIP file containing Markdown files to begin.")
