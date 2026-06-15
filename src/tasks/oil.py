"""领油线路"""
from ok.task.task import BaseTask
from ok import og

POPUPS = ["点击继续"]
STEPS = ["快速领取", "炼油厂", "排班", "编辑", "进行排班", "一键领取", "主页"]
NEED_CONFIRM = {"编辑", "进行排班"}


class OilTask(BaseTask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "2. 领油"
        self.description = "快速领取 → 炼油厂 → 排班 → 编辑 → 进行排班 → 一键领取 → 商店"
        self.sleep_check_interval = 0.3

    def sleep_check(self):
        """sleep 期间扫描弹窗"""
        for name in POPUPS:
            box = self.find_one(name)
            if box:
                self.log_info(f"弹窗: {box.name} -> 点击")
                self.click_box(box)
                return

    def _find_and_tap(self, name: str) -> bool:
        """找图 + 直接 adb 点击，比 wait_click_feature 快很多"""
        box = None
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

    def run(self):
        for i, name in enumerate(STEPS):
            if self.exit_is_set():
                return
            self.log_info(f">> Step {i+1}: {name}")

            # 快速轮询找图，最多等 10 秒
            found = False
            for _ in range(20):
                if self.exit_is_set():
                    return
                if self._find_and_tap(name):
                    self.sleep(1)
                    found = True
                    break
                self.sleep(0.5)

            if found:
                # 排班和编辑之后要点确定（轮询等弹窗）
                if name in NEED_CONFIRM:
                    self.sleep(0.5)
                    for _ in range(10):
                        if self._find_and_tap("确定"):
                            self.log_info("  已点击确定")
                            break
                        self.sleep(0.3)
            else:
                self.log_info(f"  {name} 未找到，跳过")

        # 一键领取后等主页
        self.log_info("等待主页...")
        self.sleep(2)
        while not self.exit_is_set() and self.enabled:
            if self._find_and_tap("主页"):
                self.log_info("主页已出现，完成")
                break
            og.device_manager.shell("input tap 355 59")
            self.sleep(1)

        self.log_info("领油完成")
