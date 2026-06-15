"""任务-一键领取线路"""
from ok.task.task import BaseTask
from ok import og

POPUPS = ["点击继续"]


class MissionTask(BaseTask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "8. 任务"
        self.description = "任务 -> 任务一键领取 -> 连点15秒 -> 主页"
        self.sleep_check_interval = 0.5

    def sleep_check(self):
        for name in POPUPS:
            box = self.find_one(name)
            if box:
                self.log_info(f"弹窗: {box.name} -> 点击")
                self.click_box(box)
                return

    def _find_and_tap(self, name: str) -> bool:
        try:
            box = self.find_one(name)
        except ValueError:
            return False
        if box:
            cx = box.x + box.width // 2
            cy = box.y + box.height // 2
            og.device_manager.shell(f"input tap {cx} {cy}")
            return True
        return False

    def _poll_and_tap(self, name: str, timeout: float = 10) -> bool:
        for _ in range(int(timeout / 0.3)):
            if self.exit_is_set():
                return False
            if self._find_and_tap(name):
                self.sleep(1)
                return True
            self.sleep(0.3)
        return False

    def run(self):
        # 导航
        for name in ["任务", "任务一键领取"]:
            if self.exit_is_set():
                return
            self.log_info(f">> {name}")
            if not self._poll_and_tap(name, 10):
                self.log_info(f"  {name} 未找到，退出")
                return

        # 找到任务一键领取的位置
        box = self.find_one("任务一键领取")
        if box:
            cx, cy = box.x + box.width // 2, box.y + box.height // 2
        else:
            self.log_info("任务一键领取 未找到，退出")
            return

        # 每秒点同位置，连点 15 秒
        self.log_info(f"连点 15 秒 @ ({cx},{cy})...")
        for i in range(15):
            if self.exit_is_set():
                return
            og.device_manager.shell(f"input tap {cx} {cy}")
            self.log_info(f"  [{i+1}/15]")
            if i < 14:
                self.sleep(1)

        # 回主页
        self.log_info("等待主页...")
        while not self.exit_is_set() and self.enabled:
            if self._find_and_tap("主页"):
                self.log_info("主页已出现，完成")
                break
            og.device_manager.shell("input tap 355 59")
            self.sleep(1)

        self.log_info("任务完成")
