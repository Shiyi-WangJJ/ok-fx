"""无尽海域60关线路"""
from ok.task.task import BaseTask
from ok import og
from qfluentwidgets import FluentIcon

POPUPS = ["点击继续"]
GRID_SPACING = 370  # 关卡格子间距（像素）
EMPTY_CLICK = (934, 812)  # 战斗中空点击坐标


class WeeklyTask(BaseTask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "无尽海域60关"
        self.description = "在主页启动"
        self.group_name = "无尽海域60关"
        self.group_icon = FluentIcon.SYNC
        self.sleep_check_interval = 0.5
        self.default_config = {"_auto_start": False}
        self.enable_after_start = False
        self.hide_auto_buttons = True

    def sleep_check(self):
        for name in POPUPS:
            box = self.find_one(name)
            if box:
                self.log_info(f"弹窗: {box.name} -> 点击")
                self.click_box(box)
                return

    def _find_and_tap(self, name: str, use_gray_scale: bool = False) -> bool:
        box = self.find_one(name, use_gray_scale=use_gray_scale)
        if box is None:
            return False
        cx = box.x + box.width // 2
        cy = box.y + box.height // 2
        og.device_manager.shell(f"input tap {cx} {cy}")
        return True

    def _poll_and_tap(self, name: str, timeout: float = 10) -> bool:
        for _ in range(int(timeout / 0.3)):
            if self.exit_is_set():
                return False
            if self._find_and_tap(name):
                self.sleep(2)
                return True
            self.sleep(0.3)
        return False

    def _find_and_tap_current_level(self, timeout: float = 10) -> bool:
        """边点空位置边扫描锁定卡，找到后左偏一格点击要打的关卡"""
        self.log_info("扫描锁定关卡...")
        self.log_info("  持续点击空位置，等待锁定卡出现")
        start = __import__('time').time()
        while not self.exit_is_set():
            if __import__('time').time() - start > timeout:
                self.log_info("  扫描超时")
                return False

            og.device_manager.shell(f"input tap {EMPTY_CLICK[0]} {EMPTY_CLICK[1]}")

            try:
                boxes = self.find_feature(feature_name="32", limit=20,
                                          horizontal_variance=0.5)
            except ValueError:
                continue

            if not boxes:
                continue

            boxes.sort(key=lambda b: b.x)
            locked = boxes[0]

            locked_cx = locked.x + locked.width // 2
            locked_cy = locked.y + locked.height // 2
            target_x = locked_cx - GRID_SPACING
            target_y = locked_cy

            self.log_info(f"  找到锁定卡")
            self.log_info(f"    位置: ({locked_cx}, {locked_cy})")
            self.log_info(f"    偏移 {GRID_SPACING}px → 点击要打的关卡 ({target_x}, {target_y})")
            og.device_manager.shell(f"input tap {target_x} {target_y}")
            self.sleep(1)
            return True

        return False

    def _combat_loop(self):
        """战斗循环: 一直点空位置，直到锁定卡重新出现"""
        self.log_info("进入战斗循环")
        self.log_info(f"  空点击坐标: ({EMPTY_CLICK[0]}, {EMPTY_CLICK[1]})")
        self.log_info("  持续点击，每10次检查一次锁定卡...")
        tap_count = 0
        while not self.exit_is_set() and self.enabled:
            og.device_manager.shell(f"input tap {EMPTY_CLICK[0]} {EMPTY_CLICK[1]}")
            tap_count += 1

            # 每 5 次点击检查一次锁定卡（截图太频繁会拖慢点击节奏）
            if tap_count % 5 == 0:
                try:
                    self.find_one("32", horizontal_variance=0.5)
                    self.log_info(f"  锁定卡出现！(共点击 {tap_count} 次)")
                    self.log_info("  本关战斗结束")
                    return True
                except ValueError:
                    pass
                self.sleep(0.1)
        return False

    def _setup_fleet(self):
        """空阵容 → 空船 → 一键移除 → 一键移除确定 → 快速选择 → 弹药5×6 → 一键选择确定 → 起航2"""
        self.log_info("")
        self.log_info("══════════════════════════════════")
        self.log_info("  检测到空阵容，开始配置舰队")
        self.log_info("══════════════════════════════════")

        self.sleep(2)  # 等编队界面加载
        self.log_info(">> 空船 (固定坐标 1174, 436)")
        og.device_manager.shell("input tap 1174 436")
        self.sleep(2)

        self.log_info(">> 一键移除")
        if not self._poll_and_tap("一键移除", 10):
            self.log_info("  一键移除未找到")
            return False
        self.sleep(1)

        self.log_info(">> 一键移除确定")
        if not self._poll_and_tap("一键移除确定", 10):
            self.log_info("  一键移除确定未找到")
            return False
        self.sleep(1)

        self.log_info(">> 快速选择")
        if not self._poll_and_tap("快速选择", 10):
            self.log_info("  快速选择未找到")
            return False
        self.sleep(1)

        self.log_info(">> 选择弹药5 × 6")
        clicked = set()  # 记录已点过的位置，避免重复点同一个
        scroll_count = 0
        max_scroll = 10
        found_total = 0
        need_count = 6

        while found_total < need_count and scroll_count <= max_scroll:
            if self.exit_is_set():
                return False
            try:
                boxes = self.find_feature(
                    feature_name="弹药5", limit=20,
                    threshold=0.80,
                    horizontal_variance=1.0, vertical_variance=1.0,
                )
            except ValueError:
                boxes = []

            # 过滤已点过的（按坐标去重，容差 30px）
            new_boxes = []
            for b in boxes:
                key = (b.x // 30, b.y // 30)
                if key not in clicked:
                    new_boxes.append(b)

            self.log_info(f"  第 {scroll_count + 1} 轮: 找到 {len(boxes)} 个, 新增 {len(new_boxes)} 个")

            for box in new_boxes:
                if found_total >= need_count:
                    break
                cx = box.x + box.width // 2
                cy = box.y + box.height // 2
                og.device_manager.shell(f"input tap {cx} {cy}")
                key = (box.x // 30, box.y // 30)
                clicked.add(key)
                found_total += 1
                self.log_info(f"  弹药5 [{found_total}/{need_count}] @ ({cx}, {cy})")
                self.sleep(0.3)

            if found_total >= need_count:
                break

            # 往下滑一点再找
            if scroll_count < max_scroll:
                self.log_info(f"  不足 {need_count} 个，下滑...")
                self.swipe_relative(0.5, 0.7, 0.5, 0.4)
                self.sleep(1)
            scroll_count += 1

        self.log_info(f"  弹药5 已选: {found_total}/{need_count} 个")
        self.sleep(1)

        self.log_info(">> 一键选择确定")
        if not self._poll_and_tap("一键选择确定", 10):
            self.log_info("  一键选择确定未找到")
            return False
        self.sleep(1)

        self.log_info(">> 起航2")
        if not self._poll_and_tap("起航2", 10):
            self.log_info("  起航2未找到")
            return False

        self.log_info("  舰队配置完成")
        self.log_info("")
        return True

    def _run_one_level(self):
        """打一关: 选关 → 起航 → [编队] → 战斗"""
        self.log_info("")
        self.log_info("──────────────────────────────────")

        # 找锁定卡 → 点击要打的关卡
        if not self._find_and_tap_current_level(10):
            self.log_info("  未找到锁定关卡")
            return False

        # 起航：匹配+点击+双击，间隔1s
        self.log_info(">> 起航")
        # 第一次点击
        for _ in range(int(10 / 0.3)):
            if self.exit_is_set():
                return False
            if self._find_and_tap("起航"):
                break
            self.sleep(0.3)
        else:
            self.log_info("  起航未找到")
            return False
        self.log_info("  起航成功")
        # 双击，间隔1s
        self.sleep(1)
        box = self.find_one("起航")
        if box is None:
            self.log_info("  起航已消失，进入战斗")
        else:
            cx = box.x + box.width // 2
            cy = box.y + box.height // 2
            self.log_info(f"  双击起航 @ ({cx}, {cy})")
            og.device_manager.shell(f"input tap {cx} {cy}")
            self.sleep(2)
            # 还在 = 被卡住，走编队
            if self.find_one("起航") is None:
                self.log_info("  起航已消失，进入战斗")
            else:
                self.log_info("  起航仍在，走编队流程")
                og.device_manager.shell("input tap 257 895")
                self.log_info("  空阵容 (固定坐标 257, 895)")
                self.sleep(3)
                if not self._setup_fleet():
                    return False

        # 战斗
        return self._combat_loop()

    def run(self):
        self.log_info("")
        self.log_info("══════════════════════════════════")
        self.log_info("  无尽海域60关 - 开始")
        self.log_info("══════════════════════════════════")
        self.log_info("")
        self.log_info("配置参数:")
        self.log_info(f"  格子间距: {GRID_SPACING}px")
        self.log_info(f"  空点击坐标: ({EMPTY_CLICK[0]}, {EMPTY_CLICK[1]})")
        self.log_info("")

        # 确认在主页
        self.log_info("确认主页...")
        for _ in range(10):
            if self.exit_is_set():
                return
            try:
                self.find_one("商店")
                self.log_info("  商店可见，已在主页")
                break
            except ValueError:
                og.device_manager.shell("input tap 355 59")
                self.sleep(1)

        # 1. 活动
        self.log_info("")
        self.log_info(">> 活动")
        if not self._poll_and_tap("活动", 10):
            self.log_info("  活动未找到")
            return
        self.log_info("  已进入活动")

        # 2. 无尽海域入口 (双匹配)
        self.log_info(">> 等待无尽海域入口...")
        found = False
        for _ in range(int(10 / 0.2)):
            if self.exit_is_set():
                return
            for name in ["无尽海域1", "无尽海域2"]:
                if self._find_and_tap(name):
                    self.log_info(f"  匹配到: {name}")
                    self.sleep(1)
                    found = True
                    break
            if found:
                break
            self.sleep(0.2)
        if not found:
            self.log_info("  无尽海域入口未找到")
            return

        # 3. 无尽海域出击
        self.log_info(">> 无尽海域出击")
        if not self._poll_and_tap("无尽海域出击", 10):
            self.log_info("  无尽海域出击未找到")
            return
        self.log_info("  已进入选关界面")

        # 4. 循环打关
        self.log_info("")
        self.log_info("══════════════════════════════════")
        self.log_info("  开始循环打关")
        self.log_info("══════════════════════════════════")

        level_count = 0
        self.info["已完成"] = "0 关"
        while not self.exit_is_set() and self.enabled:
            if self._run_one_level():
                level_count += 1
                self.info["已完成"] = f"{level_count} 关"
                self.log_info(f"  ★ 第 {level_count} 关完成 ★")
            else:
                self.log_info("  本关未完成，继续扫描...")
                self.sleep(1)

        self.log_info(f"无尽海域结束，共完成 {level_count} 关")
