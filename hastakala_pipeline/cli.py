"""Command-line entry point for the Hastakala pipeline."""

from __future__ import annotations

import argparse

from .pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate Shopify-ready AI content from Hastakala CSV submissions."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to the raw artist-submission CSV.",
    )
    parser.add_argument(
        "--output",
        default="output/products.txt",
        help="Path to the .txt file that will contain strict JSON output.",
    )
    parser.add_argument(
        "--assets-root",
        default="assets/products",
        help="Local root where product image folders already exist.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Optional Gemini model override. Defaults to GEMINI_MODEL or gemini-2.0-flash.",
    )
    parser.add_argument(
        "--image-model",
        default=None,
        help="Optional Imagen model override. Defaults to IMAGEN_MODEL or imagen-4.0-generate-001.",
    )
    parser.add_argument(
        "--skip-image-generation",
        action="store_true",
        help="Only generate image prompts in JSON; do not call Imagen.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only the first N parsed product records. Useful for testing.",
    )
    parser.add_argument(
        "--import-root-images",
        action="store_true",
        help="Copy root-level images beside the CSV into each processed product folder before running.",
    )
    parser.add_argument(
        "--artist-index",
        type=int,
        default=None,
        help="Process products for the Nth artist as they appear in the parsed CSV.",
    )
    parser.add_argument(
        "--product-index",
        type=int,
        default=None,
        help="With --artist-index, process only the Nth product for that artist.",
    )
    parser.add_argument(
        "--offline-fallback",
        action="store_true",
        help="If Gemini text calls fail, generate deterministic local fallback content instead of aborting.",
    )
    parser.add_argument(
        "--force-offline-content",
        action="store_true",
        help="Skip Gemini text calls and use deterministic local content; useful when testing only image generation.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    products = run_pipeline(
        input_csv=args.input,
        output_txt=args.output,
        assets_root=args.assets_root,
        model=args.model,
        image_model=args.image_model,
        generate_images=not args.skip_image_generation,
        limit=args.limit,
        import_root_images=args.import_root_images,
        artist_index=args.artist_index,
        product_index=args.product_index,
        offline_fallback=args.offline_fallback,
        force_offline_content=args.force_offline_content,
    )
    print(f"Wrote {len(products)} product records to {args.output}")


if __name__ == "__main__":
    main()
