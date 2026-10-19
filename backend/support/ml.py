
"""AI-Based Complaint and Support System - ML and FAQ chatbot."""

import csv
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.pipeline import make_pipeline


BASE_DIR = Path(__file__).parent


# --------------------------------------------------
# TEXT PROCESSING
# --------------------------------------------------

def tokens(text):
    return re.findall(r"[a-z]+", str(text).lower())


# --------------------------------------------------
# NAIVE BAYES CLASSIFIER (BACKWARD COMPATIBILITY)
# --------------------------------------------------

class Classifier:
    """Multinomial Naive Bayes classifier kept for compatibility."""

    def __init__(self, rows):
        self.documents = Counter()
        self.words = defaultdict(Counter)
        self.vocabulary = set()

        for text, label in rows:
            words = tokens(text)
            self.documents[label] += 1
            self.words[label].update(words)
            self.vocabulary.update(words)

    def predict(self, text):
        counts = Counter(
            word for word in tokens(text)
            if word in self.vocabulary
        )

        if not counts or not self.documents:
            return "General Inquiry", 0.0

        scores = {}
        total = sum(self.documents.values())

        for label, count in self.documents.items():
            score = math.log(count / total)

            denominator = (
                sum(self.words[label].values())
                + len(self.vocabulary)
            )

            for word, frequency in counts.items():
                score += frequency * math.log(
                    (self.words[label][word] + 1) / denominator
                )

            scores[label] = score

        best = max(scores, key=scores.get)

        normalizer = sum(
            math.exp(score - scores[best])
            for score in scores.values()
        )

        return best, 1 / normalizer


# --------------------------------------------------
# DEPARTMENT ROUTING
# --------------------------------------------------

DEPARTMENTS = {
    "Technical Issue": "IT Support",
    "Billing/Payment": "Accounts",
    "Account Problem": "Account Support",
    "Service Complaint": "Customer Service",
    "Staff Complaint": "Human Resources",
    "Product Issue": "Product Support",
    "General Inquiry": "Help Desk",
}


# --------------------------------------------------
# CSV LOADING AND VALIDATION
# --------------------------------------------------

