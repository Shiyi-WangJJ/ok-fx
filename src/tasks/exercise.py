"""出击-演习线路：有亮卡就战，没卡换对手，直到更换对手也找不到"""
from ok.task.task import BaseTask
from ok import og

POPUPS = ["点击继续"]
CARDS = ["亮1", "亮2", "亮3", "亮4", "亮5"]
FIGHT_STEPS = ["连续挑战", "全选", "开始托管"]


class ExerciseTask(BaseTask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "4. 出击-演习"
        self.description = "出击 -> 演习 -> 有卡连战 -> 没卡换对手 -> 直到对手用完"
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

    def _any_card(self) -> bool:
        """亮1-5 有任意一个匹配到"""
        for name in CARDS:
            try:
                box = self.find_one(name)
                if box:
                    self.log_info(f"  命中: {name} conf={box.confidence:.3f} @ ({box.x},{box.y})")
                    return True
            except ValueError:
                pass
        return False

    def _in_exercise(self) -> bool:
        """演习奖励能匹配到说明在演习界面"""
        try:
            return self.find_one("演习奖励") is not None
        except ValueError:
            return False

    def run(self):
        # ---- 导航：出击 -> 演习 ----
        for step in ["出击", "演习"]:
            if self.exit_is_set():
                return
            self.log_info(f">> {step}")
            if not self._poll_and_tap(step, 10):
                self.log_info(f"  {step} 未找到，退出")
                return

        # ---- 循环：有卡就打，没卡换对手 ----
        round_num = 0
        while not self.exit_is_set() and self.enabled:
            if self.exit_is_set():
                return
            round_num += 1
            self.log_info(f">> 轮次 {round_num}: 检测状态...")
            self.log_info(f"  亮卡:{self._any_card()} 演习奖励:{self._in_exercise()}")

            if self._any_card():
                # 有亮卡就开战
                self.log_info("  检测到亮卡，开始连战")
                for step in FIGHT_STEPS:
                    if self.exit_is_set():
                        return
                    self.log_info(f"  {step}")
                    if not self._poll_and_tap(step, 10):
                        self.log_info(f"    {step} 未找到，跳过")
                self.log_info("  托管中，等待战斗结束...")
                while not self.exit_is_set():
                    in_ex = self._in_exercise()
                    any_card = self._any_card()
                    self.log_info(f"  (等待) 演习奖励:{in_ex} 亮卡:{any_card}")
                    if in_ex and not any_card:
                        self.log_info("  战斗结束，回演习界面")
                        break
                    self.sleep(5)

            elif self._in_exercise() and not self._any_card():
                # 在演习界面但没有卡 → 换对手
                self.log_info("  无亮卡，尝试更换对手...")
                # 先清掉可能挡住的确定弹窗
                try:
                    ok_box = self.find_one("确定")
                    self.log_info("  先清掉确定弹窗")
                    self.click_box(ok_box)
                    self.sleep(0.5)
                except ValueError:
                    pass
                # 多试几次，屏幕可能还在加载
                found_change = False
                for attempt in range(3):
                    if self.exit_is_set():
                        return
                    if self._poll_and_tap("更换对手", 10):
                        found_change = True
                        break
                    self.log_info(f"  更换对手未找到 (尝试 {attempt+1}/3)，等待2秒...")
                    self.sleep(2)
                if found_change:
                    self.log_info("  已点更换对手")
                    # 更换对手后有确定弹窗
                    self.sleep(0.5)
                    try:
                        ok_box = self.find_one("确定")
                        self.log_info("  检测到确定，点击")
                        self.click_box(ok_box)
                        self.sleep(0.5)
                    except ValueError:
                        pass
                    self.log_info("  等待卡片刷新...")
                    # 等 15 秒看有没有卡出现
                    for _ in range(30):
                        if self.exit_is_set():
                            return
                        if self._any_card():
                            self.log_info("  卡片已刷新")
                            break
                        self.sleep(0.5)
                    else:
                        self.log_info("  卡片未刷新，次数已用完，回主页")
                        self._poll_and_tap("主页", 5)
                        break
                else:
                    self.log_info("  更换对手按钮多次未找到，回主页")
                    self._poll_and_tap("主页", 5)

            else:
                # 战斗中或加载中，等一下再检测
                self.sleep(5)

        self.log_info(f"出击-演习完成 (共 {round_num} 轮)")
