"""一次性跑所有线路，或在 GUI 里分别勾选执行。"""
import subprocess as _subprocess
import sys, os

# 全局屏蔽所有子进程的 CMD 窗口（Windows）
if sys.platform == 'win32':
    _CREATE_NO_WINDOW = getattr(_subprocess, 'CREATE_NO_WINDOW', 0x08000000)
    _original_popen = _subprocess.Popen
    def _patched_popen(*args, **kwargs):
        kwargs.setdefault('creationflags', 0)
        kwargs['creationflags'] |= _CREATE_NO_WINDOW
        return _original_popen(*args, **kwargs)
    _subprocess.Popen = _patched_popen

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
        ["src.tasks.mission", "MissionTask"],
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
