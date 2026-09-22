from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from kiwipiepy import Kiwi
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.naive_bayes import MultinomialNB


BASE_DIR = Path(__file__).resolve().parent
IMPROVED_PATH = BASE_DIR / "books_improved.csv"
FALLBACK_PATH = BASE_DIR / "book_bestseller_clean.csv"

TARGET_TAGS = {"NNG", "NNP", "SL"}
MIN_LENGTH = 2
STOPWORDS = {"에디션"}


st.set_page_config(
    page_title="베스트셀러 텍스트 분석 앱",
    page_icon="📚",
    layout="wide",
)


@st.cache_resource(show_spinner=False)
def get_kiwi():
    return Kiwi()


def preprocess_title(text):
    """Kiwi 형태소 분석 + 최소 필터링으로 제목을 정제합니다."""
    kiwi = get_kiwi()

    words = []

    for token in kiwi.tokenize(str(text)):
        if token.tag not in TARGET_TAGS:
            continue

        word = token.form.strip().lower()

        if len(word) < MIN_LENGTH:
            continue

        if word.isdigit():
            continue

        if word in STOPWORDS:
            continue

        words.append(word)

    return " ".join(words)


def normalize_columns(df):
    df = df.copy()

    if "저자" not in df.columns and "인물" in df.columns:
        df = df.rename(
            columns={"인물": "저자"}
        )

    required_columns = [
        "상품명",
        "분야",
    ]

    missing_columns = [
        col
        for col in required_columns
        if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"필수 컬럼이 없습니다: {missing_columns}"
        )

    df["상품명"] = (
        df["상품명"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    df["분야"] = (
        df["분야"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    df = (
        df[
            (df["상품명"] != "") &
            (df["분야"] != "")
        ]
        .reset_index(drop=True)
    )

    if df.empty:
        raise ValueError(
            "사용할 수 있는 도서 데이터가 없습니다."
        )

    return df


@st.cache_data(show_spinner=False)
def load_data():
    if IMPROVED_PATH.exists():
        path = IMPROVED_PATH
        source = IMPROVED_PATH.name
        improved = True

    elif FALLBACK_PATH.exists():
        path = FALLBACK_PATH
        source = FALLBACK_PATH.name
        improved = False

    else:
        raise FileNotFoundError(
            "books_improved.csv 또는 book_bestseller_clean.csv를 "
            f"{BASE_DIR}에서 찾지 못했습니다."
        )

    df = pd.read_csv(
        path,
        encoding="utf-8-sig",
    )

    df = normalize_columns(df)

    return df, source, improved


@st.cache_resource(show_spinner=False)
def train_classifier():
    df, _, _ = load_data()

    train_df = df.copy()

    train_df["상품명_정제"] = (
        train_df["상품명"]
        .apply(preprocess_title)
    )

    if train_df["분야"].nunique() < 2:
        raise ValueError(
            "분류 모델에는 서로 다른 분야가 2개 이상 필요합니다."
        )

    vectorizer = TfidfVectorizer()

    X = vectorizer.fit_transform(
        train_df["상품명_정제"]
    )

    if X.shape[1] == 0:
        raise ValueError(
            "분류용 TF-IDF 단어 사전을 만들 수 없습니다."
        )

    model = MultinomialNB()

    model.fit(
        X,
        train_df["분야"],
    )

    return vectorizer, model


@st.cache_resource(show_spinner=False)
def build_recommender():
    df, _, _ = load_data()

    processed_titles = (
        df["상품명"]
        .apply(preprocess_title)
    )

    vectorizer = TfidfVectorizer()

    title_matrix = vectorizer.fit_transform(
        processed_titles
    )

    if title_matrix.shape[1] == 0:
        raise ValueError(
            "추천용 TF-IDF 단어 사전을 만들 수 없습니다."
        )

    return vectorizer, title_matrix


def recommend_books(
    df,
    title_matrix,
    selected_index,
    top_n=5,
):
    if top_n < 1:
        raise ValueError(
            "top_n은 1 이상이어야 합니다."
        )

    if not 0 <= selected_index < len(df):
        raise IndexError(
            f"유효하지 않은 index입니다: {selected_index}"
        )

    if len(df) != title_matrix.shape[0]:
        raise ValueError(
            "DataFrame 행 수와 추천 행렬 행 수가 다릅니다."
        )

    selected_title = df.iloc[
        selected_index
    ]["상품명"]

    selected_category = df.iloc[
        selected_index
    ]["분야"]

    candidate_indices = np.where(
        df["분야"].to_numpy()
        == selected_category
    )[0]

    selected_vector = title_matrix[
        selected_index:selected_index + 1
    ]

    similarities = cosine_similarity(
        selected_vector,
        title_matrix,
    ).ravel()

    sorted_candidates = candidate_indices[
        np.argsort(
            similarities[candidate_indices]
        )[::-1]
    ]

    recommended_indices = []

    for idx in sorted_candidates:
        idx = int(idx)

        if idx == selected_index:
            continue

        if df.iloc[idx]["상품명"] == selected_title:
            continue

        if similarities[idx] <= 0:
            continue

        recommended_indices.append(idx)

        if len(recommended_indices) >= top_n:
            break

    display_columns = [
        col
        for col in [
            "상품명",
            "저자",
            "출판사",
            "분야",
        ]
        if col in df.columns
    ]

    result = (
        df.iloc[recommended_indices][display_columns]
        .copy()
        .reset_index(drop=True)
    )

    result["유사도"] = [
        round(
            float(similarities[idx]),
            4,
        )
        for idx in recommended_indices
    ]

    return result


try:
    df, data_source, using_improved_data = load_data()

    classifier_vectorizer, classifier_model = (
        train_classifier()
    )

    _, title_matrix = build_recommender()

except Exception as error:
    st.error(
        "앱 준비 중 오류가 발생했습니다."
    )
    st.exception(error)
    st.stop()


st.title(
    "📚 교보문고 베스트셀러 텍스트 분석 앱"
)

st.write(
    "Kiwi 한국어 형태소 분석을 적용한 분야 예측과 "
    "근거가 있는 유사 도서 추천을 실습합니다."
)

if not using_improved_data:
    st.warning(
        "books_improved.csv를 찾지 못해 "
        "book_bestseller_clean.csv를 사용 중입니다. "
        "Chapter 07 실험과 같은 결과를 내려면 "
        "books_improved.csv를 app.py와 같은 폴더에 두세요."
    )

with st.expander(
    "현재 데이터/모델 상태",
    expanded=False,
):
    st.write(
        f"데이터 파일: **{data_source}**"
    )
    st.write(
        f"도서 수: **{len(df)}권**"
    )
    st.write(
        f"분야 수: **{df['분야'].nunique()}개**"
    )
    st.write(
        "전처리: **Kiwi NNG/NNP/SL + "
        "2글자 이상 + 숫자 제외 + 에디션 제외**"
    )


st.header(
    "1. 도서 분야 예측"
)

user_title = st.text_input(
    "도서 제목을 입력하세요",
    placeholder="예: 처음 배우는 파이썬 데이터 분석",
)

if st.button(
    "분야 예측",
    type="primary",
):
    clean_title = user_title.strip()

    if not clean_title:
        st.warning(
            "도서 제목을 입력해 주세요."
        )

    else:
        processed_title = preprocess_title(
            clean_title
        )

        if not processed_title:
            st.warning(
                "형태소 분석 후 사용할 수 있는 핵심 토큰이 없습니다."
            )

        else:
            title_vector = (
                classifier_vectorizer
                .transform(
                    [processed_title]
                )
            )

            predicted_category = (
                classifier_model
                .predict(title_vector)[0]
            )

            probabilities = (
                classifier_model
                .predict_proba(title_vector)[0]
            )

            best_probability = float(
                probabilities.max()
            )

            st.success(
                f"예상 분야: {predicted_category}"
            )

            st.caption(
                "모델의 가장 높은 예측 확률: "
                f"{best_probability:.1%}"
            )

            with st.expander(
                "형태소 분석 결과 보기"
            ):
                st.code(
                    processed_title
                )


st.divider()


st.header(
    "2. 비슷한 도서 추천"
)


def format_book(index):
    row = df.iloc[index]

    title = str(
        row["상품명"]
    )

    author = (
        str(row["저자"]).strip()
        if "저자" in df.columns
        else ""
    )

    if author and author.lower() != "nan":
        return (
            f"{index} | {title} | {author}"
        )

    return (
        f"{index} | {title}"
    )


selected_index = st.selectbox(
    "기준 도서를 선택하세요",
    options=list(
        range(len(df))
    ),
    format_func=format_book,
)

selected_columns = [
    col
    for col in [
        "상품명",
        "저자",
        "출판사",
        "분야",
    ]
    if col in df.columns
]

st.caption(
    "선택한 도서"
)

st.dataframe(
    df.iloc[
        [selected_index]
    ][selected_columns],
    hide_index=True,
    use_container_width=True,
)

if st.button(
    "비슷한 도서 최대 5권 추천",
    type="primary",
):
    recommendations = recommend_books(
        df=df,
        title_matrix=title_matrix,
        selected_index=int(
            selected_index
        ),
        top_n=5,
    )

    if recommendations.empty:
        st.info(
            "현재 기준으로 유사도가 있는 추천 도서를 찾지 못했습니다."
        )

    else:
        st.dataframe(
            recommendations,
            hide_index=True,
            use_container_width=True,
        )

        st.caption(
            "같은 분야 안에서 제목 TF-IDF 코사인 유사도가 "
            "0보다 큰 도서만 표시합니다."
        )


st.divider()

st.caption(
    "분류 결과는 현재 학습 데이터의 제목 패턴을 이용한 예측이며 "
    "실제 서점의 공식 분류와 다를 수 있습니다."
)

st.caption(
    "추천은 같은 분야의 제목 TF-IDF 유사도에 기반하며 "
    "유사도 0인 책은 억지로 Top 5에 포함하지 않습니다."
)

st.caption(
    "추천 결과가 없거나 5권 미만이어도 정상적인 결과입니다."
)
