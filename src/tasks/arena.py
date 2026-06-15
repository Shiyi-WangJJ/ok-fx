"""出击-竞技线路"""
from ok.task.task import BaseTask
from ok import og

POPUPS = ["点击继续"]
STEPS = ["出击", "竞技", "争锋竞技", "无畏舰队"]
NEED_CONFIRM = {"无畏舰队"}


class ArenaTask(BaseTask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "5. 出击-竞技"
        self.description = "出击 -> 竞技 -> 争锋竞技 -> 无畏舰队 -> 等主页"
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
        for _ in range(int(timeout / 0.5)):
            if self.exit_is_set():
                return False
            if self._find_and_tap(name):
                self.sleep(1)
                return True
            self.sleep(0.5)
        return False

    def run(self):
        for name in STEPS:
            if self.exit_is_set():
                return
            self.log_info(f">> {name}")
            if not self._poll_and_tap(name, 10):
                self.log_info(f"  {name} 未找到，跳过")
            elif name in NEED_CONFIRM:
                self.sleep(0.5)
                for _ in range(10):
                    if self._find_and_tap("确定"):
                        self.log_info("  已点击确定")
                        break
                    self.sleep(0.3)

        # 等 20 秒战斗
        self.log_info("等待战斗结束 (20s)...")
        self.sleep(20)

        # 等待主页出现（每秒点一次主页位置）
        self.log_info("等待主页...")
        while not self.exit_is_set() and self.enabled:
            if self._find_and_tap("主页"):
                self.log_info("主页已出现，完成")
                break
            og.device_manager.shell("input tap 355 59")
            self.sleep(1)

        self.log_info("出击-竞技完成")
