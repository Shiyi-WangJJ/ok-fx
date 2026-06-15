"""全局弹窗监控 — 每 0.5s 检查一次，命中就点。"""
from ok.task.task import TriggerTask


class PopupTrigger(TriggerTask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "弹窗处理"
        self.description = "自动点击 点击继续"
        self.trigger_interval = 0.5

    def trigger(self):
        for name in ["点击继续"]:
            box = self.find_one(name)
            if box:
                self.log_info(f"弹窗: {box.name} → 点击")
                self.click_box(box)
                return True
        return False
