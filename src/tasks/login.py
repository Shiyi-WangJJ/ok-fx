"""登录线路 — ADB启动 -> 点击开始 -> 关闭公告 -> 登录补给X -> 等待商店"""
from ok.task.task import BaseTask
from ok import og

POPUPS = ["点击继续"]
GAME_PACKAGE = "com.nineyou.fuxiao"


class LoginTask(BaseTask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "1. 登录游戏"
        self.description = "ADB启动 -> 点击屏幕开始 -> 关闭公告 -> 登录补给X -> 等待商店"
        self.sleep_check_interval = 0.5

    def sleep_check(self):
        """sleep 期间被 executor 周期性调用，扫描弹窗。"""
        for name in POPUPS:
            box = self.find_one(name)
            if box:
                self.log_info(f"弹窗: {box.name} -> 点击")
                self.click_box(box)
                return

    def _find_one_safe(self, name: str):
        """安全查找 feature — 未定义时返回 None 不抛异常"""
        try:
            return self.find_one(name)
        except ValueError:
            return None

    def _should_continue(self) -> bool:
        """检查是否应该继续运行（未停止 + 未被禁用）"""
        return not self.exit_is_set() and self.enabled

    def _confirm_home(self) -> bool:
        """确认已进主页 — 商店或主页持续出现2秒才认定，防一闪而过"""
        for _ in range(10):
            if not self._find_one_safe("商店") and not self._find_one_safe("主页"):
                return False
            self.sleep(0.2)
        return True

    def run(self):
        # Step 1: ADB 直接启动游戏
        self.log_info(f"Step 1: ADB 启动游戏 ({GAME_PACKAGE})")
        try:
            og.device_manager.shell(
                f"monkey -p {GAME_PACKAGE} -c android.intent.category.LAUNCHER 1"
            )
            self.log_info("  游戏启动命令已发送")
        except Exception as e:
            self.log_info(f"  启动失败: {e}, 尝试 ensure_in_front")
            og.device_manager.adb_ensure_in_front()
        self.sleep(6)

        # Step 2: 等到启动16出现 → 点屏幕中心 10 秒（每秒一次）
        # 超时 20 秒，没等到也继续（可能跳过了启动画面）
        self.log_info("Step 2: 等待启动16 (超时120s)...")
        waited = 0
        while self._should_continue() and waited < 120:
            box = self._find_one_safe("启动16")
            if box is not None:
                break
            # 等待期间也可能弹"更新确定"
            ok_box = self._find_one_safe("更新确定")
            if ok_box:
                self.log_info("  等待期间检测到更新确定，点击")
                self.click_box(ok_box)
                self.sleep(0.5)
            # 更新完可能直接弹公告X，先关掉
            notice_box = self._find_one_safe("公告X")
            if notice_box:
                self.log_info("  等待期间检测到公告X，点击关闭")
                self.click_box(notice_box)
                self.sleep(0.5)
            # 商店/主页出现说明已经进主页了
            if self._confirm_home():
                self.log_info("  已进主页，跳过点击屏幕")
                return
            self.sleep(0.3)
            waited += 0.3
        else:
            if waited >= 120:
                self.log_info("  超时(120s)，未检测到启动16，仍然尝试点击屏幕")

        if self._should_continue():
            self.log_info("  点击出击位置 15 秒...")
            # 出击按钮中心 (~1842, 851)
            cx, cy = 1842, 851
            for i in range(15):
                if not self._should_continue():
                    break
                # 顺手关弹窗
                for popup in ["更新确定", "公告X", "登录补给X"]:
                    box = self._find_one_safe(popup)
                    if box:
                        self.log_info(f"  检测到{popup}，点击关闭")
                        self.click_box(box)
                        self.sleep(0.5)
                og.device_manager.shell(f"input tap {cx} {cy}")
                self.log_info(f"  [{i+1}/15]")
                # 商店/主页出现就提前结束
                if self._confirm_home():
                    self.log_info("  已进主页，停止点击")
                    return
                if i < 14:
                    self.sleep(1)
            self.log_info("  15 秒点击完成")

        # Step 3: 关公告X — 同时检测商店，商店出现就直接结束
        self.log_info("Step 3: 关闭公告X...")
        notice_clicks = 0
        gone_count = 0
        while self._should_continue():
            # 商店/主页出现就表示进主页了
            if self._confirm_home():
                self.log_info("  已进主页，跳过公告")
                return

            box = self._find_one_safe("公告X")
            if box is not None:
                gone_count = 0
                cx, cy = box.x + box.width // 2, box.y + box.height // 2
                og.device_manager.shell(f"input tap {cx} {cy}")
                notice_clicks += 1
                self.sleep(0.3)
            else:
                if notice_clicks > 0:
                    gone_count += 1
                    if gone_count >= 8:
                        self.log_info(f"  公告X 彻底消失 (共点击 {notice_clicks} 次)")
                        break
                self.sleep(1)
        else:
            self.log_info("  [已停止] 公告X")

        # Step 4: 登录补给X — 每日一次，有就关，商店出现直接结束
        self.log_info("Step 4: 登录补给X...")
        if self._should_continue():
            for _ in range(10):
                if not self._should_continue():
                    break
                if self._confirm_home():
                    self.log_info("  已进主页，跳过补给")
                    return
                box = self._find_one_safe("登录补给X")
                if box:
                    self.click_box(box)
                    self.sleep(0.5)
                else:
                    self.log_info("  登录补给X 未出现，跳过")
                    break
            else:
                self.log_info("  已尝试关闭登录补给X")

        # Step 5: 等待商店/主页出现 — 每秒点一次出击位置
        self.log_info("Step 5: 等待商店/主页...")
        while self._should_continue():
            if self._confirm_home():
                self.log_info("  已进主页，登录完成!")
                break
            # 点出击位置
            og.device_manager.shell(f"input tap 1842 851")
            self.sleep(1)
        else:
            self.log_info("  [已停止]")

        self.log_info("登录完成")
