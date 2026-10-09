from pathlib import Path
import json


PROJECT_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = PROJECT_DIR / "outputs"


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Metric file not found: {path}")
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def main() -> None:
    efficientnet = load_json(OUTPUTS_DIR / "efficientnet_metrics.json")
    basic_cnn = load_json(OUTPUTS_DIR / "basic_cnn_metrics.json")

    report = f"""Model Comparison Report
=======================

EfficientNetB0 Transfer Learning
- Accuracy: {efficientnet.get("accuracy", "N/A")}
- Loss: {efficientnet.get("loss", "N/A")}
- Macro F1-score: {efficientnet.get("macro_f1", "N/A")}
- Weighted F1-score: {efficientnet.get("weighted_f1", "N/A")}

Basic CNN From Scratch
- Accuracy: {basic_cnn.get("accuracy", "N/A")}
- Loss: {basic_cnn.get("loss", "N/A")}
- Macro F1-score: {basic_cnn.get("macro_f1", "N/A")}
- Weighted F1-score: {basic_cnn.get("weighted_f1", "N/A")}

Academic Interpretation
EfficientNetB0 uses transfer learning from ImageNet and is expected to learn
stronger visual features with less project-specific data. The Basic CNN is a
baseline model trained from scratch and is useful for demonstrating why transfer
learning is valuable in disaster image classification tasks.
"""

    output_path = OUTPUTS_DIR / "model_comparison_report.txt"
    with output_path.open("w", encoding="utf-8") as file:
        file.write(report)

    print(report)
    print(f"Saved to: {output_path}")


if __name__ == "__main__":
    main()
