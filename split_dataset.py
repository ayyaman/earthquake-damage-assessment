from pathlib import Path
import shutil
from sklearn.model_selection import train_test_split


# Project paths
PROJECT_DIR = Path(__file__).resolve().parent
SOURCE_DIR = PROJECT_DIR / "final_dataset"
OUTPUT_DIR = PROJECT_DIR / "dataset_split"

# Class folder names. These names are also used by the training script.
CLASSES = ["no_damage", "damaged", "collapsed"]
VALID_EXTENSIONS = {".jpg", ".jpeg", ".png"}
TRAIN_RATIO = 0.80
RANDOM_STATE = 42


def validate_source_folders() -> None:
    """Check that final_dataset and all required class folders exist."""
    if not SOURCE_DIR.exists():
        raise FileNotFoundError(f"Dataset folder not found: {SOURCE_DIR}")

    missing_folders = [class_name for class_name in CLASSES if not (SOURCE_DIR / class_name).is_dir()]
    if missing_folders:
        missing_text = ", ".join(missing_folders)
        raise FileNotFoundError(f"Missing class folder(s) inside final_dataset: {missing_text}")


def get_image_files(class_name: str) -> list[Path]:
    """Return only jpg, jpeg and png files for a class."""
    class_dir = SOURCE_DIR / class_name
    return sorted(
        file_path
        for file_path in class_dir.iterdir()
        if file_path.is_file() and file_path.suffix.lower() in VALID_EXTENSIONS
    )


def reset_output_folders() -> None:
    """Create a clean dataset_split folder."""
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)

    for split_name in ["train", "val"]:
        for class_name in CLASSES:
            (OUTPUT_DIR / split_name / class_name).mkdir(parents=True, exist_ok=True)


def unique_destination_path(destination_dir: Path, source_file: Path) -> Path:
    """Create a destination path without overwriting files with the same name."""
    candidate = destination_dir / source_file.name
    counter = 1

    while candidate.exists():
        candidate = destination_dir / f"{source_file.stem}_{counter}{source_file.suffix.lower()}"
        counter += 1

    return candidate


def copy_files(files: list[Path], split_name: str, class_name: str) -> None:
    """Copy image files into train or validation folders."""
    destination_dir = OUTPUT_DIR / split_name / class_name

    for source_file in files:
        destination_path = unique_destination_path(destination_dir, source_file)
        shutil.copy2(source_file, destination_path)


def split_files(image_files: list[Path]) -> tuple[list[Path], list[Path]]:
    """Split files safely, even when a class has only one image."""
    if len(image_files) == 1:
        return image_files, []

    return train_test_split(
        image_files,
        train_size=TRAIN_RATIO,
        random_state=RANDOM_STATE,
        shuffle=True,
    )


def main() -> None:
    validate_source_folders()
    reset_output_folders()

    print("Splitting dataset into 80% train and 20% validation...\n")

    for class_name in CLASSES:
        image_files = get_image_files(class_name)

        if not image_files:
            print(f"Warning: No valid image files found for class '{class_name}'.")
            print(f"{class_name}: train=0, val=0\n")
            continue

        train_files, val_files = split_files(image_files)

        copy_files(train_files, "train", class_name)
        copy_files(val_files, "val", class_name)

        print(f"{class_name}: train={len(train_files)}, val={len(val_files)}")

    print(f"\nDataset split completed. Output folder: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
