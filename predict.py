from pathlib import Path
import json

import numpy as np
import tensorflow as tf
from tensorflow.keras import layers
from PIL import Image


# Project paths
PROJECT_DIR = Path(__file__).resolve().parent
MODELS_DIR = PROJECT_DIR / "models"
MODEL_PATH = MODELS_DIR / "best_damage_model.keras"
WEIGHTS_PATH = MODELS_DIR / "best_damage_model.weights.h5"
CLASS_NAMES_PATH = MODELS_DIR / "class_names.json"

IMAGE_SIZE = (224, 224)
INPUT_SHAPE = (224, 224, 3)


class CompatibleBatchNormalization(layers.BatchNormalization):
    """Load BatchNormalization layers saved by slightly different Keras versions."""

    @classmethod
    def from_config(cls, config):
        # Some TensorFlow/Keras versions save these arguments, while newer Keras
        # versions may not accept them during loading.
        config.pop("renorm", None)
        config.pop("renorm_clipping", None)
        config.pop("renorm_momentum", None)
        return super().from_config(config)


def load_class_names() -> list[str]:
    """Load the class order saved during training."""
    if not CLASS_NAMES_PATH.exists():
        raise FileNotFoundError(
            f"Class names file not found: {CLASS_NAMES_PATH}\n"
            "Please run train_model.py before prediction."
        )

    with CLASS_NAMES_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_image(image_path: Path) -> np.ndarray:
    """Open an image, resize it and convert it to a model-ready batch."""
    if not image_path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    image = Image.open(image_path).convert("RGB")
    image = image.resize(IMAGE_SIZE)
    image_array = np.array(image, dtype=np.float32)

    # Add batch dimension: (224, 224, 3) -> (1, 224, 224, 3)
    return np.expand_dims(image_array, axis=0)


def build_model_for_prediction(class_count: int) -> tf.keras.Model:
    """Rebuild the training architecture and load only weights when needed."""
    data_augmentation = tf.keras.Sequential(
        [
            layers.RandomFlip("horizontal"),
            layers.RandomRotation(0.10),
            layers.RandomZoom(0.10),
        ],
        name="data_augmentation",
    )

    base_model = tf.keras.applications.EfficientNetB0(
        include_top=False,
        weights="imagenet",
        input_shape=INPUT_SHAPE,
    )
    base_model.trainable = False

    inputs = layers.Input(shape=INPUT_SHAPE)
    x = data_augmentation(inputs)
    x = base_model(x, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dropout(0.20)(x)
    outputs = layers.Dense(class_count, activation="softmax")(x)

    return tf.keras.Model(inputs=inputs, outputs=outputs)


def load_prediction_model(class_count: int) -> tf.keras.Model:
    """Load the model in the most version-tolerant way available."""
    if WEIGHTS_PATH.exists():
        model = build_model_for_prediction(class_count)
        model.load_weights(str(WEIGHTS_PATH))
        return model

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model file not found: {MODEL_PATH}\n"
            "Please run train_model.py before prediction."
        )

    return tf.keras.models.load_model(
        str(MODEL_PATH),
        custom_objects={"BatchNormalization": CompatibleBatchNormalization},
        compile=False,
        safe_mode=False,
    )


def predict_image(image_path: Path) -> dict:
    """Predict damage class for one image and return API-friendly results."""
    class_names = load_class_names()
    model = load_prediction_model(len(class_names))

    image_batch = load_image(image_path)
    predictions = model.predict(image_batch, verbose=0)[0]

    predicted_index = int(np.argmax(predictions))
    predicted_class = class_names[predicted_index]
    confidence = float(predictions[predicted_index]) * 100
    probabilities = {
        class_name: round(float(probability) * 100, 2)
        for class_name, probability in zip(class_names, predictions)
    }

    return {
        "predicted_class": predicted_class,
        "confidence": round(confidence, 2),
        "probabilities": probabilities,
    }


def main() -> None:
    user_input = input("Enter image path: ").strip().strip('"')
    result = predict_image(Path(user_input))

    print(f"\nPredicted class: {result['predicted_class']}")
    print(f"Confidence: {result['confidence']:.2f}%")
    print("All probabilities:")

    for class_name, probability in result["probabilities"].items():
        print(f"{class_name}: {probability:.2f}%")


if __name__ == "__main__":
    main()
