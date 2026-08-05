import subprocess
import sys

# 全局屏蔽所有子进程的 CMD 窗口（Windows）
# 用类封装而非函数，避免破坏 asyncio 等库对 subprocess.Popen 的子类化
if sys.platform == 'win32':
    _CREATE_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
    _original_popen = subprocess.Popen
    class _PatchedPopen(_original_popen):
        def __init__(self, *args, **kwargs):
            kwargs.setdefault('creationflags', 0)
            kwargs['creationflags'] |= _CREATE_NO_WINDOW
            super().__init__(*args, **kwargs)
    subprocess.Popen = _PatchedPopen

import os
from ok import OK

# PyAppify 打包后是 Release 模式，本地开发是 Debug 模式
is_release = bool(os.environ.get("PYAPPIFY_APP_VERSION"))

config = {
    "use_gui": True,
    "debug": not is_release,  # 本地 True，发布 False
    "gui_title": "ok-fx",
    "gui_icon": ":/icon.ico",
    "version": "1.0.34",
    "check_mutex": False,
    "onetime_task_interval": 2,  # 任务间间隔(秒)
    "adb": {},
    "template_matching": {
        "coco_feature_json": "ok_templates/coco_annotations.json",
        "default_threshold": 0.70,
        # variance 不写=使用 OK 默认值 0.002，只在标注位置附近搜索，又快又准
    },
    "ocr": {
        "default": {
            "lib": "rapidocr",
        },
    },
    # 依次执行的任务（顺序 = 执行顺序, 开关控制是否参与全自动启动）
    "onetime_tasks": [
        ["src.tasks.orchestrator", "DailyOrchestrator"],
        ["src.tasks.weekly", "WeeklyTask"],
    ],
    # 后台弹窗监控（仅 点击继续，不含 确定）
    "trigger_tasks": [
        ["src.tasks.popups", "PopupTrigger"],
    ],
}

ok = OK(config)
ok.start()
