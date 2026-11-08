# Smart Image Preprocessing & Adaptive Compression Service for Gemini 3.5 Flash OCR

---

## 1. Executive Summary & Objective

When users upload documents, screenshots, or photos for text extraction and translation via **Gemini 3.5 Flash**, raw image files are often multi-megabyte payloads that inflate database storage costs and increase token-processing overhead. However, aggressive or blind compression destroys character stroke edges (especially in lowercase handwriting or low-contrast numbers), leading to OCR failure and translation hallucinations.

**Objective:** Build a Python 3.12 backend preprocessing pipeline that programmatically evaluates, compresses, and stores images in an optimized format (WebP) for database retention while maintaining Gemini OCR fidelity. To minimize AI evaluation costs and simplify processing logic, the system introduces a **User-Facing Handwriting Toggle** during upload, combining user intent with a computational sharpness metric to dynamically select the correct compression tier.

---

## 2. User Stories & Personas

* **As an End User**, I want to upload text-heavy images or handwritten notes quickly, and have the option to check a box if my document is handwritten, so the system preserves my tricky handwriting without me worrying about blurriness or translation errors.
* **As a Product Owner / FinOps Engineer**, I want to minimize cloud storage bloat and reduce database storage costs by downscaling and compressing images down to 50KB–150KB when high fidelity isn't needed.
* **As a Backend Engineer**, I want a deterministic, programmatic evaluation algorithm (combining user flags and Laplacian sharpness) in Python 3.12 so we avoid expensive LLM pre-classification calls.

---

## 3. Functional Requirements

### 3.1. Frontend Upload Interface

* **Handwritten Toggle:** The upload UI must include a clear, accessible checkbox or toggle field: *"Is this image handwritten or contains complex notes?"* (Default: `false`).
* **Payload Handshake:** The frontend transmits the raw image bytes alongside a boolean flag `is_handwritten` to the backend ingestion endpoint.

### 3.2. Backend Processing & Tier Routing Engine

The ingestion service must execute the following sequential pipeline:

1. **Normalization:** Convert incoming formats (PNG, RGBA, Palette-indexed images) to a standard RGB color space.
2. **Sharpness Evaluation:** Calculate the image's Variance of the Laplacian to detect blur or out-of-focus capture.
3. **Adaptive Tier Selection:** Map the user flag and sharpness score to one of three compression profiles:
* **Tier 1 (Aggressive):** For crisp digital text/screenshots (`is_handwritten=false` & High Sharpness). Max bounds: `1600px`, WebP Quality: `70`.
* **Tier 2 (Balanced):** For standard photos/normal notes (`is_handwritten=false` & Medium Sharpness). Max bounds: `2000px`, WebP Quality: `80`.
* **Tier 3 (High Preservation):** For poor handwriting, cursive, or blurry captures (`is_handwritten=true` OR Low Sharpness). Max bounds: `2400px`, WebP Quality: `90`.


4. **Database Storage:** Store the compressed WebP binary blob (`BLOB`/`BYTEA`) and associated metadata (`tier_selected`, `sharpness_score`, `original_dimensions`, `final_dimensions`).

### 3.3. Restoration Service (User View Mode)

* When a user requests to view the original upload (a rare occurrence):
* Fetch the compressed WebP blob from the database.
* Decode it and optionally apply a gentle upscale filter (e.g., Lanczos resampling) if displayed on high-DPI screens.
* Render as a standard high-compatibility JPEG (`quality=90`).



---

## 4. Technical Specifications (Python 3.12)

The implementation utilizes **Pillow (PIL)** and **NumPy** for rapid, lightweight matrix processing.

```python
import io
import numpy as np
from PIL import Image

def calculate_image_sharpness(img: Image.Image) -> float:
    """
    Calculates image sharpness using the Variance of the Laplacian.
    Lower values indicate blurrier images (bad for handwriting recognition).
    """
    gray = np.array(img.convert("L"))
    laplacian_var = np.var(
        np.abs(gray[1:, :] - gray[:-1, :]) + 
        np.abs(gray[:, 1:] - gray[:, :-1])
    )
    return float(laplacian_var)

def evaluate_and_compress_image(
    image_bytes: bytes, 
    is_handwritten: bool = False
) -> tuple[bytes, dict]:
    """
    Evaluates image characteristics, determines the required quality tier,
    and compresses it dynamically for Gemini 3.5 Flash storage.
    """
    img = Image.open(io.BytesIO(image_bytes))
    
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    original_width, original_height = img.size
    sharpness_score = calculate_image_sharpness(img)
    
    # Tier routing logic balancing user input and computational checks
    if is_handwritten or sharpness_score < 100.0:
        max_dimension = 2400
        quality = 90
        tier = "Tier 3 (High Preservation - Handwriting/Blur)"
    elif sharpness_score < 500.0:
        max_dimension = 2000
        quality = 80
        tier = "Tier 2 (Balanced - Standard Photo/Notes)"
    else:
        max_dimension = 1600
        quality = 70
        tier = "Tier 1 (Aggressive - Crisp Digital Text)"

    if max(img.size) > max_dimension:
        img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

    output_io = io.BytesIO()
    img.save(output_io, format="WEBP", quality=quality, method=6)
    compressed_bytes = output_io.getvalue()

    metadata = {
        "tier_selected": tier,
        "sharpness_score": round(sharpness_score, 2),
        "original_dimensions": (original_width, original_height),
        "final_dimensions": img.size,
        "compressed_size_kb": round(len(compressed_bytes) / 1024, 2)
    }

    return compressed_bytes, metadata

```

---

## 5. Non-Functional Requirements & Guardrails

* **Performance & Latency:** The preprocessing pipeline (sharpness calculation + resizing + WebP encoding) must execute in **under 150ms** per image on standard backend worker nodes.
* **Storage Optimization:** Expect an average reduction of **75% to 90%** in file footprint compared to raw smartphone captures, dropping storage per image from ~3MB to ~150KB.
* **Gemini Compatibility:** The WebP payload must retain clean stroke geometry so that Gemini 3.5 Flash's internal patch encoder encounters zero degradation in character tokenization.

---

## 6. Success Metrics & KPIs

| Metric | Target | Description |
| --- | --- | --- |
| **Storage Reduction** | $\ge 80\%$ | Average reduction in database capacity used for image binary records. |
| **OCR Accuracy Maintenance** | $\ge 99.5\%$ | Gemini translation and text recognition accuracy parity compared to uncompressed raw images. |
| **Preprocessing Latency** | $< 150\text{ms}$ | Time elapsed from upload receipt to completed compressed byte stream generation. |
| **Cost Efficiency** | $0\text{ LLM Token Overhead}$ | Pre-evaluation performed entirely via programmatic compute rather than external vision-LLM calls. |
