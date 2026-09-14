from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import streamlit as st

from features import MODEL_FEATURE_COLUMNS, build_model_features


# =========================================================
# 경로 설정
# =========================================================

APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parents[1]

MODEL_PATH = PROJECT_ROOT / "models" / "titanic_model_bundle.joblib"


# =========================================================
# 모델 Bundle 불러오기
# =========================================================

@st.cache_resource
def load_model_bundle():

    if not MODEL_PATH.is_file():
        raise FileNotFoundError(
            f"모델 파일이 없습니다.\n\n"
            f"{MODEL_PATH}"
        )

    bundle = joblib.load(MODEL_PATH)

    if not isinstance(bundle, dict):
        raise TypeError(
            "저장된 모델 파일이 예상한 dict 형태가 아닙니다."
        )

    required_keys = [
        "numeric_imputer",
        "categorical_imputer",
        "encoder",
        "scaler",
        "model",
    ]

    missing_keys = [
        key for key in required_keys
        if key not in bundle
    ]

    if missing_keys:
        raise KeyError(
            f"모델 Bundle에 필요한 항목이 없습니다: {missing_keys}"
        )

    return bundle


# =========================================================
# Bundle을 이용한 전처리
# =========================================================

def transform_features(
    bundle: dict,
    frame: pd.DataFrame,
):

    # 숫자형 컬럼
    numeric_columns = [
        "Age",
        "SibSp",
        "Parch",
        "Fare",
        "FamilySize",
    ]

    # 범주형 컬럼
    categorical_columns = [
        "Pclass",
        "Sex",
        "Embarked",
        "IsAlone",
    ]

    # -----------------------------------------------------
    # 숫자형 처리
    # -----------------------------------------------------

    numeric_data = frame[numeric_columns]

    numeric_imputed = bundle[
        "numeric_imputer"
    ].transform(
        numeric_data
    )

    numeric_scaled = bundle[
        "scaler"
    ].transform(
        numeric_imputed
    )

    # -----------------------------------------------------
    # 범주형 처리
    # -----------------------------------------------------

    categorical_data = frame[categorical_columns]

    categorical_imputed = bundle[
        "categorical_imputer"
    ].transform(
        categorical_data
    )

    categorical_encoded = bundle[
        "encoder"
    ].transform(
        categorical_imputed
    )

    # 혹시 sparse matrix인 경우 대비
    if hasattr(
        categorical_encoded,
        "toarray",
    ):
        categorical_encoded = (
            categorical_encoded.toarray()
        )

    # -----------------------------------------------------
    # 최종 Feature 결합
    # -----------------------------------------------------

    final_features = np.hstack(
        [
            numeric_scaled,
            categorical_encoded,
        ]
    )

    return final_features


# =========================================================
# 예측 함수
# =========================================================

def predict_survival(
    bundle: dict,
    frame: pd.DataFrame,
):

    final_features = transform_features(
        bundle,
        frame,
    )

    model = bundle["model"]

    predicted_class = int(
        model.predict(
            final_features
        )[0]
    )

    probabilities = model.predict_proba(
        final_features
    )

    classes = model.classes_

    positive_positions = np.where(
        classes == 1
    )[0]

    if len(positive_positions) != 1:
        raise ValueError(
            f"생존 class 1을 찾을 수 없습니다. "
            f"classes_: {classes}"
        )

    survival_probability = float(
        probabilities[
            0,
            positive_positions[0]
        ]
    )

    return (
        predicted_class,
        survival_probability,
        final_features,
    )


# =========================================================
# Streamlit 설정
# =========================================================

st.set_page_config(
    page_title="Titanic Survival Prediction",
    page_icon="🚢",
    layout="centered",
)


st.title("🚢 Titanic 생존 예측")

st.caption(
    "이 앱은 수업에서 직접 학습하고 저장한 머신러닝 모델을 사용합니다. "
    "예측 결과는 실제 생존 가능성을 보장하지 않습니다."
)


# =========================================================
# 모델 로딩
# =========================================================

try:

    bundle = load_model_bundle()

except Exception as exc:

    st.error(
        f"모델을 불러오는 중 오류가 발생했습니다.\n\n"
        f"{exc}"
    )

    st.stop()


# =========================================================
# 입력 폼
# =========================================================

with st.form(
    "passenger_form"
):

    pclass = st.selectbox(
        "객실 등급 (Pclass)",
        [1, 2, 3],
        index=2,
    )

    sex = st.selectbox(
        "성별 (Sex)",
        [
            "female",
            "male",
        ],
        index=1,
    )

    age = st.number_input(
        "나이 (Age)",
        min_value=0.0,
        max_value=100.0,
        value=30.0,
        step=1.0,
    )

    sibsp = st.number_input(
        "함께 탑승한 형제·배우자 수 (SibSp)",
        min_value=0,
        max_value=10,
        value=0,
        step=1,
    )

    parch = st.number_input(
        "함께 탑승한 부모·자녀 수 (Parch)",
        min_value=0,
        max_value=10,
        value=0,
        step=1,
    )

    fare = st.number_input(
        "운임 (Fare)",
        min_value=0.0,
        value=10.0,
        step=1.0,
    )

    embarked = st.selectbox(
        "탑승 항구 (Embarked)",
        [
            "S",
            "C",
            "Q",
        ],
        index=0,
    )

    submitted = st.form_submit_button(
        "예측하기"
    )


# =========================================================
# 예측 실행
# =========================================================

if submitted:

    raw_input = pd.DataFrame(
        [
            {
                "Pclass": pclass,
                "Sex": sex,
                "Age": age,
                "SibSp": sibsp,
                "Parch": parch,
                "Fare": fare,
                "Embarked": embarked,
            }
        ]
    )

    try:

        # -----------------------------------------------
        # features.py에서 FamilySize / IsAlone 생성
        # -----------------------------------------------

        feature_frame = build_model_features(
            raw_input
        )

        # 필요한 컬럼만 정리
        model_input = feature_frame[
            MODEL_FEATURE_COLUMNS
        ]

        # -----------------------------------------------
        # 예측
        # -----------------------------------------------

        (
            predicted_class,
            survival_probability,
            final_features,
        ) = predict_survival(
            bundle,
            model_input,
        )

        # -----------------------------------------------
        # 결과 출력
        # -----------------------------------------------

        st.divider()

        if predicted_class == 1:

            st.success(
                "모델 예측: 생존"
            )

        else:

            st.warning(
                "모델 예측: 비생존"
            )

        st.metric(
            "생존 확률",
            f"{survival_probability:.1%}",
        )

        # -----------------------------------------------
        # 입력값 확인
        # -----------------------------------------------

        with st.expander(
            "입력한 승객 정보 확인"
        ):

            st.dataframe(
                raw_input,
                width="stretch",
            )

        # -----------------------------------------------
        # 파생 Feature 확인
        # -----------------------------------------------

        with st.expander(
            "모델 입력 Feature 확인"
        ):

            st.dataframe(
                model_input,
                width="stretch",
            )

        st.info(
            "이 결과는 Titanic 학습 데이터를 기반으로 한 "
            "머신러닝 모델의 예측값입니다."
        )

    except Exception as exc:

        st.error(
            "예측 처리 중 오류가 발생했습니다.\n\n"
            f"{exc}"
        )