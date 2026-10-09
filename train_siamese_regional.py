def main() -> None:
    print(
        "Deprecated: supervised regional Siamese CNN training is not used because "
        "regional_dataset/images does not contain low/medium/high labels.\n"
        "Use batch_regional_analysis.py or predict_regional.py for unsupervised "
        "pre-post change analysis."
    )


if __name__ == "__main__":
    main()
