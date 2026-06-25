"""商店-每日礼包线路"""
from ok.task.task import BaseTask
from ok import og

POPUPS = ["点击继续"]


class ShopTask(BaseTask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "9. 商店-每日礼包"
        self.description = "商店 -> 每日礼包 -> 每日启航包 -> 免费购买 -> 主页"
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

    def _find_one_safe(self, name: str):
        try:
            return self.find_one(name)
        except ValueError:
            return None

    def _wait_and_tap(self, name: str, timeout: float = 10) -> bool:
        """轮询等待并点击，返回是否成功"""
        for _ in range(int(timeout / 0.3)):
            if self.exit_is_set() or not self.enabled:
                return False
            if self._find_and_tap(name):
                return True
            self.sleep(0.3)
        return False

    def run(self):
        # Step 1: 进商店
        self.log_info(">> 商店")
        if not self._wait_and_tap("商店", timeout=15):
            self.log_info("  商店未找到，退出")
            return
        self.sleep(1.5)

        # Step 2: 每日礼包
        self.log_info(">> 每日礼包")
        if not self._wait_and_tap("每日礼包", timeout=10):
            self.log_info("  每日礼包未找到，退出")
            return
        self.sleep(1.5)

        # Step 3: 每日启航包 — 检测不到直接回主页退出
        self.log_info(">> 每日启航包")
        found = False
        for _ in range(15):
            if self.exit_is_set() or not self.enabled:
                return
            box = self._find_one_safe("每日启航包")
            if box:
                self.log_info("  每日启航包 已出现，点击")
                self.click_box(box)
                self.sleep(1)
                found = True
                break
            self.sleep(0.3)

        if not found:
            self.log_info("  每日启航包 未检测到，回主页退出")
            self._go_home()
            return

        # Step 4: 免费购买
        self.log_info(">> 免费购买")
        if not self._wait_and_tap("免费购买", timeout=10):
            self.log_info("  免费购买未找到")
        else:
            self.sleep(1)
            self.log_info("  免费购买 完成")

        # Step 5: 回主页
        self.log_info(">> 回主页")
        self._go_home()
        self.log_info("商店-每日礼包完成")

    def _go_home(self):
        """回到主页"""
        while not self.exit_is_set() and self.enabled:
            if self._find_and_tap("主页"):
                self.log_info("  主页已出现")
                break
            og.device_manager.shell("input tap 355 59")
            self.sleep(1)
