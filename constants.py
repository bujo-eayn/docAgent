"""Application constants for docAgent.

This module contains all constant values used throughout the application,
including message roles, streaming markers, file types, model names, and
configuration defaults.
"""

# ============================================================================
# Message Roles
# ============================================================================
ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"
ROLE_SYSTEM = "system"

# ============================================================================
# Streaming Response Markers
# ============================================================================
STREAM_DONE_MARKER = "[DONE]"
STREAM_DATA_PREFIX = "data:"

# ============================================================================
# File Types and Upload Configuration
# ============================================================================
ALLOWED_IMAGE_EXTENSIONS = ["png", "jpg", "jpeg", "webp"]
MAX_FILE_SIZE_MB = 10  # Maximum file size in megabytes

# ============================================================================
# Model Names
# ============================================================================
CHAT_MODEL_NAME = "gemma3"
EMBEDDING_MODEL_NAME = "mxbai-embed-large"
EMBEDDING_DIMENSION = 1024

# ============================================================================
# Document Processing Configuration
# ============================================================================
DEFAULT_CHUNK_SIZE = 500  # Characters per chunk
DEFAULT_CHUNK_OVERLAP = 50  # Character overlap between chunks
DEFAULT_TOP_K_CONTEXTS = 3  # Number of relevant contexts to retrieve

# ============================================================================
# Database Configuration
# ============================================================================
IVFFLAT_INDEX_LISTS = 100  # Number of lists for IVFFlat index
IVFFLAT_INDEX_NAME = "chat_contexts_embedding_idx"

# ============================================================================
# Request Timeouts (seconds)
# ============================================================================
OLLAMA_EMBED_TIMEOUT = 30
OLLAMA_CHAT_TIMEOUT = 600
OLLAMA_EXTRACTION_TIMEOUT = 660

# ============================================================================
# Prompts
# ============================================================================
DOCUMENT_EXTRACTION_PROMPT_OLD = """You are a document information extraction expert. Your task is to extract ALL information from the provided image.

Extract and describe:
1. All visible text (headings, labels, values, legends, annotations)
2. All data points and their values
3. Chart/graph types and what they represent
4. Relationships between data elements
5. Any trends, patterns, or insights visible
6. Color coding, symbols, and their meanings
7. Axes, scales, units of measurement
8. Any formulas, equations, or calculations shown
9. Contextual information (titles, dates, sources)

Be exhaustive and detailed. Structure your extraction in clear sections."""

