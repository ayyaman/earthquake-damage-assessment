from pathlib import Path
import json

import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers
from sklearn.metrics import f1_score


PROJECT_DIR = Path(__file__).resolve().parent
DATASET_DIR = PROJECT_DIR / "dataset_split"
TRAIN_DIR = DATASET_DIR / "train"
VAL_DIR = DATASET_DIR / "val"
MODELS_DIR = PROJECT_DIR / "models"
OUTPUTS_DIR = PROJECT_DIR / "outputs"

IMAGE_SIZE = (224, 224)
INPUT_SHAPE = (224, 224, 3)
BATCH_SIZE = 32
EPOCHS = 15
CLASS_NAMES = ["no_damage", "damaged", "collapsed"]


def load_datasets() -> tuple[tf.data.Dataset, tf.data.Dataset]:
    """Load train and validation images for the basic CNN baseline."""
    train_dataset = tf.keras.utils.image_dataset_from_directory(
        str(TRAIN_DIR),
        label_mode="categorical",
        class_names=CLASS_NAMES,
        image_size=IMAGE_SIZE,
        batch_size=BATCH_SIZE,
        color_mode="rgb",
        shuffle=True,
    )

    val_dataset = tf.keras.utils.image_dataset_from_directory(
        str(VAL_DIR),
        label_mode="categorical",
        class_names=CLASS_NAMES,
        image_size=IMAGE_SIZE,
        batch_size=BATCH_SIZE,
        color_mode="rgb",
        shuffle=False,
    )

    return (
        train_dataset.prefetch(tf.data.AUTOTUNE),
        val_dataset.prefetch(tf.data.AUTOTUNE),
    )


def build_basic_cnn() -> tf.keras.Model:
    """Build a small CNN from scratch for academic comparison."""
    model = tf.keras.Sequential(
        [
            layers.Input(shape=INPUT_SHAPE),
            layers.Rescaling(1.0 / 255),
            layers.Conv2D(32, 3, activation="relu"),
            layers.MaxPooling2D(),
            layers.Conv2D(64, 3, activation="relu"),
            layers.MaxPooling2D(),
            layers.Conv2D(128, 3, activation="relu"),
            layers.MaxPooling2D(),
            layers.Flatten(),
            layers.Dense(128, activation="relu"),
            layers.Dropout(0.30),
            layers.Dense(len(CLASS_NAMES), activation="softmax"),
        ],
        name="basic_cnn_from_scratch",
    )

    model.compile(
        optimizer=tf.keras.optimizers.Adam(),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def save_training_plots(history: tf.keras.callbacks.History) -> None:
    """Save baseline CNN accuracy and loss plots."""
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(8, 5))
    plt.plot(history.history["accuracy"], label="Train Accuracy")
    plt.plot(history.history["val_accuracy"], label="Validation Accuracy")
    plt.title("Basic CNN Accuracy")
    plt.xlabel("Epoch")
    plt.ylabel("Accuracy")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(OUTPUTS_DIR / "basic_cnn_accuracy.png")
    plt.close()

    plt.figure(figsize=(8, 5))
    plt.plot(history.history["loss"], label="Train Loss")
    plt.plot(history.history["val_loss"], label="Validation Loss")
    plt.title("Basic CNN Loss")
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(OUTPUTS_DIR / "basic_cnn_loss.png")
    plt.close()


def save_metrics(model: tf.keras.Model, val_dataset: tf.data.Dataset, history: tf.keras.callbacks.History) -> None:
    """Save basic CNN validation metrics for comparison with EfficientNetB0."""
    true_labels = []
    predicted_labels = []

    for images, labels in val_dataset:
        predictions = model.predict(images, verbose=0)
        true_labels.extend(np.argmax(labels.numpy(), axis=1))
        predicted_labels.extend(np.argmax(predictions, axis=1))

    metrics = {
        "model_name": "Basic CNN From Scratch",
        "accuracy": round(float(history.history["val_accuracy"][-1]), 4),
        "loss": round(float(history.history["val_loss"][-1]), 4),
        "macro_f1": round(float(f1_score(true_labels, predicted_labels, average="macro")), 4),
        "weighted_f1": round(float(f1_score(true_labels, predicted_labels, average="weighted")), 4),
    }

    with (OUTPUTS_DIR / "basic_cnn_metrics.json").open("w", encoding="utf-8") as file:
        json.dump(metrics, file, indent=2)


def main() -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    train_dataset, val_dataset = load_datasets()
    model = build_basic_cnn()
    model.summary()

    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=3,
            restore_best_weights=True,
        ),
        tf.keras.callbacks.ModelCheckpoint(
            filepath=str(MODELS_DIR / "basic_cnn_model.keras"),
            monitor="val_loss",
            save_best_only=True,
        ),
    ]

    history = model.fit(
        train_dataset,
        validation_data=val_dataset,
        epochs=EPOCHS,
        callbacks=callbacks,
    )

    save_training_plots(history)
    save_metrics(model, val_dataset, history)
    print("Basic CNN training completed.")


if __name__ == "__main__":
    main()
