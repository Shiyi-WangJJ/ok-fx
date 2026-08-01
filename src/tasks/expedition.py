"""远征线路 — 出击 -> 远征 -> 领取 -> 12小时 -> 依次出征远征1~4 -> 主页"""
from ok.task.task import BaseTask
from ok import og

POPUPS = ["点击继续"]
HOUR12 = ["12小时", "12小时2"]


class ExpeditionTask(BaseTask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "6. 远征"
        self.description = "出击 -> 远征 -> 远征全部领取 -> 12小时 -> 远征1~4依次出征 -> 返回主页"
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

    def _poll_and_tap(self, name, timeout: float = 5) -> bool:
        best_conf = 0
        for _ in range(int(timeout / 0.2)):
            if self.exit_is_set():
                return False
            if self._find_and_tap(name):
                self.sleep(1)
                return True
            try:
                boxes = self.find_feature(feature_name=name, limit=1)
                if boxes and boxes[0].confidence > best_conf:
                    best_conf = boxes[0].confidence
            except ValueError:
                pass
            self.sleep(0.2)
        if best_conf > 0:
            self.log_info(f"  {name} 最高置信度: {best_conf:.3f}")
        return False

    def _dispatch_one(self, exp_name: str):
        """点击远征槽位 -> 检查返航/出征"""
        self.log_info(f"  >> {exp_name}")
        if not self._poll_and_tap(exp_name, 10):
            self.log_info(f"    {exp_name} 未找到，跳过")
            return False
        self.sleep(0.5)

        # 如果位置显示"返航"，说明已出征，跳过（只检测不点击）
        try:
            if self.find_one("返航"):
                self.log_info(f"    已是返航状态，跳过")
                return True
        except ValueError:
            pass

        # 否则正常点出征
        if not self._poll_and_tap("出征", 10):
            self.log_info(f"    出征 未找到，跳过")
            return False
        self.sleep(0.5)
        return True

    def run(self):
        # 1. 出击 -> 远征
        self.log_info(">> 出击")
        if not self._poll_and_tap("出击", 10):
            self.log_info("  出击 未找到，退出")
            return

        self.log_info(">> 远征")
        if not self._poll_and_tap("远征", 10):
            self.log_info("  远征 未找到，退出")
            return

        # 2. 远征全部领取
        self.log_info(">> 远征全部领取")
        if not self._poll_and_tap("远征全部领取", 10):
            self.log_info("  远征全部领取 未找到，跳过")
        self.sleep(2)

        # 3. 12小时（双模板，任意一个匹配即可）
        self.log_info(">> 12小时")
        if not self._poll_and_tap(HOUR12, 10):
            self.log_info("  12小时 未找到，跳过")
        self.sleep(0.5)

        # 4. 依次出征 远征1 ~ 远征3
        for exp_name in ["远征1", "远征2", "远征3"]:
            if self.exit_is_set():
                return
            self._dispatch_one(exp_name)

        # 5. 在远征列表区域往上拉动露出远征4
        self.log_info(">> 拉动列表，露出远征4")
        self.swipe_relative(0.69, 0.72, 0.69, 0.35, duration=0.5)
        self.sleep(1)

        # 6. 远征4 -> 出征
        self._dispatch_one("远征4")

        # 7. 返回主页
        self.log_info(">> 返回主页")
        self.sleep(3)
        while not self.exit_is_set() and self.enabled:
            if self._find_and_tap("主页"):
                self.log_info("主页已出现，完成")
                break
            og.device_manager.shell("input tap 355 59")
            self.sleep(1)

        self.log_info("远征完成")
