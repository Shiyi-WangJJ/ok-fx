from ok import OK

config = {
    "use_gui": True,
    "debug": True,
    "gui_title": "ok-fx",
    "gui_icon": ":/icon/icon.ico",
    "version": "1.0.0",
    "check_mutex": False,
    "onetime_task_interval": 2,  # 任务间间隔(秒)
    "adb": {},
    "template_matching": {
        "coco_feature_json": "ok_templates/coco_annotations.json",
        "default_threshold": 0.70,
        # variance 不写=使用 OK 默认值 0.002，只在标注位置附近搜索，又快又准
    },
    # 依次执行的任务（顺序 = 执行顺序, 开关控制是否参与全自动启动）
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
    # 后台弹窗监控（仅 点击继续，不含 确定）
    "trigger_tasks": [
        ["src.tasks.popups", "PopupTrigger"],
    ],
}

ok = OK(config)
ok.start()
