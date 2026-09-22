"""Chapter 07용 순수 Python/NumPy ML 호환 레이어.

Windows 애플리케이션 제어 정책이 SciPy의 컴파일 DLL/PYD를 차단하는 환경에서
scikit-learn 없이도 수업의 핵심 흐름(TF-IDF, Multinomial NB, stratified split,
평가 지표, cosine similarity)을 실행하기 위한 최소 구현입니다.
"""

from __future__ import annotations

import math
import re

import numpy as np


class TfidfVectorizer:
    """수업에 필요한 범위만 구현한 간단한 TF-IDF Vectorizer."""

    def __init__(self, lowercase: bool = True):
        self.lowercase = lowercase
        self.vocabulary_ = {}
        self.feature_names_ = None
        self.idf_ = None
        self._token_pattern = re.compile(r"(?u)\b\w\w+\b")

    def _analyze(self, document):
        text = "" if document is None else str(document)

        if self.lowercase:
            text = text.lower()

        return self._token_pattern.findall(text)

    def fit(self, documents):
        documents = list(documents)
        tokenized = [
            self._analyze(document)
            for document in documents
        ]

        terms = sorted({
            term
            for tokens in tokenized
            for term in tokens
        })

        if not terms:
            raise ValueError("empty vocabulary")

        self.feature_names_ = np.array(
            terms,
            dtype=object,
        )

        self.vocabulary_ = {
            term: index
            for index, term in enumerate(terms)
        }

        document_frequency = np.zeros(
            len(terms),
            dtype=float,
        )

        for tokens in tokenized:
            for term in set(tokens):
                document_frequency[
                    self.vocabulary_[term]
                ] += 1

        n_documents = len(documents)

        # scikit-learn 기본값과 같은 smooth IDF 형태입니다.
        self.idf_ = (
            np.log(
                (1 + n_documents)
                / (1 + document_frequency)
            )
            + 1.0
        )

        return self

    def transform(self, documents):
        if self.feature_names_ is None:
            raise ValueError(
                "Vectorizer가 아직 fit되지 않았습니다."
            )

        documents = list(documents)

        matrix = np.zeros(
            (
                len(documents),
                len(self.feature_names_),
            ),
            dtype=float,
        )

        for row_index, document in enumerate(documents):
            for term in self._analyze(document):
                column_index = self.vocabulary_.get(
                    term
                )

                if column_index is not None:
                    matrix[
                        row_index,
                        column_index,
                    ] += 1.0

        matrix *= self.idf_

        # scikit-learn TfidfVectorizer 기본값과 같은 L2 정규화입니다.
        norms = np.linalg.norm(
            matrix,
            axis=1,
            keepdims=True,
        )

        norms[norms == 0] = 1.0

        return matrix / norms

    def fit_transform(self, documents):
        documents = list(documents)

        self.fit(documents)

        return self.transform(documents)

    def get_feature_names_out(self):
        if self.feature_names_ is None:
            raise ValueError(
                "Vectorizer가 아직 fit되지 않았습니다."
            )

        return self.feature_names_.copy()


class MultinomialNB:
    """수업에 필요한 범위만 구현한 Multinomial Naive Bayes."""

    def __init__(self, alpha: float = 1.0):
        self.alpha = float(alpha)

    def fit(self, X, y):
        X = np.asarray(
            X,
            dtype=float,
        )

        y = np.asarray(
            list(y),
            dtype=object,
        )

        if X.ndim != 2:
            raise ValueError(
                "X는 2차원 행렬이어야 합니다."
            )

        if len(X) != len(y):
            raise ValueError(
                "X와 y 길이가 다릅니다."
            )

        self.classes_, encoded = np.unique(
            y,
            return_inverse=True,
        )

        class_count = np.bincount(
            encoded,
            minlength=len(self.classes_),
        ).astype(float)

        feature_count = np.zeros(
            (
                len(self.classes_),
                X.shape[1],
            ),
            dtype=float,
        )

        for class_index in range(
            len(self.classes_)
        ):
            feature_count[class_index] = (
                X[encoded == class_index]
                .sum(axis=0)
            )

        smoothed = (
            feature_count
            + self.alpha
        )

        self.feature_log_prob_ = np.log(
            smoothed
            / smoothed.sum(
                axis=1,
                keepdims=True,
            )
        )

        self.class_log_prior_ = np.log(
            class_count
            / class_count.sum()
        )

        return self

    def _joint_log_likelihood(self, X):
        X = np.asarray(
            X,
            dtype=float,
        )

        return (
            X @ self.feature_log_prob_.T
            + self.class_log_prior_
        )

    def predict(self, X):
        joint = self._joint_log_likelihood(
            X
        )

        return self.classes_[
            np.argmax(
                joint,
                axis=1,
            )
        ]

    def predict_proba(self, X):
        joint = self._joint_log_likelihood(
            X
        )

        joint = (
            joint
            - joint.max(
                axis=1,
                keepdims=True,
            )
        )

        exp_values = np.exp(
            joint
        )

        return (
            exp_values
            / exp_values.sum(
                axis=1,
                keepdims=True,
            )
        )


