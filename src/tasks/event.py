"""倒油线路（活动 / 主线 二选一）"""
import os
import cv2
from datetime import datetime
from ok.task.task import BaseTask
from ok import og

POPUPS = ["点击继续"]
# "活动" 和 "活动出击" 用固定坐标，不依赖模板匹配（活动每期随机）
TAP_COORDS = {
    "活动": (1808, 703),
    "活动出击": (1676, 966),
}
STEPS = [
    "活动", "活动出击", "地狱EX", "开始委托",
    "轮数设定", "活动MAX", "活动确认", "活动开始委托",
]
CONFIRM_AFTER = {"活动开始委托"}


class EventTask(BaseTask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "6. 倒油"
        self.description = "倒油 -> [活动 / 主线]"
        self.sleep_check_interval = 0.5
        self.default_config = {"线路": "活动"}
        self.config_type = {
            "线路": {"options": ["活动", "主线"]}
        }

    def sleep_check(self):
        for name in POPUPS:
            box = self.find_one(name, use_gray_scale=True)
            if box:
                self.log_info(f"弹窗: {box.name} -> 点击")
                self.click_box(box)
                return

    # 地狱EX 有两个版本，任意一个出现都算
    EX_STEPS = {"地狱EX": ["地狱EX", "地狱EX2"], "轮数设定": ["轮数设定", "轮数设定2"]}

    def _find_and_tap(self, name: str) -> bool:
        names = self.EX_STEPS.get(name, [name])
        for n in names:
            try:
                box = self.find_one(n, use_gray_scale=True)
            except ValueError:
                continue
            if box:
                cx = box.x + box.width // 2
                cy = box.y + box.height // 2
                og.device_manager.shell(f"input tap {cx} {cy}")
                return True
        return False

    def _poll_and_tap(self, name: str, timeout: float = 10) -> bool:
        best_conf = 0
        for _ in range(int(timeout / 0.2)):
            if self.exit_is_set():
                return False
            if self._find_and_tap(name):
                self.sleep(1)
                return True
            try:
                boxes = self.find_feature(feature_name=name, limit=1, use_gray_scale=True)
                if boxes and boxes[0].confidence > best_conf:
                    best_conf = boxes[0].confidence
            except ValueError:
                pass
            self.sleep(0.2)
        if best_conf > 0:
            self.log_info(f"  {name} 最高置信度: {best_conf:.3f}")
        return False

    # 退役后的子步骤序列
    RETIRE_SUB_SEQUENCE = ["退役一键选择", "退役选择确定", "退役确定"]
    RETIRE_REPEAT = 5

    def _handle_retire(self) -> bool:
        """处理退役新线路：点退役 → 5轮子步骤 → 回到主页。返回 True 表示处理成功"""
        self.log_info("退役出现，开始退役新线路...")
        if not self._poll_and_tap("退役", 3):
            self.log_info("退役点击失败，跳过退役处理")
            return False
        self.sleep(2)

        for i in range(self.RETIRE_REPEAT):
            if self.exit_is_set():
                return
            self.log_info(f"  退役子步骤 第 {i+1}/{self.RETIRE_REPEAT} 轮")
            for name in self.RETIRE_SUB_SEQUENCE:
                if self.exit_is_set():
                    return
                self.log_info(f"    >> {name}")
                if not self._poll_and_tap(name, 5):
                    self.log_info(f"    {name} 未找到，跳过")
                if name == "退役选择确定":
                    self.sleep(2)  # 退役选择确定后界面切换慢，多等一会
                self.sleep(3 if name == "退役确定" else 1)

        self.log_info("退役线路结束，等待主页...")
        while not self.exit_is_set() and self.enabled:
            if self._find_and_tap("主页"):
                self.log_info("主页已出现，重新跑倒油流程")
                break
            og.device_manager.shell("input tap 355 59")
            self.sleep(1)

    def run(self):
        mode = self.config.get("线路", "活动")
        if mode == "主线":
            self._run_main_story()
        else:
            self._run_event()

    def _run_event(self):
        """倒油主流程，退役后回到主页再重新跑，直到完成"""
        # 确认在主页：检查"商店"是否存在
        self.log_info("确认主页...")
        for _ in range(10):
            if self.exit_is_set():
                return
            try:
                self.find_one("商店", use_gray_scale=True)
                self.log_info("商店可见，已在主页")
                break
            except ValueError:
                og.device_manager.shell("input tap 355 59")
                self.sleep(1)

        while not self.exit_is_set() and self.enabled:
            for name in STEPS:
                if self.exit_is_set():
                    return

                if name == "开始委托":
                    self.log_info("  检查委托完成...")
                    if self._find_and_tap("委托完成"):
                        self.sleep(0.5)
                        for _ in range(10):
                            if self._find_and_tap("委托完成X"):
                                self.log_info("  已关闭委托完成X")
                                break
                            self.sleep(0.3)
                        self.sleep(1)

                self.log_info(f">> {name}")
                if name in TAP_COORDS:
                    cx, cy = TAP_COORDS[name]
                    og.device_manager.shell(f"input tap {cx} {cy}")
                    self.log_info(f"  坐标点击 ({cx}, {cy})")
                    self.sleep(3)
                elif not self._poll_and_tap(name, 10):
                    self.log_info(f"  {name} 未找到，跳过")
                elif name == "活动开始委托":
                    # 活动开始委托完成后检测退役
                    self.sleep(0.5)
                    for _ in range(10):
                        if self._find_and_tap("确定"):
                            self.log_info("  已点击确定")
                            break
                        self.sleep(0.3)
                    self.log_info("  检查退役...")
                    try:
                        boxes = self.find_feature(feature_name="退役", limit=1, use_gray_scale=True, threshold=0.9)
                        if boxes:
                            b = boxes[0]
                            self.log_info(f"  ⚠ 退役匹配! conf={b.confidence:.4f} @ ({b.x},{b.y}) {b.width}x{b.height}")
                            # 保存截图
                            os.makedirs("logs/screenshots", exist_ok=True)
                            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                            path = f"logs/screenshots/retire_{ts}_conf{b.confidence:.2f}.png"
                            cv2.imwrite(path, self.executor.frame)
                            self.log_info(f"  截图已保存: {path}")
                            if self._handle_retire():
                                break  # 退役处理完回到主页，break → while 重新跑
                    except ValueError:
                        pass
            else:
                # for 循环正常结束（没遇到退役），跳出 while
                break
            # 被 break 了（遇到退役），while 会继续下一轮
            self.log_info("退役处理完毕，重新开始倒油流程...")

        self.log_info("等待 5s...")
        self.sleep(5)

        self.log_info("等待主页...")
        while not self.exit_is_set() and self.enabled:
            if self._find_and_tap("主页"):
                self.log_info("主页已出现，完成")
                break
            og.device_manager.shell("input tap 355 59")
            self.sleep(1)

        self.log_info("活动完成")

    def _run_main_story(self):
        self.log_info("主线线路（占位，待补充）")
        self.sleep(2)
