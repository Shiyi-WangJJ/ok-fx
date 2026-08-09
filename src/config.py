"""OK-Script 默认配置（供 CLI `ok run_task` 使用）"""

config = {
    "use_gui": False,
    "debug": False,
    "gui_title": "ok-fx",
    "gui_icon": ":/icon.ico",
    "version": "1.0.0",
    "check_mutex": False,
    "onetime_task_interval": 2,
    "adb": {},
    "template_matching": {
        "coco_feature_json": "ok_templates/coco_annotations.json",
        "default_threshold": 0.70,
    },
    "onetime_tasks": [
        ["src.tasks.login", "LoginTask"],
        ["src.tasks.oil", "OilTask"],
        ["src.tasks.daily", "DailyTask"],
        ["src.tasks.exercise", "ExerciseTask"],
        ["src.tasks.arena", "ArenaTask"],
        ["src.tasks.event", "EventTask"],
        ["src.tasks.expedition", "ExpeditionTask"],
        ["src.tasks.mission", "MissionTask"],
        ["src.tasks.oil", "OilTask"],
    ],
    "trigger_tasks": [],
}