def read_csv(path, required_columns):
    """Read UTF-8 CSV files, including files with a BOM."""

    with Path(path).open(
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise ValueError(
                f"CSV file is empty or missing a header: {path}"
            )

        reader.fieldnames = [
            name.strip()
            for name in reader.fieldnames
        ]

        missing = set(required_columns) - set(reader.fieldnames)

        if missing:
            raise ValueError(
                f"Missing CSV columns in {path}: "
                f"{sorted(missing)}. "
                f"Found: {reader.fieldnames}"
            )

        rows = []

        for line_number, row in enumerate(reader, start=2):

            if None in row:
                raise ValueError(
                    f"Extra CSV fields found at line "
                    f"{line_number} in {path}"
                )

            cleaned = {
                key: (value or "").strip()
                for key, value in row.items()
            }

            if not any(cleaned.values()):
                continue

            if any(
                not cleaned.get(column)
                for column in required_columns
            ):
                raise ValueError(
                    f"Missing required value at line "
                    f"{line_number} in {path}"
                )

            rows.append(cleaned)

    if not rows:
        raise ValueError(f"No training rows found in {path}")

    return rows


# --------------------------------------------------
# CATEGORY TRAINING DATA
# --------------------------------------------------

def training_rows():
    file_path = BASE_DIR / "data" / "complaints.csv"

    rows = read_csv(
        file_path,
        required_columns=("text", "category")
    )

    return [
        (row["text"], row["category"])
        for row in rows
    ]


# --------------------------------------------------
# MACHINE LEARNING MODEL
# --------------------------------------------------

def fit_model(rows):
    rows = list(rows)

    if not rows:
        raise ValueError("Cannot train a model with no examples.")

    model = make_pipeline(
        TfidfVectorizer(
            ngram_range=(1, 2),
            sublinear_tf=True
        ),
        LogisticRegression(
            max_iter=1000,
            class_weight="balanced",
            random_state=42
        )
    )

    model.fit(
        [text for text, label in rows],
        [label for text, label in rows]
    )

    return model


class TextModel:
    """TF-IDF and Logistic Regression classifier."""

    def __init__(self, rows):
        rows = list(rows)

        self.pipeline = fit_model(rows)

        self.documents = Counter(
            label for text, label in rows
        )

    def predict(self, text):
        text = str(text or "")

        vector = self.pipeline[0].transform([text])

        if not vector.nnz:
            return "General Inquiry", 0.0

        probabilities = self.pipeline.predict_proba([text])[0]
        best = int(probabilities.argmax())

        return (
            str(self.pipeline.classes_[best]),
            float(probabilities[best])
        )


# Train category classifier
MODEL = TextModel(training_rows())


# --------------------------------------------------
# PRIORITY AND SENTIMENT MODELS
# --------------------------------------------------

signals = read_csv(
    BASE_DIR / "data" / "signals.csv",
    required_columns=("text", "priority", "sentiment")
)


PRIORITY_MODEL = fit_model([
    (row["text"], row["priority"])
    for row in signals
])


SENTIMENT_MODEL = fit_model([
    (row["text"], row["sentiment"])
    for row in signals
])


# --------------------------------------------------
# COMPLAINT ANALYSIS
# --------------------------------------------------

def analyze(text):
    """Classify complaint and return its analysis."""

    text = str(text or "")

    category, confidence = MODEL.predict(text)

    priority = str(
        PRIORITY_MODEL.predict([text])[0]
    )

    emergency_words = {
        "danger",
        "fire",
        "injury",
        "unsafe",
        "fraud",
        "threat",
        "emergency",
        "hacked",
        "leak"
    }

    if set(tokens(text)) & emergency_words:
        priority = "High"

    sentiment = str(
        SENTIMENT_MODEL.predict([text])[0]
    )

    department = DEPARTMENTS.get(
        category,
        "Help Desk"
    )

    return (
        category,
        priority,
        department,
        sentiment,
        confidence
    )


# --------------------------------------------------
# FAQ CHATBOT ANSWERS
# --------------------------------------------------

FAQ = [
    (
        {"track", "status", "tracking"},
        "Open Dashboard, then select your complaint ID "
        "to see its status, staff responses and activity history."
    ),
    (
        {"payment", "refund", "billing", "charged", "bill"},
        "Check your bill and transaction reference for "
        "unexpected charges. Submit a Billing complaint "
        "with the relevant details. Do not share passwords "
        "or full card details. Staff must review refunds."
    ),
    (
        {"password", "login", "account"},
        "Check your email and password. For a locked account, "
        "submit an Account Problem complaint for staff review."
    ),
    (
        {"internet", "wifi", "connection", "network"},
        "Restart your router and check cables. "
        "If the issue continues, submit a Technical Issue complaint."
    ),
    (
        {"submit", "complaint", "file"},
        "Select New complaint, enter a title and details, "
        "and submit. You will receive a complaint ID."
    ),
    (
        {"urgent", "emergency", "danger"},
        "For immediate danger, contact the appropriate "
        "emergency service directly. "
        "This demo is not monitored continuously."
    ),
]


# --------------------------------------------------
# FAQ TRAINING EXAMPLES
# --------------------------------------------------

FAQ_EXAMPLES = [

    # Complaint tracking
    ("track my complaint status", 0),
    ("how do I track my complaints", 0),
    ("where can I see my complaint progress", 0),
    ("check ticket status and responses", 0),
    ("where is my complaint", 0),

    # Billing and payments
    ("payment refund billing charged twice", 1),
    ("money deducted subscription inactive", 1),
    ("why is my bill higher than usual", 1),
    ("why is my bill higher than ususall", 1),
    ("unexpected high bill extra charges", 1),
    ("incorrect bill amount", 1),
    ("why was I charged extra money", 1),
    ("payment failed but money deducted", 1),
    ("how do I request a refund", 1),

    # Account problems
    ("password login locked account", 2),
    ("forgot password cannot sign in", 2),
    ("unable to login to my account", 2),
    ("my account is locked", 2),

    # Technical problems
    ("internet wifi network connection problem", 3),
    ("wifi keeps disconnecting", 3),
    ("internet is not working", 3),
    ("my connection is very slow", 3),

    # Complaint submission
    ("how do I submit a complaint", 4),
    ("create a new complaint", 4),
    ("where can I file a complaint", 4),
    ("how to register a complaint", 4),

    # Emergency
    ("urgent emergency danger help", 5),
    ("fire injury unsafe threat", 5),
]


# --------------------------------------------------
# FAQ SIMILARITY MODEL
# --------------------------------------------------

FAQ_VECTOR = TfidfVectorizer(
    ngram_range=(1, 2),
    stop_words="english"
)

FAQ_MATRIX = FAQ_VECTOR.fit_transform([
    phrase for phrase, intent in FAQ_EXAMPLES
])


# --------------------------------------------------
# CHATBOT RESPONSE FUNCTION
# --------------------------------------------------

def answer(text):
    """Return a suitable FAQ response."""

    text = str(text or "")
    words = set(tokens(text))

    if not words:
        return (
            "Please enter a question about complaints, "
            "billing, login, internet or support."
        )

    # Emergency has highest priority
    if words & {
        "emergency",
        "danger",
        "fire",
        "injury",
        "unsafe",
        "threat"
    }:
        return FAQ[5][1]

    # Complaint tracking
    if words & {
        "track",
        "tracks",
        "tracking",
        "status",
        "progress"
    }:
        return FAQ[0][1]

    # Billing and payments
    if words & {
        "bill",
        "bills",
        "billing",
        "charged",
        "charges",
        "refund",
        "payment",
        "payments"
    }:
        return FAQ[1][1]

    # Similarity-based FAQ matching
    question_vector = FAQ_VECTOR.transform([text])

    scores = cosine_similarity(
        question_vector,
        FAQ_MATRIX
    )[0]

    best = int(scores.argmax())

    if scores[best] >= 0.15:
        intent = FAQ_EXAMPLES[best][1]
        return FAQ[intent][1]

    return (
        "I can help with tracking, payments, login, "
        "internet and submitting complaints. "
        "Please submit a complaint for other support needs."
    )