def train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=None,
    stratify=None,
):
    """이번 수업에 필요한 간단한 stratified train/test split."""

    n_samples = len(X)

    if len(y) != n_samples:
        raise ValueError(
            "X와 y 길이가 다릅니다."
        )

    rng = np.random.default_rng(
        random_state
    )

    if stratify is None:
        positions = np.arange(
            n_samples
        )

        rng.shuffle(
            positions
        )

        if isinstance(
            test_size,
            float,
        ):
            n_test = math.ceil(
                n_samples
                * test_size
            )
        else:
            n_test = int(
                test_size
            )

        test_positions = positions[
            :n_test
        ]

        train_positions = positions[
            n_test:
        ]

    else:
        labels = np.asarray(
            list(stratify),
            dtype=object,
        )

        train_parts = []
        test_parts = []

        for label in np.unique(
            labels
        ):
            positions = np.flatnonzero(
                labels == label
            )

            if len(positions) < 2:
                raise ValueError(
                    "stratify를 사용하려면 "
                    "각 클래스에 최소 2개 데이터가 필요합니다."
                )

            rng.shuffle(
                positions
            )

            if isinstance(
                test_size,
                float,
            ):
                n_test = int(
                    round(
                        len(positions)
                        * test_size
                    )
                )

                n_test = max(
                    1,
                    n_test,
                )

            else:
                # 현재 수업에서는 float test_size를 사용합니다.
                raise ValueError(
                    "stratify 사용 시 이번 호환 함수는 "
                    "float test_size를 사용하세요."
                )

            if n_test >= len(
                positions
            ):
                n_test = (
                    len(positions)
                    - 1
                )

            test_parts.append(
                positions[:n_test]
            )

            train_parts.append(
                positions[n_test:]
            )

        test_positions = np.concatenate(
            test_parts
        )

        train_positions = np.concatenate(
            train_parts
        )

        rng.shuffle(
            test_positions
        )

        rng.shuffle(
            train_positions
        )

    def take(values, positions):
        if hasattr(
            values,
            "iloc",
        ):
            return values.iloc[
                positions
            ]

        array = np.asarray(
            values
        )

        return array[
            positions
        ]

    return (
        take(
            X,
            train_positions,
        ),
        take(
            X,
            test_positions,
        ),
        take(
            y,
            train_positions,
        ),
        take(
            y,
            test_positions,
        ),
    )


def accuracy_score(
    y_true,
    y_pred,
):
    y_true = np.asarray(
        list(y_true),
        dtype=object,
    )

    y_pred = np.asarray(
        list(y_pred),
        dtype=object,
    )

    return float(
        np.mean(
            y_true == y_pred
        )
    )


def _class_metrics(
    y_true,
    y_pred,
):
    y_true = np.asarray(
        list(y_true),
        dtype=object,
    )

    y_pred = np.asarray(
        list(y_pred),
        dtype=object,
    )

    labels = np.array(
        sorted(
            set(y_true)
            | set(y_pred)
        ),
        dtype=object,
    )

    rows = {}

    for label in labels:
        true_positive = int(
            np.sum(
                (y_true == label)
                & (y_pred == label)
            )
        )

        false_positive = int(
            np.sum(
                (y_true != label)
                & (y_pred == label)
            )
        )

        false_negative = int(
            np.sum(
                (y_true == label)
                & (y_pred != label)
            )
        )

        support = int(
            np.sum(
                y_true == label
            )
        )

        precision = (
            true_positive
            / (
                true_positive
                + false_positive
            )
            if (
                true_positive
                + false_positive
            )
            else 0.0
        )

        recall = (
            true_positive
            / (
                true_positive
                + false_negative
            )
            if (
                true_positive
                + false_negative
            )
            else 0.0
        )

        f1 = (
            2
            * precision
            * recall
            / (
                precision
                + recall
            )
            if (
                precision
                + recall
            )
            else 0.0
        )

        rows[
            str(label)
        ] = {
            "precision": precision,
            "recall": recall,
            "f1-score": f1,
            "support": support,
        }

    return rows


