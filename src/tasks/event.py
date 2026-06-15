"""活动线路"""
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
        self.name = "6. 活动"
        self.description = "活动 -> 活动出击 -> 地狱EX -> 开始委托 -> 轮数设定 -> 活动MAX -> 活动确认 -> 活动开始委托 -> 主页"
        self.sleep_check_interval = 0.5

    def sleep_check(self):
        for name in POPUPS:
            box = self.find_one(name, use_gray_scale=True)
            if box:
                self.log_info(f"弹窗: {box.name} -> 点击")
                self.click_box(box)
                return

    # 地狱EX 有两个版本，任意一个出现都算
    EX_STEPS = {"地狱EX": ["地狱EX", "地狱EX2"]}

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
            # 记录最高置信度
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

    def run(self):
        for name in STEPS:
            if self.exit_is_set():
                return

            # 地狱EX之后先点委托完成，再点委托完成X
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
            # "活动" 和 "活动出击" 用固定坐标点，加间隔
            if name in TAP_COORDS:
                cx, cy = TAP_COORDS[name]
                og.device_manager.shell(f"input tap {cx} {cy}")
                self.log_info(f"  坐标点击 ({cx}, {cy})")
                self.sleep(3)  # 等页面加载
            elif not self._poll_and_tap(name, 10):
                self.log_info(f"  {name} 未找到，跳过")
            elif name in CONFIRM_AFTER:
                self.sleep(0.5)
                for _ in range(10):
                    if self._find_and_tap("确定"):
                        self.log_info("  已点击确定")
                        break
                    self.sleep(0.3)

        # 先等 5 秒再开始找主页
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
