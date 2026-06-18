import os
import uuid


class Storage:
    def __init__(self, root):
        self.root = root
        os.makedirs(root, exist_ok=True)

    def _dir(self, doc_id):
        return os.path.join(self.root, doc_id)

    def new_doc(self, data: bytes) -> str:
        doc_id = uuid.uuid4().hex[:8]
        os.makedirs(self._dir(doc_id), exist_ok=True)
        with open(self.source_path(doc_id), "wb") as f:
            f.write(data)
        return doc_id

    def source_path(self, doc_id):
        return os.path.join(self._dir(doc_id), "source.pptx")

    def output_path(self, doc_id):
        return os.path.join(self._dir(doc_id), f"{doc_id}-out.pptx")

    def exists(self, doc_id):
        return os.path.isdir(self._dir(doc_id))
