from pathlib import Path
import json

import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers
from sklearn.metrics import classification_report, confusion_matrix, f1_score


# EfficientNetB0 with ImageNet weights expects RGB images in channels-last format:
# (height, width, 3). This line avoids local Keras config issues that can cause
# the model to be built as if images had 1 channel.
tf.keras.backend.set_image_data_format("channels_last")

# Project paths
PROJECT_DIR = Path(__file__).resolve().parent
DATASET_DIR = PROJECT_DIR / "dataset_split"
TRAIN_DIR = DATASET_DIR / "train"
VAL_DIR = DATASET_DIR / "val"
MODELS_DIR = PROJECT_DIR / "models"
OUTPUTS_DIR = PROJECT_DIR / "outputs"
GRADCAM_DIR = OUTPUTS_DIR / "gradcam_examples"

# Training settings
IMAGE_SIZE = (224, 224)
INPUT_SHAPE = (224, 224, 3)
BATCH_SIZE = 32
EPOCHS = 15
CLASS_NAMES = ["no_damage", "damaged", "collapsed"]


def validate_dataset() -> None:
    """Check that train and validation folders exist before training."""
    for split_dir in [TRAIN_DIR, VAL_DIR]:
        if not split_dir.exists():
            raise FileNotFoundError(
                f"Dataset split folder not found: {split_dir}\n"
                "Please run split_dataset.py before training."
            )

        missing_folders = [class_name for class_name in CLASS_NAMES if not (split_dir / class_name).is_dir()]
        if missing_folders:
            missing_text = ", ".join(missing_folders)
            raise FileNotFoundError(f"Missing folder(s) in {split_dir}: {missing_text}")


def load_datasets() -> tuple[tf.data.Dataset, tf.data.Dataset]:
    """Load train and validation images from folders."""
    train_dataset = tf.keras.utils.image_dataset_from_directory(
        str(TRAIN_DIR),
        labels="inferred",
        label_mode="categorical",
        class_names=CLASS_NAMES,
        image_size=IMAGE_SIZE,
        batch_size=BATCH_SIZE,
        color_mode="rgb",
        shuffle=True,
    )

    val_dataset = tf.keras.utils.image_dataset_from_directory(
        str(VAL_DIR),
        labels="inferred",
        label_mode="categorical",
        class_names=CLASS_NAMES,
        image_size=IMAGE_SIZE,
        batch_size=BATCH_SIZE,
        color_mode="rgb",
        shuffle=False,
    )

    # Prefetch improves training speed by preparing the next batch in advance.
    train_dataset = train_dataset.prefetch(buffer_size=tf.data.AUTOTUNE)
    val_dataset = val_dataset.prefetch(buffer_size=tf.data.AUTOTUNE)

    return train_dataset, val_dataset


def build_model() -> tf.keras.Model:
    """Build an EfficientNetB0 transfer learning model."""
    inputs = layers.Input(shape=INPUT_SHAPE)

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

    x = data_augmentation(inputs)
    x = base_model(x, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dropout(0.20)(x)
    outputs = layers.Dense(len(CLASS_NAMES), activation="softmax")(x)

    model = tf.keras.Model(inputs=inputs, outputs=outputs)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )

    return model


