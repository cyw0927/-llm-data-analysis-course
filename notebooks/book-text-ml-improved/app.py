from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from kiwipiepy import Kiwi

from ml_compat import (
    TfidfVectorizer,
    MultinomialNB,
    cosine_similarity,
)


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "book_improved.csv"

TARGET_TAGS = {"NNG", "NNP", "SL"}
MIN_LENGTH = 2
STOPWORDS = {"에디션"}


st.set_page_config(
    page_title="도서 텍스트 분석 개선 앱",
    page_icon="📚",
    layout="wide",
)


@st.cache_resource(show_spinner=False)
def get_kiwi():
    """Kiwi 객체는 한 번만 생성해서 재사용합니다."""
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


@st.cache_data(show_spinner=False)
def load_data():
    """현재 폴더의 book_improved.csv를 읽고 기본 정리를 합니다."""
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"데이터 파일을 찾지 못했습니다: {DATA_PATH}"
        )

    df = pd.read_csv(
        DATA_PATH,
        encoding="utf-8-sig",
    )

    required_columns = ["상품명", "분야"]

    missing = [
        col
        for col in required_columns
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"필수 컬럼이 없습니다: {missing}"
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

    # 현재 CSV의 '인물' 컬럼을 앱에서는 '저자'로 함께 사용합니다.
    if "저자" not in df.columns and "인물" in df.columns:
        df["저자"] = (
            df["인물"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    if "출판사" in df.columns:
        df["출판사"] = (
            df["출판사"]
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
def prepare_data():
    """
    Kiwi 전처리는 시간이 걸리므로 최초 1회만 실행하고 캐시에 저장합니다.
    앱 첫 화면에서는 호출하지 않아서 화면이 바로 나타납니다.
    """
    df = load_data().copy()

    df["상품명_정제"] = (
        df["상품명"]
        .apply(preprocess_title)
    )

    return df


@st.cache_resource(show_spinner=False)
def train_classifier():
    """전처리된 전체 데이터로 앱 시연용 분류 모델을 준비합니다."""
    prepared_df = prepare_data()

    if prepared_df["분야"].nunique() < 2:
        raise ValueError(
            "분류에는 서로 다른 분야가 2개 이상 필요합니다."
        )

    vectorizer = TfidfVectorizer()

    X = vectorizer.fit_transform(
        prepared_df["상품명_정제"]
    )

    if X.shape[1] == 0:
        raise ValueError(
            "분류용 TF-IDF feature를 만들 수 없습니다."
        )

    model = MultinomialNB()

    model.fit(
        X,
        prepared_df["분야"],
    )

    return vectorizer, model


@st.cache_resource(show_spinner=False)
def build_recommender():
    """전처리된 제목으로 추천용 TF-IDF 행렬을 만듭니다."""
    prepared_df = prepare_data()

    vectorizer = TfidfVectorizer()

    title_matrix = vectorizer.fit_transform(
        prepared_df["상품명_정제"]
    )

    if title_matrix.shape[1] == 0:
        raise ValueError(
            "추천용 TF-IDF feature를 만들 수 없습니다."
        )

    return vectorizer, title_matrix


def recommend_books(
    df,
    title_matrix,
    selected_index,
    top_n=5,
):
    """같은 분야에서 유사도가 0보다 큰 도서만 추천합니다."""
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
            "DataFrame과 추천 행렬의 행 수가 다릅니다."
        )

    selected_title = df.iloc[selected_index]["상품명"]
    selected_category = df.iloc[selected_index]["분야"]

    candidate_indices = np.flatnonzero(
        df["분야"].to_numpy()
        == selected_category
    )

    similarities = cosine_similarity(
        title_matrix[
            selected_index:selected_index + 1
        ],
        title_matrix,
    ).ravel()

    sorted_candidates = candidate_indices[
        np.argsort(
            similarities[candidate_indices]
        )[::-1]
    ]

    selected = []

    for idx in sorted_candidates:
        idx = int(idx)

        # 자기 자신 제외
        if idx == selected_index:
            continue

        # 동일 제목 중복 제외
        if df.iloc[idx]["상품명"] == selected_title:
            continue

        # 유사도 0 이하 제외
        if similarities[idx] <= 0:
            continue

        selected.append(idx)

        if len(selected) >= top_n:
            break

    columns = [
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
        df.iloc[selected][columns]
        .copy()
        .reset_index(drop=True)
    )

    result["유사도"] = [
        round(
            float(similarities[idx]),
            4,
        )
        for idx in selected
    ]

    return result


# ------------------------------------------------------------
# 여기부터 화면을 먼저 그립니다.
# 무거운 Kiwi 전처리/모델 학습은 버튼을 눌렀을 때만 실행합니다.
# ------------------------------------------------------------

st.title(
    "📚 도서 텍스트 분석 개선 앱"
)

st.write(
    "book_improved.csv를 이용해 Kiwi 형태소 분석 기반 분야 예측과 "
    "같은 분야 내 유사 도서 추천을 실행합니다."
)

try:
    df = load_data()

except Exception as error:
    st.error(
        "데이터를 불러오는 중 오류가 발생했습니다."
    )
    st.exception(error)
    st.stop()


with st.expander(
    "현재 데이터 상태",
    expanded=True,
):
    col1, col2, col3 = st.columns(3)

    col1.metric(
        "도서 수",
        f"{len(df)}권",
    )

    col2.metric(
        "분야 수",
        f"{df['분야'].nunique()}개",
    )

    col3.metric(
        "데이터 파일",
        DATA_PATH.name,
    )

    counts = (
        df["분야"]
        .value_counts()
        .sort_index()
        .rename("도서 수")
    )

    st.dataframe(
        counts,
        use_container_width=True,
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
    key="predict_button",
):
    clean_title = user_title.strip()

    if not clean_title:
        st.warning(
            "도서 제목을 입력해 주세요."
        )

    else:
        try:
            with st.spinner(
                "처음 실행입니다. 900권 제목을 Kiwi로 분석하고 모델을 준비하는 중입니다..."
            ):
                classifier_vectorizer, classifier_model = (
                    train_classifier()
                )

            processed_title = preprocess_title(
                clean_title
            )

            if not processed_title:
                st.warning(
                    "형태소 분석 후 사용할 수 있는 핵심 토큰이 없습니다."
                )

            else:
                vector = classifier_vectorizer.transform(
                    [processed_title]
                )

                prediction = classifier_model.predict(
                    vector
                )[0]

                probabilities = classifier_model.predict_proba(
                    vector
                )[0]

                st.success(
                    f"예상 분야: {prediction}"
                )

                st.caption(
                    f"가장 높은 예측 확률: {float(probabilities.max()):.1%}"
                )

                with st.expander(
                    "형태소 분석 결과"
                ):
                    st.code(
                        processed_title
                    )

        except Exception as error:
            st.error(
                "분야 예측 준비 또는 실행 중 오류가 발생했습니다."
            )
            st.exception(error)


st.divider()


st.header(
    "2. 비슷한 도서 추천"
)


def format_book(index):
    row = df.iloc[index]
    title = str(row["상품명"])

    if "저자" in df.columns:
        author = str(
            row["저자"]
        ).strip()

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
    key="recommend_button",
):
    try:
        with st.spinner(
            "추천 모델을 준비하는 중입니다. 첫 실행만 조금 걸릴 수 있습니다..."
        ):
            _, title_matrix = (
                build_recommender()
            )

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
                "같은 분야 안에서 TF-IDF 코사인 유사도가 "
                "0보다 큰 도서만 표시합니다."
            )

    except Exception as error:
        st.error(
            "추천 준비 또는 실행 중 오류가 발생했습니다."
        )
        st.exception(error)


st.divider()

st.caption(
    "분류는 현재 900권 데이터의 제목 패턴을 이용한 예측이며 "
    "실제 공식 분야와 다를 수 있습니다."
)

st.caption(
    "추천은 같은 분야 안에서 제목 유사도가 0보다 큰 책만 반환합니다. "
    "추천 결과가 5권 미만이거나 없을 수도 있습니다."
)