def f1_score(
    y_true,
    y_pred,
    average="macro",
):
    rows = _class_metrics(
        y_true,
        y_pred,
    )

    if average == "macro":
        return float(
            np.mean([
                values["f1-score"]
                for values in rows.values()
            ])
        )

    if average == "weighted":
        support = sum(
            values["support"]
            for values in rows.values()
        )

        if support == 0:
            return 0.0

        return float(
            sum(
                values["f1-score"]
                * values["support"]
                for values in rows.values()
            )
            / support
        )

    raise ValueError(
        "이번 호환 함수는 macro 또는 weighted 평균을 지원합니다."
    )


def classification_report(
    y_true,
    y_pred,
    zero_division=0,
    output_dict=False,
):
    # zero_division은 scikit-learn 호출 형태와의 호환성을 위해 받습니다.
    _ = zero_division

    rows = _class_metrics(
        y_true,
        y_pred,
    )

    accuracy = accuracy_score(
        y_true,
        y_pred,
    )

    total_support = sum(
        values["support"]
        for values in rows.values()
    )

    macro = {
        key: float(
            np.mean([
                values[key]
                for values in rows.values()
            ])
        )
        for key in [
            "precision",
            "recall",
            "f1-score",
        ]
    }

    macro["support"] = total_support

    weighted = {
        key: (
            float(
                sum(
                    values[key]
                    * values["support"]
                    for values in rows.values()
                )
                / total_support
            )
            if total_support
            else 0.0
        )
        for key in [
            "precision",
            "recall",
            "f1-score",
        ]
    }

    weighted["support"] = total_support

    if output_dict:
        result = {
            label: values.copy()
            for label, values in rows.items()
        }

        result["accuracy"] = accuracy
        result["macro avg"] = macro
        result["weighted avg"] = weighted

        return result

    lines = [
        (
            f"{'':>20} "
            f"{'precision':>9} "
            f"{'recall':>9} "
            f"{'f1-score':>9} "
            f"{'support':>9}"
        ),
        "",
    ]

    for label, values in rows.items():
        lines.append(
            f"{label:>20} "
            f"{values['precision']:9.2f} "
            f"{values['recall']:9.2f} "
            f"{values['f1-score']:9.2f} "
            f"{values['support']:9d}"
        )

    lines.extend([
        "",
        (
            f"{'accuracy':>20} "
            f"{'':>9} "
            f"{'':>9} "
            f"{accuracy:9.2f} "
            f"{total_support:9d}"
        ),
        (
            f"{'macro avg':>20} "
            f"{macro['precision']:9.2f} "
            f"{macro['recall']:9.2f} "
            f"{macro['f1-score']:9.2f} "
            f"{total_support:9d}"
        ),
        (
            f"{'weighted avg':>20} "
            f"{weighted['precision']:9.2f} "
            f"{weighted['recall']:9.2f} "
            f"{weighted['f1-score']:9.2f} "
            f"{total_support:9d}"
        ),
    ])

    return "\n".join(
        lines
    )


def cosine_similarity(
    X,
    Y=None,
):
    X = np.atleast_2d(
        np.asarray(
            X,
            dtype=float,
        )
    )

    if Y is None:
        Y = X

    else:
        Y = np.atleast_2d(
            np.asarray(
                Y,
                dtype=float,
            )
        )

    numerator = (
        X @ Y.T
    )

    denominator = (
        np.linalg.norm(
            X,
            axis=1,
            keepdims=True,
        )
        * np.linalg.norm(
            Y,
            axis=1,
            keepdims=True,
        ).T
    )

    return np.divide(
        numerator,
        denominator,
        out=np.zeros_like(
            numerator,
            dtype=float,
        ),
        where=(
            denominator != 0
        ),
    )