def save_class_names() -> None:
    """Save class order so predict.py can use the same class indexes."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    class_names_path = MODELS_DIR / "class_names.json"

    with class_names_path.open("w", encoding="utf-8") as file:
        json.dump(CLASS_NAMES, file, ensure_ascii=False, indent=2)


def plot_training_history(history: tf.keras.callbacks.History) -> None:
    """Save accuracy and loss graphics into the outputs folder."""
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(8, 5))
    plt.plot(history.history["accuracy"], label="Train Accuracy")
    plt.plot(history.history["val_accuracy"], label="Validation Accuracy")
    plt.title("Model Accuracy")
    plt.xlabel("Epoch")
    plt.ylabel("Accuracy")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(OUTPUTS_DIR / "accuracy.png")
    plt.close()

    plt.figure(figsize=(8, 5))
    plt.plot(history.history["loss"], label="Train Loss")
    plt.plot(history.history["val_loss"], label="Validation Loss")
    plt.title("Model Loss")
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(OUTPUTS_DIR / "loss.png")
    plt.close()


def save_confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray) -> None:
    """Save a confusion matrix image for validation predictions."""
    matrix = confusion_matrix(y_true, y_pred)

    plt.figure(figsize=(7, 6))
    plt.imshow(matrix, interpolation="nearest", cmap="Blues")
    plt.title("Confusion Matrix")
    plt.colorbar()

    tick_marks = np.arange(len(CLASS_NAMES))
    plt.xticks(tick_marks, CLASS_NAMES, rotation=30, ha="right")
    plt.yticks(tick_marks, CLASS_NAMES)

    threshold = matrix.max() / 2 if matrix.max() > 0 else 0
    for row_index in range(matrix.shape[0]):
        for col_index in range(matrix.shape[1]):
            color = "white" if matrix[row_index, col_index] > threshold else "black"
            plt.text(
                col_index,
                row_index,
                str(matrix[row_index, col_index]),
                ha="center",
                va="center",
                color=color,
            )

    plt.ylabel("True Label")
    plt.xlabel("Predicted Label")
    plt.tight_layout()
    plt.savefig(OUTPUTS_DIR / "confusion_matrix.png")
    plt.close()


def save_classification_report(y_true: np.ndarray, y_pred: np.ndarray) -> None:
    """Save precision, recall and F1-score values as a text report."""
    report = classification_report(y_true, y_pred, target_names=CLASS_NAMES, zero_division=0)
    macro_f1 = f1_score(y_true, y_pred, average="macro")
    weighted_f1 = f1_score(y_true, y_pred, average="weighted")

    report_text = (
        "Building Damage Classification Report\n"
        "=====================================\n\n"
        f"{report}\n"
        f"Macro F1-score: {macro_f1:.4f}\n"
        f"Weighted F1-score: {weighted_f1:.4f}\n"
    )

    with (OUTPUTS_DIR / "classification_report.txt").open("w", encoding="utf-8") as file:
        file.write(report_text)

    metrics = {
        "model_name": "EfficientNetB0 Transfer Learning",
        "macro_f1": round(float(macro_f1), 4),
        "weighted_f1": round(float(weighted_f1), 4),
    }
    with (OUTPUTS_DIR / "efficientnet_metrics.json").open("w", encoding="utf-8") as file:
        json.dump(metrics, file, indent=2)


def make_gradcam_heatmap(model: tf.keras.Model, image_batch: tf.Tensor, class_index: int) -> np.ndarray:
    """Create a Grad-CAM heatmap for EfficientNetB0's last convolution layer."""
    data_augmentation = model.get_layer("data_augmentation")
    efficientnet = model.get_layer("efficientnetb0")
    last_conv_layer = efficientnet.get_layer("top_conv")

    feature_model = tf.keras.Model(
        inputs=efficientnet.input,
        outputs=[last_conv_layer.output, efficientnet.output],
    )

    pooling_layer = next(layer for layer in model.layers if isinstance(layer, layers.GlobalAveragePooling2D))
    dropout_layer = next(layer for layer in model.layers if isinstance(layer, layers.Dropout))
    prediction_layer = model.layers[-1]

    with tf.GradientTape() as tape:
        augmented_image = data_augmentation(image_batch, training=False)
        conv_outputs, features = feature_model(augmented_image)
        x = pooling_layer(features)
        x = dropout_layer(x, training=False)
        predictions = prediction_layer(x)
        class_score = predictions[:, class_index]

    gradients = tape.gradient(class_score, conv_outputs)
    pooled_gradients = tf.reduce_mean(gradients, axis=(0, 1, 2))
    conv_outputs = conv_outputs[0]

    heatmap = conv_outputs @ pooled_gradients[..., tf.newaxis]
    heatmap = tf.squeeze(heatmap)
    heatmap = tf.maximum(heatmap, 0) / (tf.reduce_max(heatmap) + 1e-8)

    return heatmap.numpy()


