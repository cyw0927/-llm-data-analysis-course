from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.naive_bayes import MultinomialNB


BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "book_bestseller_clean.csv"
XLSX_PATH = BASE_DIR / "교보문고_종합_베스트셀러_상품리스트.xlsx"


st.set_page_config(
    page_title="베스트셀러 텍스트 분석 앱",
    page_icon="📚",
    layout="wide",
)


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """앱에서 사용하는 핵심 컬럼을 정리합니다."""
    df = df.copy()

    # 원본/전처리 파일에서 저자 컬럼 이름이 다를 수 있어 통일합니다.
    if "저자" not in df.columns and "인물" in df.columns:
        df = df.rename(columns={"인물": "저자"})

    required_columns = ["상품명", "분야"]
    missing_columns = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "필수 컬럼이 없습니다: "
            + ", ".join(missing_columns)
        )

    df["상품명"] = (
        df["상품명"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    df["분야"] = (
        df["분야"]
        .fillna("미분류")
        .astype(str)
        .str.strip()
        .replace("", "미분류")
    )

    if "저자" in df.columns:
        df["저자"] = (
            df["저자"]
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

    # 빈 제목은 사용할 수 없으므로 제외합니다.
    df = (
        df[df["상품명"] != ""]
        .reset_index(drop=True)
    )

    if df.empty:
        raise ValueError(
            "사용할 수 있는 도서 제목이 없습니다."
        )

    return df


@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    """CSV를 우선 사용하고, 없으면 원본 Excel을 자동으로 사용합니다."""
    if CSV_PATH.exists():
        df = pd.read_csv(
            CSV_PATH,
            encoding="utf-8-sig",
        )
        source = CSV_PATH.name

    elif XLSX_PATH.exists():
        df = pd.read_excel(
            XLSX_PATH,
        )
        source = XLSX_PATH.name

    else:
        raise FileNotFoundError(
            "도서 데이터 파일을 찾지 못했습니다.\n"
            f"- CSV: {CSV_PATH}\n"
            f"- Excel: {XLSX_PATH}"
        )

    df = _normalize_columns(df)
    return df, source


@st.cache_resource(show_spinner=False)
def train_classifier(df: pd.DataFrame):
    """앱 시연용 최종 분류 모델을 학습합니다."""
    train_df = (
        df[df["분야"] != "미분류"]
        .copy()
    )

    if train_df.empty:
        raise ValueError(
            "분류 모델을 학습할 라벨 데이터가 없습니다."
        )

    if train_df["분야"].nunique() < 2:
        raise ValueError(
            "분류 모델에는 서로 다른 분야가 2개 이상 필요합니다."
        )

    vectorizer = TfidfVectorizer()

    X = vectorizer.fit_transform(
        train_df["상품명"]
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
def build_recommender(df: pd.DataFrame):
    """전체 도서 제목을 추천용 TF-IDF 행렬로 변환합니다."""
    vectorizer = TfidfVectorizer()

    title_matrix = vectorizer.fit_transform(
        df["상품명"]
    )

    if title_matrix.shape[1] == 0:
        raise ValueError(
            "추천용 TF-IDF 단어 사전을 만들 수 없습니다."
        )

    return vectorizer, title_matrix


def recommend_books(
    df: pd.DataFrame,
    title_matrix,
    selected_index: int,
    top_n: int = 5,
) -> pd.DataFrame:
    """선택 도서와 제목 TF-IDF가 비슷한 다른 도서를 추천합니다."""
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

    # 1행 슬라이스로 가져와 SciPy 버전에 관계없이 2차원 형태를 유지합니다.
    selected_vector = title_matrix[
        selected_index:selected_index + 1
    ]

    similarities = cosine_similarity(
        selected_vector,
        title_matrix,
    ).ravel()

    selected_title = df.iloc[
        selected_index
    ]["상품명"]

    sorted_indices = np.argsort(
        similarities
    )[::-1]

    recommended_indices = []

    for idx in sorted_indices:
        idx = int(idx)

        # 자기 자신 제외
        if idx == selected_index:
            continue

        # 같은 제목이 중복 등록된 경우도 제외
        if df.iloc[idx]["상품명"] == selected_title:
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
    df, data_source = load_data()

    classifier_vectorizer, classifier_model = (
        train_classifier(df)
    )

    _, title_matrix = build_recommender(df)

except Exception as error:
    st.error("앱 준비 중 오류가 발생했습니다.")
    st.exception(error)
    st.stop()


st.title("📚 교보문고 베스트셀러 텍스트 분석 앱")

st.write(
    "도서 제목으로 분야를 예측하고, "
    "기존 도서와 제목이 비슷한 책을 추천합니다."
)

with st.expander("현재 데이터 상태", expanded=False):
    st.write(f"데이터 파일: **{data_source}**")
    st.write(f"도서 수: **{len(df)}권**")
    st.write(f"분야 수: **{df['분야'].nunique()}개**")
    st.write(
        f"분류 TF-IDF feature 수: "
        f"**{len(classifier_vectorizer.get_feature_names_out())}개**"
    )
    st.write(
        f"추천 TF-IDF matrix: "
        f"**{title_matrix.shape[0]} × {title_matrix.shape[1]}**"
    )


st.header("1. 도서 분야 예측")

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
        title_vector = (
            classifier_vectorizer
            .transform([clean_title])
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


st.divider()


st.header("2. 비슷한 도서 추천")


def format_book(index: int) -> str:
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
        return f"{index} | {title} | {author}"

    return f"{index} | {title}"


selected_index = st.selectbox(
    "기준 도서를 선택하세요",
    options=list(range(len(df))),
    format_func=format_book,
)

selected_book_columns = [
    col
    for col in [
        "상품명",
        "저자",
        "출판사",
        "분야",
    ]
    if col in df.columns
]

st.caption("선택한 도서")
st.dataframe(
    df.iloc[[selected_index]][selected_book_columns],
    hide_index=True,
    use_container_width=True,
)

if st.button(
    "비슷한 도서 5권 추천",
    type="primary",
):
    recommendations = recommend_books(
        df=df,
        title_matrix=title_matrix,
        selected_index=int(selected_index),
        top_n=5,
    )

    if recommendations.empty:
        st.warning(
            "추천할 수 있는 다른 도서가 없습니다."
        )
    else:
        st.dataframe(
            recommendations,
            hide_index=True,
            use_container_width=True,
        )


st.divider()

st.caption(
    "분류 결과는 현재 학습 데이터의 제목 패턴을 이용한 예측이며 "
    "실제 서점의 공식 분류와 다를 수 있습니다."
)

st.caption(
    "추천 결과는 제목 TF-IDF 코사인 유사도에 기반하며 "
    "개별 사용자의 취향을 직접 반영하지 않습니다."
)
