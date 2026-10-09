from pathlib import Path
import re

import cv2
import numpy as np
import pandas as pd
import tensorflow as tf
from scipy.spatial.distance import cosine
from skimage.metrics import structural_similarity as ssim
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input


PROJECT_DIR = Path(__file__).resolve().parent
REGIONAL_IMAGES_DIR = PROJECT_DIR / "regional_dataset" / "images"
OUTPUTS_DIR = PROJECT_DIR / "outputs"
HEATMAPS_DIR = OUTPUTS_DIR / "regional_heatmaps"

IMAGE_SIZE = (224, 224)
VALID_EXTENSIONS = {".jpg", ".jpeg", ".png"}
CHANGE_AREA_THRESHOLD = 0.18
SEVERE_CHANGE_THRESHOLD = 0.38
MIN_AFFECTED_REGION_AREA = 80

_FEATURE_EXTRACTOR: tf.keras.Model | None = None


def get_feature_extractor() -> tf.keras.Model:
    """Load a pretrained CNN once and reuse it for deep feature extraction."""
    global _FEATURE_EXTRACTOR

    if _FEATURE_EXTRACTOR is None:
        _FEATURE_EXTRACTOR = MobileNetV2(
            include_top=False,
            weights="imagenet",
            pooling="avg",
            input_shape=(IMAGE_SIZE[0], IMAGE_SIZE[1], 3),
        )

    return _FEATURE_EXTRACTOR


def pair_id_from_filename(file_path: Path) -> tuple[str, str] | None:
    """Extract pair id and image type from names ending with pre/post_disaster."""
    match = re.match(r"(.+)_(pre|post)_disaster$", file_path.stem)
    if not match:
        return None
    pair_id, image_type = match.groups()
    return pair_id, image_type


def find_pre_post_pairs(images_dir: Path) -> list[tuple[Path, Path]]:
    """Find pre/post image pairs from one folder using the shared file id."""
    if not images_dir.exists():
        raise FileNotFoundError(f"Regional images folder not found: {images_dir}")

    pairs_by_id: dict[str, dict[str, Path]] = {}

    for image_path in sorted(images_dir.iterdir()):
        if not image_path.is_file() or image_path.suffix.lower() not in VALID_EXTENSIONS:
            continue

        parsed = pair_id_from_filename(image_path)
        if parsed is None:
            continue

        pair_id, image_type = parsed
        pairs_by_id.setdefault(pair_id, {})[image_type] = image_path

    pairs = []
    skipped_count = 0

    for pair_id, files in sorted(pairs_by_id.items()):
        pre_image = files.get("pre")
        post_image = files.get("post")

        if pre_image and post_image:
            pairs.append((pre_image, post_image))
        else:
            skipped_count += 1

    print(f"Found {len(pairs)} valid pre/post pair(s).")
    if skipped_count:
        print(f"Skipped {skipped_count} incomplete pair(s).")

    return pairs


def preprocess_image(image_path: Path, image_size: tuple[int, int] = IMAGE_SIZE) -> np.ndarray:
    """Read an image, convert it to RGB, resize it and normalize to 0-1."""
    image = cv2.imread(str(image_path))
    if image is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")

    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image = cv2.resize(image, image_size)
    return image.astype(np.float32) / 255.0


def calculate_pixel_difference(pre_img: np.ndarray, post_img: np.ndarray) -> float:
    """Calculate the average absolute pixel difference as a 0-1 score."""
    difference = np.abs(pre_img - post_img)
    return float(np.clip(np.mean(difference), 0.0, 1.0))


def calculate_difference_map(pre_img: np.ndarray, post_img: np.ndarray) -> np.ndarray:
    """Create a single-channel 0-1 difference map from RGB pre/post images."""
    return np.mean(np.abs(pre_img - post_img), axis=2)


def calculate_change_area_ratio(difference_map: np.ndarray) -> float:
    """Calculate how much of the image changed above a moderate threshold."""
    changed_pixels = difference_map > CHANGE_AREA_THRESHOLD
    return float(np.mean(changed_pixels))


