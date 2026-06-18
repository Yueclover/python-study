def slide_id_for(index0: int) -> str:
    return f"s{index0 + 1}"


def shape_short_id(order0: int) -> str:
    return f"sh{order0 + 1}"


def shape_id_for(slide_index0: int, shape_order0: int) -> str:
    return f"{slide_id_for(slide_index0)}_{shape_short_id(shape_order0)}"


class IdIndex:
    """解析与回写共用的确定性 ID → python-pptx 对象映射。

    在一次 /apply 会话内对内存中的同一个 Presentation 操作；
    dup_slide 产生的副本通过 register_temp_slide 注册临时页 ID。
    """

    def __init__(self, prs):
        self.prs = prs
        self._slides = {}        # slide_id -> slide
        self._shapes = {}        # shape_id -> shape
        self._temp_slides = {}   # temp_id -> slide
        for si, slide in enumerate(prs.slides):
            sid = slide_id_for(si)
            self._slides[sid] = slide
            for oi, shp in enumerate(slide.shapes):
                self._shapes[shape_id_for(si, oi)] = shp

    def slide(self, slide_id):
        if slide_id in self._temp_slides:
            return self._temp_slides[slide_id]
        return self._slides.get(slide_id)

    def register_temp_slide(self, temp_id, slide):
        self._temp_slides[temp_id] = slide

    def shape(self, shape_id):
        if "::" in shape_id:
            temp_id, short = shape_id.split("::", 1)
            slide = self._temp_slides.get(temp_id)
            if slide is None:
                return None
            try:
                order0 = int(short[2:]) - 1  # "sh2" -> 1
            except ValueError:
                return None
            shapes = list(slide.shapes)
            if 0 <= order0 < len(shapes):
                return shapes[order0]
            return None
        return self._shapes.get(shape_id)
