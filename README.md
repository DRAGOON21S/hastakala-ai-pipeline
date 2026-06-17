# Hastakala AI Pipeline

This Python pipeline reads messy artist-submission CSV data, finds already-local
product images, calls Gemini through LangChain for content and visual planning,
optionally calls Gemini or Imagen for generated mockup/story images, and writes
strict JSON to a `.txt` file for the Shopify OS 2.0 frontend.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env`:

```env
GOOGLE_GENAI_USE_VERTEXAI=true
GOOGLE_CLOUD_PROJECT=your-google-cloud-project-id
GOOGLE_CLOUD_LOCATION=global
GOOGLE_APPLICATION_CREDENTIALS=
GOOGLE_APPLICATION_CREDENTIALS_JSON_BASE64=base64_encoded_service_account_json
GEMINI_MODEL=gemini-3.1-pro-preview
IMAGE_PROVIDER=gemini
GEMINI_IMAGE_MODEL=gemini-3-pro-image
IMAGEN_MODEL=imagen-4.0-generate-001
```

This uses Vertex AI / Gemini Enterprise Agent Platform instead of the Google AI
Studio API key path. The current high-quality defaults are:

- `GEMINI_MODEL=gemini-3.1-pro-preview` for text and structured JSON.
- `GEMINI_IMAGE_MODEL=gemini-3-pro-image` for highest-quality Gemini image
  generation.

For a cheaper/faster text model, use `gemini-3.5-flash`. For a cheaper/faster
image model, use `gemini-3.1-flash-image`.

## Vertex AI Credentials

In Google Cloud:

1. Select the project that has your credits.
2. Enable billing and the Vertex AI / Gemini Enterprise Agent Platform API.
3. Create a service account.
4. Grant it `Vertex AI User`.
5. Create and download a JSON key.

For Docker and Droplet usage, encode the JSON key as one line:

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes(".\google-credentials.json"))
```

Paste that value into:

```env
GOOGLE_APPLICATION_CREDENTIALS_JSON_BASE64=...
```

Do not commit the JSON key or `.env`. Both are ignored by git.

If you want local Python to use your `gcloud auth application-default login`
credentials instead, leave both `GOOGLE_APPLICATION_CREDENTIALS` and
`GOOGLE_APPLICATION_CREDENTIALS_JSON_BASE64` empty.

To use the older Google AI Studio key path instead, set:

```env
GOOGLE_GENAI_USE_VERTEXAI=false
GEMINI_API_KEY=your_google_ai_studio_api_key_here
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
python -m hastakala_pipeline.cli --input submissions.csv --output output/products.txt --assets-root assets/products --model gemini-3.1-pro-preview --image-model gemini-3-pro-image
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

## Docker

Build the image:

```powershell
docker build --provenance=false -t hastakala-ai-pipeline:local .
```

Run with the sample CSV mounted by Docker Compose:

```powershell
docker compose run --rm pipeline
```

Run a custom CSV:

```powershell
docker run --rm --env-file .env `
  -v "${PWD}\assets:/app/assets" `
  -v "${PWD}\output:/app/output" `
  -v "${PWD}\submissions.csv:/app/submissions.csv:ro" `
  hastakala-ai-pipeline:local `
  --input /app/submissions.csv `
  --output /app/output/products.txt `
  --assets-root /app/assets/products
```

## DigitalOcean Deployment

This is a batch pipeline, not a long-running web server. You only need a Droplet
if you want a machine that runs the container on a schedule or on demand. For
CI/CD, this repo builds the Docker image and pushes it to DigitalOcean Container
Registry via `.github/workflows/ci-cd.yml`.

The DigitalOcean Container Registry for this project is:

```text
registry.digitalocean.com/hastakala-ai-pipeline
```

Add these GitHub Actions secrets:

- `DIGITALOCEAN_ACCESS_TOKEN`: a DigitalOcean API token with registry access.
- `DROPLET_HOST`: optional, only needed for Droplet deploys.
- `DROPLET_USER`: optional, usually `root` or a deploy user.
- `DROPLET_SSH_PRIVATE_KEY`: optional, the private key GitHub Actions uses to
  SSH into the Droplet.

Set this GitHub Actions variable only when you want the workflow to run the
pipeline on a Droplet after publishing the image:

- `DEPLOY_TO_DROPLET=true`

After a push to `main` or `master`, GitHub Actions publishes:

```text
registry.digitalocean.com/hastakala-ai-pipeline/hastakala-ai-pipeline:latest
registry.digitalocean.com/hastakala-ai-pipeline/hastakala-ai-pipeline:<git-sha>
```

To run it on a Droplet:

```bash
echo "$DIGITALOCEAN_ACCESS_TOKEN" | docker login registry.digitalocean.com -u "$DIGITALOCEAN_ACCESS_TOKEN" --password-stdin
docker pull registry.digitalocean.com/hastakala-ai-pipeline/hastakala-ai-pipeline:latest
docker run --rm --env-file .env \
  -v "$PWD/assets:/app/assets" \
  -v "$PWD/output:/app/output" \
  -v "$PWD/submissions.csv:/app/submissions.csv:ro" \
  registry.digitalocean.com/hastakala-ai-pipeline/hastakala-ai-pipeline:latest \
  --input /app/submissions.csv \
  --output /app/output/products.txt \
  --assets-root /app/assets/products
```

To create a fresh Ubuntu Droplet for this job, use the included cloud-init file
after confirming you want a paid Droplet:

```powershell
doctl compute droplet create hastakala-ai-pipeline `
  --region blr1 `
  --image ubuntu-24-04-x64 `
  --size s-1vcpu-1gb `
  --ssh-keys <ssh-key-id> `
  --user-data-file deploy/droplet-cloud-init.yaml `
  --wait
```

Then upload `/opt/hastakala-ai-pipeline/.env`, `submissions.csv`, and assets to
the Droplet before enabling `DEPLOY_TO_DROPLET=true` in GitHub Actions.
