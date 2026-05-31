# Hastakala AI Pipeline

This Python pipeline reads messy artist-submission CSV data, finds already-local
product images, calls Gemini through LangChain for content and visual planning,
optionally calls Imagen for generated mockup/story images, and writes strict JSON
to a `.txt` file for the Shopify OS 2.0 frontend.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env`:

```env
GEMINI_API_KEY=your_google_ai_studio_api_key_here
GEMINI_MODEL=gemini-2.5-flash-lite
IMAGE_PROVIDER=gemini
GEMINI_IMAGE_MODEL=gemini-2.5-flash-image
IMAGEN_MODEL=imagen-4.0-generate-001
```

## Expected CSV Headers

The parser accepts these headers:

- `Artist Name`
- `Hastakala Artist ID`
- `Price (₹)`
- `Product Name`
- `Category`
- `Art Style / Craft Type`
- `Short Description`
- `Material`
- `Height`
- `Width`
- `Weight`
- `Availability`

Google Drive image URL columns can remain in the CSV, but they are ignored for
now because images are expected to already exist locally.

## Local Image Layout

Place images here:

```text
assets/products/<product_id>/img_1.jpg
assets/products/<product_id>/img_2.jpg
```

For quick testing with a loose image in the same folder as the CSV, use
`--import-root-images --limit 1`. That copies root-level images into the first
processed product folder before the pipeline runs.

If the CSV does not contain a `Product ID` column, product IDs are generated as:

```text
<Hastakala Artist ID>-01
<Hastakala Artist ID>-02
```

For example:

```text
assets/products/HK-AR-0007-01/img_1.jpg
```

## Run

```powershell
python -m hastakala_pipeline.cli --input submissions.csv --output output/products.txt
```

Optional:

```powershell
python -m hastakala_pipeline.cli --input submissions.csv --output output/products.txt --assets-root assets/products --model gemini-2.5-flash-lite --image-model gemini-2.5-flash-image
```

Test only the first parsed product and import loose root images:

```powershell
python -m hastakala_pipeline.cli --input "Artists Products Details (Responses) - Form responses 1.csv" --output output/test-products.txt --limit 1 --import-root-images
```

Generate only text and visual prompts, without calling Imagen:

```powershell
python -m hastakala_pipeline.cli --input submissions.csv --output output/products.txt --skip-image-generation
```

The output file is a JSON array saved as `.txt`, with one object per CSV row.