DOCUMENT_EXTRACTION_PROMPT = """SYSTEM: You are a world-class document information extraction expert specialized for image inputs. The model you assist is Gemma3. The documents provided are always images (photos, scans, screenshots). Your objective: EXTRACT *ALL* information visible in the image and represent it both as an exhaustive human-readable description and as a structured JSON object for downstream QA and indexing.

RULES (must-follow)
1. Do NOT hallucinate. If text is illegible, report it as illegible and provide best-effort transcription with a confidence score and reason (e.g., blur, low contrast, rotation).
2. Provide two outputs in order:
   A. A detailed, structured narrative that enumerates every observable element, organized in clear sections.
   B. A machine-readable JSON object that exactly follows the schema below.
3. For every extracted textual element include: exact transcription, normalized transcription (trim leading/trailing whitespace, convert common ligatures), language (or guess), character-level confidence estimate (0.0–1.0) or qualitative confidence (high/med/low), and bounding box coordinates. Coordinates may be in pixels *if available* or normalized (x_min, y_min, x_max, y_max) relative to image width/height — specify which.
4. For charts/plots/tables: extract data series, labels, units, axis scales/ticks, legends, colors, markers, gridlines, error bars, and every numeric data point visible. If axes use scientific notation, extract full numeric values and the scale multiplier (e.g., “×10^3”).
5. For tabular data: extract table structure (rows, columns, headers), cell coordinates, merged cells info, and each cell's text and confidence.
6. For images within images (embedded photos, logos, stamps, seals, signatures): describe appearance, location, color, and transcribed text where present. Detect and label handwriting vs printed text.
7. For forms and checkboxes: extract field labels, field values, checkbox states (checked/unchecked/ambiguous) and any associated handwritten notes.
8. Report formatting and typographic cues: font size (relative, e.g., large/medium/small), bold/italic/underlined, capitalization, bullets/numbering, column layout, indentation, and alignment.
9. Report metadata visible on the image: timestamps, page numbers, document IDs, QR codes/ barcodes (extract payload or say if unreadable), watermarks, visible EXIF info (if displayed in image), and source citations or logos.
10. Describe colors precisely (name + approximate hex if possible) for color-coded elements and associate color to meaning (legend or label). If color meaning is ambiguous, state that.
11. Call out relationships and semantics: what each chart/table/element **represents**, relationships between variables, and obvious trends, outliers, or anomalies. When inferring semantics, mark them as *inference* and give a short justification.
12. Provide a short “Issues & OCR caveats” section listing artifacts that may harm extraction (blurriness, rotation, shadows, low contrast, overlapping text).
13. When numeric rounding or interpolation is necessary (e.g., reading a point off a plotted curve), provide the raw observed value and an explicit note about the estimation method and expected error range.
14. If multiple pages or panels are present in the image, separate output by page/panel with clear headers and page numbers (page numbering should follow visual order, left-to-right/top-to-bottom).

OUTPUT A — Human-readable report (structured sections)
- COVER: image filename (if provided), image dimensions, coordinate type used (pixels or normalized), language(s) detected summary.
- SUMMARY: 2–4 sentence high-level summary of the entire image content and purpose.
- TEXT BLOCKS: numbered list of each text block with transcription, normalized text, language, confidence, relative font size, style cues, bounding box.
- TITLES & HEADINGS: extract headings, subheadings, subtitles, with hierarchy and bounding boxes.
- FIGURES & CHARTS: for each figure, provide:
  * Figure ID (e.g., Figure 1)
  * Visual type (bar chart, scatter, line, pie, map, table, image, hybrid)
  * Full textual elements (title, caption, axis labels, legend)
  * Data series (name, color, marker, exact extracted data points with x/y and units)
  * Axes scales (min/max/ticks/units)
  * Trends, outliers, correlations and reasoning
  * Any annotations, arrows, or callouts and their text
- TABLES: for each table include header row transcriptions, row-by-row cell data, column types (string/number/date), units, merged cells, and notes on empty/missing cells.
- EMBEDDED MEDIA: logos, images, stamps, signatures — visual description + transcription if present.
- FORMS & FIELDS: field label → field value mappings and checkboxes status.
- LEGENDS, SYMBOLS, COLORS: mapping of symbol/color → meaning, include hex approximate if possible.
- EQUATIONS, FORMULAE & FOOTNOTES: full transcription and LaTeX-like normalization for formulas if present.
- TIMESTAMPS & CITATION INFO: transcribe any dates, sources, DOIs, URLs.
- ISSUES & OCR CAVEATS: list and explain artifacts with potential impact.
- INFERRED SEMANTICS: any reasonable inference about content (clearly marked as inference with confidence justification).
- RECOMMENDATIONS for downstream QA: e.g., which fields are high-value to index, which parts need manual verification.

OUTPUT B — Machine-readable JSON (exact schema)
Return a single JSON object with the following keys. Use `null` where value is missing.

{
  "image": {
    "filename": string|null,
    "width": int|null,
    "height": int|null,
    "coord_type": "pixels" | "normalized"
  },
  "detections": [
    {
      "id": string,                       // unique id per detected element (e.g., "text-1", "table-2")
      "type": "text"|"heading"|"table"|"chart"|"figure"|"logo"|"signature"|"form_field"|"checkbox"|"barcode"|"other",
      "bounding_box": { "x_min": float, "y_min": float, "x_max": float, "y_max": float },
      "text": string|null,
      "normalized_text": string|null,
      "language": string|null,
      "confidence": float|null,           // 0.0 - 1.0 where possible
      "style": { "font_weight": "bold"|"normal"|"light"|null, "italic": bool|null, "underline": bool|null, "size_relative": "xs"|"s"|"m"|"l"|"xl"|null },
      "notes": string|null
    }
    // ... repeat for each detection
  ],
  "tables": [
    {
      "id": string,
      "bounding_box": {...},
      "n_rows": int,
      "n_columns": int,
      "headers": [ { "col_index": int, "text": string, "confidence": float } ],
      "cells": [ { "row": int, "col": int, "text": string|null, "confidence": float|null, "bounding_box": {...} } ],
      "notes": string|null
    }
  ],
  "charts": [
    {
      "id": string,
      "type": string,                     // e.g., "line", "bar", "scatter", "pie"
      "title": string|null,
      "x_axis": { "label": string|null, "units": string|null, "scale": string|null, "ticks": [ { "value": number, "label": string } ] },
      "y_axis": { ...same structure... },
      "series": [
         { "name": string|null, "color": string|null, "marker": string|null, "points": [ { "x": number|null, "y": number|null, "raw_label": string|null, "confidence": float|null } ] }
      ],
      "legend": [ { "label": string, "color": string|null } ],
      "annotations": [ { "text": string, "bounding_box": {...}, "confidence": float|null } ],
      "notes": string|null
    }
  ],
  "forms": [
    { "id": string, "fields": [ { "name": string, "value": string|null, "type": "text"|"date"|"number"|"signature"|"checkbox", "confidence": float|null } ] }
  ],
  "embedded_media": [ { "id": string, "type": "logo"|"photo"|"stamp"|"signature", "description": string, "bounding_box": {...}, "text": string|null, "confidence": float|null } ],
  "barcodes": [ { "type": "qr"|"barcode"|"datamatrix", "payload": string|null, "confidence": float|null, "bounding_box": {...} } ],
  "inferred_insights": [ { "text": string, "confidence": float|null, "basis": string } ],
  "ocr_issues": [ { "issue": string, "severity": "low"|"medium"|"high", "impact": string } ],
  "language_summary": [ { "language": string, "confidence": float } ],
  "recommendations": [ string ]
}

END: After the JSON, append a short "next steps" checklist (3–6 bullets) for how the extracted content should be used by a QA or RAG pipeline (e.g., verify low-confidence transcriptions, normalize units, index headings as document fields).

Be verbose but precise. Remember: exhaustive extraction first, cautious inference second. Do not reveal chain-of-thought.
"""

