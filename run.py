"""一次性跑所有线路，或在 GUI 里分别勾选执行。"""
import subprocess as _subprocess
import sys, os

# 全局屏蔽所有子进程的 CMD 窗口（Windows）
# 用类封装而非函数，避免破坏 asyncio 等库对 subprocess.Popen 的子类化
if sys.platform == 'win32':
    _CREATE_NO_WINDOW = getattr(_subprocess, 'CREATE_NO_WINDOW', 0x08000000)
    _original_popen = _subprocess.Popen
    class _PatchedPopen(_original_popen):
        def __init__(self, *args, **kwargs):
            kwargs.setdefault('creationflags', 0)
            kwargs['creationflags'] |= _CREATE_NO_WINDOW
            super().__init__(*args, **kwargs)
    _subprocess.Popen = _PatchedPopen

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ok import run_task

config = {
    "use_gui": False,
    "debug": False,
    "check_mutex": False,
    "onetime_task_interval": 2,  # 任务间间隔(秒)
    "adb": {},
    "template_matching": {
        "coco_feature_json": "ok_templates/coco_annotations.json",
        "default_threshold": 0.70,
    },
    "onetime_tasks": [
        ["src.tasks.login",    "LoginTask"],
        ["src.tasks.oil",      "OilTask"],
        ["src.tasks.daily",    "DailyTask"],
        ["src.tasks.exercise", "ExerciseTask"],
        ["src.tasks.expedition", "ExpeditionTask"],
        ["src.tasks.event", "EventTask"],
        ["src.tasks.mission", "MissionTask"],
        ["src.tasks.shop", "ShopTask"],
        ["src.tasks.oil", "OilTask"],
    ],
    "trigger_tasks": [
        ["src.tasks.popups", "PopupTrigger"],
    ],
}

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_task(config, task=sys.argv[1])
    else:
        run_task(config, task=1)  # 全跑
