"""确定性拼装 frontend-slides Chatflow 的 Dify advanced-chat DSL。

用法:
    python dify/build_frontend_slides_chatflow.py
会(重新)生成 dify/frontend-slides-chatflow.yml。
"""
import importlib.util
from pathlib import Path

import yaml

_HERE = Path(__file__).resolve().parent


def _load_prompts():
    spec = importlib.util.spec_from_file_location(
        "fs_prompts", _HERE / "frontend_slides_prompts.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# —— 模型配置(用户按 Dify 内可用模型自行修改)——
MODEL_PROVIDER = "wxj/bifrost/bifrost"
PLAN_MODEL = "qwen3.6-plus"      # 策划:快即可
RENDER_MODEL = "qwen3.6-plus"    # 生成长 HTML:建议换成可用列表里最强的模型


def _llm_node(node_id, title, model, system_text, user_text, x):
    return {
        "id": node_id,
        "type": "custom",
        "width": 242, "height": 98,
        "position": {"x": x, "y": 100},
        "positionAbsolute": {"x": x, "y": 100},
        "selected": False,
        "sourcePosition": "right", "targetPosition": "left",
        "data": {
            "type": "llm", "title": title, "desc": "", "selected": False,
            "context": {"enabled": False, "variable_selector": []},
            "vision": {"enabled": False},
            "model": {
                "provider": MODEL_PROVIDER, "name": model, "mode": "chat",
                "completion_params": {"temperature": 0.2},
            },
            "prompt_template": [
                {"role": "system", "text": system_text},
                {"role": "user", "text": user_text},
            ],
        },
    }


def build_app() -> dict:
    prompts = _load_prompts()

    start = {
        "id": "start", "type": "custom",
        "width": 242, "height": 116,
        "position": {"x": 0, "y": 100},
        "positionAbsolute": {"x": 0, "y": 100},
        "selected": False, "sourcePosition": "right", "targetPosition": "left",
        "data": {
            "type": "start", "title": "开始", "desc": "", "selected": False,
            "variables": [
                {
                    "variable": "density", "label": "密度", "type": "select",
                    "required": False, "options": ["auto", "speaker-led", "reading-first"],
                    "default": "auto", "max_length": 48,
                },
                {
                    "variable": "pages", "label": "期望页数(选填)", "type": "number",
                    "required": False, "options": [],
                },
            ],
        },
    }

    plan_user = (
        "用户需求:\n{{#sys.query#}}\n\n"
        "密度:{{#start.density#}};期望页数:{{#start.pages#}}\n\n"
        "请只输出大纲 JSON。"
    )
    plan = _llm_node("plan", "策划", PLAN_MODEL,
                     prompts.PLAN_SYSTEM_PROMPT, plan_user, x=300)

    render_user = "大纲 JSON:\n{{#plan.text#}}\n\n请只输出最终 HTML 全文。"
    render = _llm_node("render", "生成", RENDER_MODEL,
                       prompts.build_render_system_prompt(), render_user, x=600)
    # 生成长 HTML,放宽采样
    render["data"]["model"]["completion_params"]["temperature"] = 0.4

    answer = {
        "id": "answer", "type": "custom",
        "width": 242, "height": 116,
        "position": {"x": 900, "y": 100},
        "positionAbsolute": {"x": 900, "y": 100},
        "selected": False, "sourcePosition": "right", "targetPosition": "left",
        "data": {
            "type": "answer", "title": "直接回复", "desc": "", "selected": False,
            "answer": "```html\n{{#render.text#}}\n```",
            "variables": [],
        },
    }

    def edge(src, dst):
        return {
            "id": f"{src}-{dst}", "source": src, "target": dst,
            "sourceHandle": "source", "targetHandle": "target",
            "type": "custom", "selected": False,
            "data": {"sourceType": "custom", "targetType": "custom", "isInLoop": False},
        }

    return {
        "app": {
            "name": "Frontend Slides 生成器",
            "description": "聊天给出主题/大纲,流式输出零依赖单文件 HTML 幻灯片(自动选风格)。",
            "mode": "advanced-chat",
            "icon": "🎬", "icon_background": "#1a1a1a", "icon_type": "emoji",
            "use_icon_as_answer_icon": False,
        },
        "kind": "app",
        "version": "0.6.0",
        "dependencies": [],
        "workflow": {
            "conversation_variables": [],
            "environment_variables": [],
            "features": {
                "file_upload": {"enabled": False},
                "opening_statement": "给我主题或大纲,我直接生成一套可保存为 .html 的幻灯片源码。",
                "retriever_resource": {"enabled": False},
                "sensitive_word_avoidance": {"enabled": False},
                "speech_to_text": {"enabled": False},
                "suggested_questions": [],
                "suggested_questions_after_answer": {"enabled": False},
                "text_to_speech": {"enabled": False, "language": "", "voice": ""},
            },
            "graph": {
                "nodes": [start, plan, render, answer],
                "edges": [edge("start", "plan"), edge("plan", "render"), edge("render", "answer")],
                "viewport": {"x": 0, "y": 0, "zoom": 0.8},
            },
            "rag_pipeline_variables": [],
        },
    }


def main():
    app = build_app()
    out = _HERE / "frontend-slides-chatflow.yml"
    out.write_text(
        yaml.safe_dump(app, allow_unicode=True, sort_keys=False, width=4096),
        encoding="utf-8",
    )
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