def calculate_severe_change_ratio(difference_map: np.ndarray) -> float:
    """Calculate how much of the image changed above a severe threshold."""
    severe_pixels = difference_map > SEVERE_CHANGE_THRESHOLD
    return float(np.mean(severe_pixels))


def calculate_affected_region_count(difference_map: np.ndarray) -> int:
    """Count large connected changed regions without claiming building counts."""
    severe_mask = (difference_map > CHANGE_AREA_THRESHOLD).astype(np.uint8)
    kernel = np.ones((5, 5), np.uint8)
    cleaned_mask = cv2.morphologyEx(severe_mask, cv2.MORPH_OPEN, kernel)
    cleaned_mask = cv2.morphologyEx(cleaned_mask, cv2.MORPH_CLOSE, kernel)

    component_count, labels, stats, _ = cv2.connectedComponentsWithStats(cleaned_mask, connectivity=8)
    affected_regions = 0

    for component_index in range(1, component_count):
        area = stats[component_index, cv2.CC_STAT_AREA]
        if area >= MIN_AFFECTED_REGION_AREA:
            affected_regions += 1

    return affected_regions


def calculate_ssim_score(pre_img: np.ndarray, post_img: np.ndarray) -> float:
    """Calculate SSIM-based change score. Higher means more visual change."""
    pre_gray = cv2.cvtColor((pre_img * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
    post_gray = cv2.cvtColor((post_img * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)

    similarity = ssim(pre_gray, post_gray, data_range=255)
    change_score = 1.0 - similarity
    return float(np.clip(change_score, 0.0, 1.0))


def calculate_deep_feature_difference(pre_img: np.ndarray, post_img: np.ndarray) -> float:
    """Compare pretrained CNN feature vectors using normalized cosine distance."""
    model = get_feature_extractor()

    pre_batch = np.expand_dims(pre_img * 255.0, axis=0)
    post_batch = np.expand_dims(post_img * 255.0, axis=0)

    pre_features = model.predict(preprocess_input(pre_batch), verbose=0)[0]
    post_features = model.predict(preprocess_input(post_batch), verbose=0)[0]

    # Cosine distance is usually 0-2. Dividing by 2 maps it into an approximate 0-1 range.
    distance = cosine(pre_features, post_features)
    if np.isnan(distance):
        distance = 0.0

    return float(np.clip(distance / 2.0, 0.0, 1.0))


def calculate_regional_damage_score(pre_image_path: Path, post_image_path: Path) -> dict:
    """Combine visual, structural and deep feature differences into one score."""
    pre_img = preprocess_image(pre_image_path)
    post_img = preprocess_image(post_image_path)

    difference_map = calculate_difference_map(pre_img, post_img)
    pixel_difference = calculate_pixel_difference(pre_img, post_img)
    ssim_change = calculate_ssim_score(pre_img, post_img)
    deep_feature_difference = calculate_deep_feature_difference(pre_img, post_img)
    change_area_ratio = calculate_change_area_ratio(difference_map)
    severe_change_ratio = calculate_severe_change_ratio(difference_map)
    affected_region_count = calculate_affected_region_count(difference_map)

    final_score = (
        0.25 * pixel_difference
        + 0.25 * ssim_change
        + 0.20 * deep_feature_difference
        + 0.20 * change_area_ratio
        + 0.10 * severe_change_ratio
    )

    return {
        "pixel_difference": round(pixel_difference, 4),
        "ssim_change": round(ssim_change, 4),
        "deep_feature_difference": round(deep_feature_difference, 4),
        "change_area_ratio": round(change_area_ratio, 4),
        "severe_change_ratio": round(severe_change_ratio, 4),
        "affected_region_count": affected_region_count,
        "regional_damage_score": round(float(np.clip(final_score, 0.0, 1.0)), 4),
    }


def get_priority_level(score: float, severe_change_ratio: float = 0.0) -> str:
    """Convert regional score into a five-level priority scale."""
    if severe_change_ratio > 0.40:
        return "very_high"

    if score < 0.15:
        priority = "very_low"
    elif score < 0.35:
        priority = "low"
    elif score < 0.55:
        priority = "medium"
    elif score < 0.75:
        priority = "high"
    else:
        priority = "very_high"

    if severe_change_ratio > 0.25 and priority in {"very_low", "low", "medium"}:
        return "high"

    return priority


def priority_sort_key(priority_level: str) -> int:
    """Return an order value for regional priority labels."""
    order = {
        "very_low": 0,
        "low": 1,
        "medium": 2,
        "high": 3,
        "very_high": 4,
    }
    return order[priority_level]


def ensure_minimum_priority(priority_level: str, minimum_priority: str) -> str:
    """Raise priority to a minimum level when override rules require it."""
    if priority_sort_key(priority_level) < priority_sort_key(minimum_priority):
        return minimum_priority
    return priority_level


def legacy_priority_level(score: float) -> str:
    """Deprecated helper kept only for old imports if any local script used it."""
    if score < 0.15:
        return "very_low"
    if score < 0.35:
        return "low"
    if score < 0.55:
        return "medium"
    if score < 0.75:
        return "high"
    return "very_high"


def generate_change_heatmap(pre_image_path: Path, post_image_path: Path, output_path: Path) -> Path:
    """Generate and save a heatmap from absolute image difference."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    pre_img = preprocess_image(pre_image_path)
    post_img = preprocess_image(post_image_path)

    difference = calculate_difference_map(pre_img, post_img)
    difference_uint8 = (difference * 255).astype(np.uint8)

    heatmap_bgr = cv2.applyColorMap(difference_uint8, cv2.COLORMAP_JET)
    post_bgr = cv2.cvtColor((post_img * 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
    overlay = cv2.addWeighted(post_bgr, 0.60, heatmap_bgr, 0.40, 0)

    cv2.imwrite(str(output_path), overlay)
    return output_path


def analyze_regional_pair(
    pre_image_path: Path,
    post_image_path: Path,
    create_heatmap: bool = False,
) -> dict:
    """Analyze one pre/post pair and optionally save a change heatmap."""
    scores = calculate_regional_damage_score(pre_image_path, post_image_path)
    priority_level = get_priority_level(
        scores["regional_damage_score"],
        scores["severe_change_ratio"],
    )

    result = {
        **scores,
        "priority_level": priority_level,
    }

    if create_heatmap:
        heatmap_name = f"{pre_image_path.stem.replace('_pre_disaster', '')}_heatmap.png"
        heatmap_path = generate_change_heatmap(
            pre_image_path,
            post_image_path,
            HEATMAPS_DIR / heatmap_name,
        )
        result["heatmap_path"] = str(heatmap_path)

    return result


def analyze_all_regional_pairs(images_dir: Path, create_heatmaps: bool = False) -> Path:
    """Analyze every pair in regional_dataset/images and save a CSV report."""
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    pairs = find_pre_post_pairs(images_dir)

    if not pairs:
        raise ValueError(f"No valid pre/post pairs found in: {images_dir}")

    rows = []

    for pre_image_path, post_image_path in pairs:
        result = analyze_regional_pair(
            pre_image_path,
            post_image_path,
            create_heatmap=create_heatmaps,
        )
        rows.append(
            {
                "pair_id": pre_image_path.stem.replace("_pre_disaster", ""),
                "pre_image": str(pre_image_path),
                "post_image": str(post_image_path),
                **result,
            }
        )

    dataframe = pd.DataFrame(rows)
    output_path = OUTPUTS_DIR / "regional_analysis_results.csv"
    dataframe.to_csv(output_path, index=False)

    print(f"\nResults saved to: {output_path}")
    print("Priority counts:")
    print(dataframe["priority_level"].value_counts().to_string())

    return output_path


if __name__ == "__main__":
    analyze_all_regional_pairs(REGIONAL_IMAGES_DIR, create_heatmaps=False)
