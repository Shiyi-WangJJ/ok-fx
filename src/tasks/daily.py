"""出击-日常线路"""
from ok.task.task import BaseTask
from ok import og

POPUPS = ["点击继续"]
CARDS = ["武器运输", "通商护航", "综合演练", "军备科技", "战术训练", "战场探索"]


class DailyTask(BaseTask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "3. 出击-日常"
        self.description = "出击 -> 日常 -> 逐个扫荡6个卡片 -> 主页"
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

    def _any_card(self, done: set):
        for name in CARDS:
            if name in done:
                continue
            try:
                box = self.find_one(name, vertical_variance=0.1)
                if box:
                    return name, box
            except ValueError:
                pass
        return None, None

    def run(self):
        # 导航
        for step in ["出击", "日常"]:
            if self.exit_is_set():
                return
            self.log_info(f">> {step}")
            for _ in range(20):
                if self.exit_is_set():
                    return
                if self._find_and_tap(step):
                    self.sleep(1)
                    break
                self.sleep(0.3)
            else:
                self.log_info(f"  {step} 未找到，退出")
                return

        # 等页面加载
        self.log_info("等待卡片加载...")
        self.sleep(3)

        # 逐个扫荡
        done = set()
        while not self.exit_is_set() and self.enabled:
            name, box = self._any_card(done)
            if name is None:
                self.log_info("  所有卡片已处理")
                break

            self.log_info(f">> {name}")
            cx = box.x + box.width // 2
            cy = box.y + box.height // 2

            # 点卡片
            og.device_manager.shell(f"input tap {cx} {cy}")
            self.sleep(1)

            # 再点一次同位置
            og.device_manager.shell(f"input tap {cx} {cy}")
            self.sleep(2)  # 等系统确认弹窗

            # 点确定
            self._find_and_tap("确定")

            # 等奖励弹窗消失、卡片列表回来
            for _ in range(40):
                if self._any_card(done)[0]:
                    self.sleep(1.5)  # 等过渡动画完成，同时 sleep_check 处理残留弹窗
                    break
                self.sleep(0.2)
            else:
                self.sleep(3)

            done.add(name)
            self.log_info(f"  {name} 完成 ({len(done)}/6)")

        # 回主页
        self.log_info("等待主页...")
        while not self.exit_is_set() and self.enabled:
            if self._find_and_tap("主页"):
                self.log_info("主页已出现，完成")
                break
            og.device_manager.shell("input tap 355 59")
            self.sleep(1)

        self.log_info("出击-日常完成")
