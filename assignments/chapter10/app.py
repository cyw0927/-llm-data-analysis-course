from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.classification import FEATURE_COLUMNS, run_classification_analysis  # noqa: E402


PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORT_DIR = PROJECT_ROOT / "reports"

DAY_LABELS = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]


st.set_page_config(
    page_title="Chapter 10. 주문 취소 위험 예측",
    page_icon="📦",
    layout="wide",
)


@st.cache_resource(show_spinner=False)
def get_analysis_result():
    """Train/Validation/Test를 한 번만 실행하고 고정된 모델+threshold를 재사용합니다."""
    return run_classification_analysis(
        processed_dir=PROCESSED_DIR,
        report_dir=REPORT_DIR,
        test_size=0.2,
        val_size=0.2,
        random_state=42,
    )


def build_option_lists(model_data: pd.DataFrame) -> dict[str, list[str]]:
    return {
        "payment_method": sorted(model_data["payment_method"].dropna().unique().tolist()),
        "gender": sorted(model_data["gender"].dropna().unique().tolist()),
        "city": sorted(model_data["city"].dropna().unique().tolist()),
        "dominant_category": sorted(model_data["dominant_category"].dropna().unique().tolist()),
    }


st.title("📦 Chapter 10. 주문 취소 위험 예측")

st.write(
    "`chapter10.ipynb`에서 Validation으로 고정한 모델과 threshold를 그대로 불러와, "
    "새 주문 정보를 입력하면 취소 위험을 예측합니다."
)

try:
    with st.spinner("처음 실행입니다. 데이터를 불러오고 모델을 학습하는 중입니다..."):
        result = get_analysis_result()
except Exception as error:
    st.error("분석 파이프라인을 실행하는 중 오류가 발생했습니다.")
    st.exception(error)
    st.stop()

model_data = result["model_data"]
selected_model_name = result["selected_model_name"]
selected_threshold = result["selected_threshold"]
model = result["models"][selected_model_name]
test_metrics = result["test_metrics"]
options = build_option_lists(model_data)


with st.expander("현재 고정된 모델 정보", expanded=True):
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("선택된 모델", selected_model_name)
    col2.metric("선택된 Threshold", f"{selected_threshold:.2f}")

    selected_row = test_metrics.loc[test_metrics["model"].eq(selected_model_name)].iloc[0]
    baseline_row = test_metrics.loc[test_metrics["model"].eq("Dummy Most Frequent")].iloc[0]
    col3.metric(
        "Final Test F1",
        f"{selected_row['f1']:.3f}",
        delta=f"{selected_row['f1'] - baseline_row['f1']:+.3f} vs Baseline",
    )
    col4.metric("Final Test Recall", f"{selected_row['recall']:.3f}")

    st.caption(
        "Validation에서만 모델과 threshold를 선택하고, Final Test는 이 값을 고정한 뒤 "
        "마지막에 한 번만 확인했습니다. 자세한 과정은 chapter10.ipynb를 참고하세요."
    )


st.header("1. 새 주문의 취소 위험 예측")

with st.form("prediction_form"):
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        order_month = st.selectbox("주문 월", options=list(range(1, 13)), index=0)
        order_dayofweek_label = st.selectbox("주문 요일", options=DAY_LABELS, index=0)
        payment_method = st.selectbox("결제 수단", options=options["payment_method"])

    with col_b:
        age = st.number_input("고객 나이", min_value=15, max_value=100, value=30, step=1)
        gender = st.selectbox("고객 성별", options=options["gender"])
        city = st.selectbox("고객 거주 도시", options=options["city"])

    with col_c:
        item_count = st.number_input("장바구니 품목 수", min_value=1, max_value=50, value=2, step=1)
        total_quantity = st.number_input("총 수량", min_value=1, max_value=200, value=3, step=1)
        order_amount = st.number_input("주문 금액", min_value=0, value=50000, step=1000)

    col_d, col_e = st.columns(2)

    with col_d:
        category_count = st.number_input(
            "장바구니 카테고리 다양성 (서로 다른 카테고리 수)",
            min_value=1,
            max_value=10,
            value=1,
            step=1,
        )
        dominant_category = st.selectbox("가장 많이 담은 카테고리", options=options["dominant_category"])

    with col_e:
        tenure_known = st.checkbox("가입 후 경과일을 알고 있음", value=True)
        customer_tenure_days = st.number_input(
            "가입 후 주문까지 걸린 일수",
            min_value=0,
            max_value=3650,
            value=180,
            step=1,
            disabled=not tenure_known,
        )

    submitted = st.form_submit_button("취소 위험 예측", type="primary")

if submitted:
    order_dayofweek = DAY_LABELS.index(order_dayofweek_label)

    input_row = pd.DataFrame(
        [
            {
                "order_month": order_month,
                "order_dayofweek": order_dayofweek,
                "age": age,
                "item_count": item_count,
                "total_quantity": total_quantity,
                "order_amount": order_amount,
                "category_count": category_count,
                "customer_tenure_days": customer_tenure_days if tenure_known else pd.NA,
                "payment_method": payment_method,
                "gender": gender,
                "city": city,
                "dominant_category": dominant_category,
            }
        ]
    )[FEATURE_COLUMNS]

    try:
        cancel_probability = float(model.predict_proba(input_row)[0, 1])
    except Exception as error:
        st.error("예측 중 오류가 발생했습니다.")
        st.exception(error)
    else:
        is_risk = cancel_probability >= selected_threshold

        if is_risk:
            st.error(f"🚨 취소 위험 (예측 확률 {cancel_probability:.1%}, threshold {selected_threshold:.2f})")
        else:
            st.success(f"✅ 정상 완료 예상 (예측 확률 {cancel_probability:.1%}, threshold {selected_threshold:.2f})")

        st.caption(
            f"{selected_model_name}이(가) 학습 당시 Train 데이터로 이 확률을 계산했습니다. "
            "threshold보다 확률이 높으면 '취소 위험'으로 분류합니다."
        )

        with st.expander("입력한 주문 정보"):
            st.dataframe(input_row, hide_index=True, use_container_width=True)


st.divider()

st.header("2. 현재 모델의 Final Test 성능")

st.dataframe(test_metrics, hide_index=True, use_container_width=True)

confusion_figure = REPORT_DIR / "figures" / "ch10_confusion_matrix.png"
if confusion_figure.exists():
    st.image(str(confusion_figure), caption=f"Confusion Matrix ({selected_model_name}, threshold={selected_threshold:.2f})", width=400)

st.caption(
    "이 표와 이미지는 chapter10.ipynb / scripts/run_classification_analysis.py와 "
    "완전히 같은 로직(random_state=42)으로 만들어집니다."
)

st.divider()

st.caption(
    "이 예측은 교육용 random split으로 학습한 모델이며, 실제 운영 전에는 시간 순서 기반 "
    "out-of-time 검증과 FP/FN 실제 비용 분석이 추가로 필요합니다."
)