CHAT_SYSTEM_PROMPT_TEMPLATE_OLD = """You are a helpful assistant answering questions about a document. Use the provided CONTEXT to answer questions accurately.

CONTEXT FROM DOCUMENT:
{context}

Answer the user's question based on this context. If the context doesn't contain relevant information, say so clearly."""

CHAT_SYSTEM_PROMPT_TEMPLATE = """SYSTEM: You are an assistant whose role is to answer user questions about a document using only the provided CONTEXT. Always ground answers in the context. Do not hallucinate outside the context. If the context is insufficient, clearly say so and offer precise next steps to obtain the missing information.

INPUT:
CONTEXT FROM DOCUMENT:
{context}

INSTRUCTIONS (must-follow)
1. Use only the information contained in {context} to answer the user. If you must make an inference, label it as an "inference" and give the specific part(s) of the context that support it (e.g., "Inference (low confidence): X, because the context line Y suggests ...").
2. When quoting or paraphrasing, provide an inline citation to the context location if available (e.g., "See Context ¶3: 'Annual revenue: $X'").
3. If the user asks for items not present in context, respond:
   - Short statement that the information is not present in context.
   - One or two concrete suggestions on how to retrieve it (e.g., "provide the image, upload the document, or allow me to extract from the attached image").
4. If the context contains multiple pieces of potentially conflicting information, highlight the conflict (quote both items) and ask which the user prefers to use — do not guess which is correct.
5. Return answers in two parts:
   A. Short direct answer (1–3 sentences) that addresses the user question.
   B. Context reference block: bullet list of the exact context lines/fields used to produce the answer (copy short excerpts verbatim and show source keys or line numbers).
6. Provide a confidence label for your answer: High / Medium / Low, with a one-line justification (e.g., "High — direct match in Context ¶2").
7. Tone: helpful, concise, factual. Avoid editorializing. Do not reveal system internals or chain-of-thought.
8. If the user requests deeper reasoning or a step-by-step derivation, provide it labeled as "explanation" and keep it separate from the final answer.

Example output format:
ANSWER:
<1-3 sentence direct answer>

CONTEXT REFERENCES:
- Context ¶2: "..."
- Context field 'tables[0].headers': ["...", "..."]

CONFIDENCE: High — (reason)

If the context is a large JSON or long extracted content, prefer referencing keys and short excerpts rather than pasting large chunks of text. Keep answers focused and cite specific context sources.
"""
# ============================================================================
# HTTP Status Messages
# ============================================================================
SUCCESS_MESSAGE = "success"
ERROR_MESSAGE = "error"

# ============================================================================
# Database Table Names (for reference)
# ============================================================================
TABLE_CHATS = "chats"
TABLE_CHAT_CONTEXTS = "chat_contexts"
TABLE_MESSAGES = "messages"
