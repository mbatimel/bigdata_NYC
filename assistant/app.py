import streamlit as st

from agent import generate_sql, load_semantic_layer, run_sql, schema_summary, summarize


st.set_page_config(page_title="DLH BI Assistant", layout="wide")

st.title("SQL BI Assistant")

with st.sidebar:
    st.subheader("Lakehouse")
    st.caption("Trino -> Iceberg -> MinIO")
    semantic = load_semantic_layer()
    st.write("Tables")
    for table_name, meta in semantic["tables"].items():
        st.markdown(f"- `{table_name}`")
        st.caption(meta["description"])

    with st.expander("Schema"):
        st.code(schema_summary() or "Run ETL first", language="text")

question = st.text_input(
    "Question",
    value="Покажи топ-10 маршрутов по количеству поездок",
)

if st.button("Run", type="primary") and question:
    with st.spinner("Generating SQL and querying Trino"):
        diagnostics = []
        sql = generate_sql(question, diagnostics)
        try:
            df = run_sql(sql)
        except Exception as exc:
            st.error("Trino query failed. Check that the stack is up and ETL has finished.")
            st.code(str(exc), language="text")
            st.subheader("SQL")
            st.code(sql, language="sql")
            st.stop()
        answer = summarize(question, sql, df, diagnostics)

    st.subheader("Answer")
    st.write(answer)

    if diagnostics:
        st.warning(
            "LLM вызов не завершился успешно, поэтому ассистент использовал "
            "offline fallback для SQL или ответа."
        )
        with st.expander("LLM diagnostics"):
            for item in diagnostics:
                st.code(item, language="text")

    st.subheader("SQL")
    st.code(sql, language="sql")

    st.subheader("Result")
    st.dataframe(df, use_container_width=True, hide_index=True)