def save_gradcam_examples(model: tf.keras.Model, val_dataset: tf.data.Dataset) -> None:
    """Save a few Grad-CAM examples from validation images."""
    GRADCAM_DIR.mkdir(parents=True, exist_ok=True)

    saved_count = 0
    for images, labels in val_dataset.take(2):
        predictions = model.predict(images, verbose=0)

        for image, label, prediction in zip(images, labels, predictions):
            true_index = int(np.argmax(label.numpy()))
            predicted_index = int(np.argmax(prediction))
            heatmap = make_gradcam_heatmap(model, tf.expand_dims(image, axis=0), predicted_index)

            plt.figure(figsize=(5, 5))
            plt.imshow(image.numpy().astype("uint8"))
            plt.imshow(heatmap, cmap="jet", alpha=0.40)
            plt.axis("off")
            plt.title(f"True: {CLASS_NAMES[true_index]} | Pred: {CLASS_NAMES[predicted_index]}")
            plt.tight_layout()
            plt.savefig(GRADCAM_DIR / f"gradcam_{saved_count + 1}.png")
            plt.close()

            saved_count += 1
            if saved_count >= 6:
                return


def evaluate_model(model: tf.keras.Model, val_dataset: tf.data.Dataset) -> None:
    """Generate confusion matrix, classification report and Grad-CAM examples."""
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    true_labels = []
    predicted_labels = []

    for images, labels in val_dataset:
        predictions = model.predict(images, verbose=0)
        true_labels.extend(np.argmax(labels.numpy(), axis=1))
        predicted_labels.extend(np.argmax(predictions, axis=1))

    y_true = np.array(true_labels)
    y_pred = np.array(predicted_labels)

    save_confusion_matrix(y_true, y_pred)
    save_classification_report(y_true, y_pred)
    save_gradcam_examples(model, val_dataset)


def update_efficientnet_history_metrics(history: tf.keras.callbacks.History) -> None:
    """Add validation accuracy and loss to the EfficientNet metric file."""
    metrics_path = OUTPUTS_DIR / "efficientnet_metrics.json"
    metrics = {}

    if metrics_path.exists():
        with metrics_path.open("r", encoding="utf-8") as file:
            metrics = json.load(file)

    metrics.update(
        {
            "model_name": "EfficientNetB0 Transfer Learning",
            "accuracy": round(float(history.history["val_accuracy"][-1]), 4),
            "loss": round(float(history.history["val_loss"][-1]), 4),
        }
    )

    with metrics_path.open("w", encoding="utf-8") as file:
        json.dump(metrics, file, indent=2)


def main() -> None:
    validate_dataset()

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    train_dataset, val_dataset = load_datasets()

    model = build_model()
    model.summary()

    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=3,
            restore_best_weights=True,
        ),
        tf.keras.callbacks.ModelCheckpoint(
            filepath=str(MODELS_DIR / "best_damage_model.keras"),
            monitor="val_loss",
            save_best_only=True,
        ),
        tf.keras.callbacks.ModelCheckpoint(
            filepath=str(MODELS_DIR / "best_damage_model.weights.h5"),
            monitor="val_loss",
            save_best_only=True,
            save_weights_only=True,
        ),
    ]

    history = model.fit(
        train_dataset,
        validation_data=val_dataset,
        epochs=EPOCHS,
        callbacks=callbacks,
    )

    model.save(str(MODELS_DIR / "final_damage_model.keras"))
    model.save_weights(str(MODELS_DIR / "final_damage_model.weights.h5"))
    save_class_names()
    plot_training_history(history)
    evaluate_model(model, val_dataset)
    update_efficientnet_history_metrics(history)

    print("\nTraining completed.")
    print(f"Best model saved to: {MODELS_DIR / 'best_damage_model.keras'}")
    print(f"Best model weights saved to: {MODELS_DIR / 'best_damage_model.weights.h5'}")
    print(f"Final model saved to: {MODELS_DIR / 'final_damage_model.keras'}")
    print(f"Final model weights saved to: {MODELS_DIR / 'final_damage_model.weights.h5'}")
    print(f"Class names saved to: {MODELS_DIR / 'class_names.json'}")
    print(f"Training plots saved to: {OUTPUTS_DIR}")
    print(f"Evaluation report saved to: {OUTPUTS_DIR / 'classification_report.txt'}")
    print(f"Confusion matrix saved to: {OUTPUTS_DIR / 'confusion_matrix.png'}")


if __name__ == "__main__":
    main()
