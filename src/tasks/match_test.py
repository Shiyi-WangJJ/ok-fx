"""匹配测试 — 持续 5 秒，每 0.5 秒扫一轮，只看框不点击"""
from ok.task.task import BaseTask

FEATURES = [
    "退役", "退役一键选择", "退役选择确定", "退役确定",
    "确定", "活动开始委托", "委托完成",
]


class MatchTest(BaseTask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "匹配测试"
        self.description = "持续匹配 5 秒，每 0.5 秒一轮"
        self.default_config["启动"] = False
        self.visible = True

    def run(self):
        for round_num in range(10):  # 10 轮 × 0.5s = 5 秒
            self.log_info(f"{'='*40} 第 {round_num+1}/10 轮 {'='*40}")
            for name in FEATURES:
                if not self.feature_exists(name):
                    continue
                try:
                    boxes = self.find_feature(feature_name=name, limit=1, use_gray_scale=True)
                    if boxes:
                        b = boxes[0]
                        self.log_info(
                            f"  ✅ {name}: conf={b.confidence:.4f} @ ({b.x},{b.y}) {b.width}x{b.height}"
                        )
                    else:
                        self.log_info(f"  ❌ {name}: 未找到")
                except ValueError:
                    self.log_info(f"  ❌ {name}: 匹配失败")
            if round_num < 9:
                self.sleep(0.5)
