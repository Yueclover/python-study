import os
from app.storage import Storage


def test_new_doc_persists_source(tmp_path):
    st = Storage(str(tmp_path))
    doc_id = st.new_doc(b"hello-bytes")
    assert st.exists(doc_id)
    with open(st.source_path(doc_id), "rb") as f:
        assert f.read() == b"hello-bytes"
    assert st.output_path(doc_id).endswith(f"{doc_id}-out.pptx")


def test_missing_doc(tmp_path):
    st = Storage(str(tmp_path))
    assert st.exists("nope") is False
