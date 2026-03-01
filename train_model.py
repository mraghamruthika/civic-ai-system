import csv
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC


DATASET_PATH = Path("dataset.csv")
MODEL_PATH = Path("model.pkl")


def load_dataset(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Create dataset.csv first.")

    texts, labels = [], []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if "text" not in reader.fieldnames or "category" not in reader.fieldnames:
            raise ValueError("dataset.csv must contain headers: text,category")

        for row in reader:
            t = (row.get("text") or "").strip()
            y = (row.get("category") or "").strip()
            if t and y:
                texts.append(t)
                labels.append(y)

    if len(texts) < 10:
        raise ValueError("Add at least 10+ rows in dataset.csv for a meaningful model.")

    return texts, labels


def main():
    texts, labels = load_dataset(DATASET_PATH)

    # Pipeline = TF-IDF + Linear SVM (works great for text classification)
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            max_features=5000
        )),
        ("clf", LinearSVC())
    ])

    pipeline.fit(texts, labels)

    joblib.dump(pipeline, MODEL_PATH)
    print(f"✅ Model trained and saved to {MODEL_PATH} (rows={len(texts)})")


if __name__ == "__main__":
    main()