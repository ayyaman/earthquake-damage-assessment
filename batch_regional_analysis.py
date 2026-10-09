from argparse import ArgumentParser

from regional_analysis import REGIONAL_IMAGES_DIR, analyze_all_regional_pairs


def parse_args():
    parser = ArgumentParser(description="Analyze all regional pre/post image pairs.")
    parser.add_argument(
        "--heatmaps",
        action="store_true",
        help="Also generate heatmaps for every pair. Default only creates CSV.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    analyze_all_regional_pairs(REGIONAL_IMAGES_DIR, create_heatmaps=args.heatmaps)


if __name__ == "__main__":
    main()
