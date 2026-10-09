from argparse import ArgumentParser
from pathlib import Path

from regional_analysis import HEATMAPS_DIR, analyze_regional_pair, generate_change_heatmap


def parse_args():
    parser = ArgumentParser(description="Analyze one pre/post disaster satellite image pair.")
    parser.add_argument("--pre", required=True, help="Path to pre-disaster image.")
    parser.add_argument("--post", required=True, help="Path to post-disaster image.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pre_image_path = Path(args.pre)
    post_image_path = Path(args.post)

    result = analyze_regional_pair(pre_image_path, post_image_path)

    heatmap_path = HEATMAPS_DIR / f"{pre_image_path.stem.replace('_pre_disaster', '')}_heatmap.png"
    generate_change_heatmap(pre_image_path, post_image_path, heatmap_path)

    print("\nRegional Damage Analysis")
    print(f"Pixel difference: {result['pixel_difference']:.4f}")
    print(f"SSIM change: {result['ssim_change']:.4f}")
    print(f"Deep feature difference: {result['deep_feature_difference']:.4f}")
    print(f"Change area ratio: {result['change_area_ratio']:.4f}")
    print(f"Severe change ratio: {result['severe_change_ratio']:.4f}")
    print(f"Affected region count: {result['affected_region_count']}")
    print(f"Final regional damage score: {result['regional_damage_score']:.4f}")
    print(f"Priority level: {result['priority_level']}")
    print(f"Heatmap saved to: {heatmap_path}")


if __name__ == "__main__":
    main()
