"""匹配测试 — 只看框不点击"""
from ok.task.task import BaseTask

FEATURES = ["亮1", "亮2", "亮3", "亮4", "亮5", "演习奖励"]


class MatchTest(BaseTask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "匹配测试"
        self.description = "只匹配不点击"
        self.default_config["启动"] = False
        self.visible = True

    def run(self):
        self.log_info("=" * 40)
        for name in FEATURES:
            if not self.feature_exists(name):
                self.log_info(f"  {name}: 特征不存在")
                continue

            boxes = self.find_feature(feature_name=name, limit=1)
            if boxes:
                b = boxes[0]
                self.log_info(f"  {name}: conf={b.confidence:.3f} @ ({b.x},{b.y}) {b.width}x{b.height}")
            else:
                self.log_info(f"  {name}: 未找到")
        self.log_info("=" * 40)
