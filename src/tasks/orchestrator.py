"""一条龙编排器 — 登录 → 领油 → 日常 → 演习 → 竞技 → 远征 → 倒油 → 任务 → 商店 → 领油"""
import os
import re
import time
import cv2
from datetime import datetime
from ok.task.task import BaseTask
from ok.task.exceptions import TaskDisabledException
from ok import og

GAME_PACKAGE = "com.nineyou.fuxiao"
POPUPS = ["点击继续"]

# 领油步骤
OIL_STEPS = ["快速领取", "炼油厂", "排班", "编辑", "进行排班", "一键领取", "主页"]
OIL_CONFIRM = {"编辑", "进行排班", "一键领取"}

# 日常卡片
DAILY_CARDS = ["武器运输", "通商护航", "综合演练", "军备科技", "战术训练", "战场探索"]

# 远征
HOUR12 = ["12小时", "12小时2"]

# 倒油-活动
EVENT_TAP_COORDS = {"活动": (1808, 703), "活动出击": (1676, 966)}
EVENT_STEPS = ["活动", "活动出击", "地狱EX", "开始委托", "轮数设定", "活动MAX", "活动确认", "活动开始委托"]
EVENT_DUAL = {"地狱EX": ["地狱EX", "地狱EX2"], "轮数设定": ["轮数设定", "轮数设定2"]}


class DailyOrchestrator(BaseTask):
    _first_init_done = False  # 模块级：区分真正启动 vs 热加载

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "0. 一条龙"
        self.description = "登录→领油→日常→演习→竞技→远征→倒油→任务→商店→领油"
        self.sleep_check_interval = 0.2
        self.default_config.update({"倒油线路": "活动", "竞技线路": "争锋", "单步执行": "全部", "贸易商店": False})
        self.config_type = {
            "倒油线路": {"options": ["活动", "20-5", "20-1", "20-10"]},
            "竞技线路": {"options": ["争锋", "普通"]},
            "单步执行": {"options": ["全部", "领油(1)", "出击-日常", "出击-演习", "出击-竞技", "远征", "倒油", "任务", "商店", "贸易商店", "领油(2)"]},
        }

    def on_create(self):
        # 只在真正启动时重置为"全部"，热加载时不重置
        if not DailyOrchestrator._first_init_done:
            DailyOrchestrator._first_init_done = True
            if self.config.get("单步执行", "全部") != "全部":
                dict.__setitem__(self.config, "单步执行", "全部")

    # ==================================================================
    # 通用工具
    # ==================================================================

    def sleep_check(self):
        for name in POPUPS:
            box = self.find_one(name)
            if box:
                self.log_info(f"弹窗: {box.name} -> 点击")
                self.click_box(box)
                return

    def _find_one_safe(self, name: str):
        try:
            return self.find_one(name)
        except ValueError:
            return None

    def _find_and_tap(self, name: str, threshold: float = None,
                      use_gray_scale: bool = False,
                      horizontal_variance: float = 0.0,
                      vertical_variance: float = 0.0) -> bool:
        try:
            kwargs = {}
            if threshold is not None:
                kwargs["threshold"] = threshold
            if use_gray_scale:
                kwargs["use_gray_scale"] = True
            if horizontal_variance:
                kwargs["horizontal_variance"] = horizontal_variance
            if vertical_variance:
                kwargs["vertical_variance"] = vertical_variance
            box = self.find_one(name, **kwargs) if kwargs else self.find_one(name)
        except ValueError:
            return False
        if box:
            conf = getattr(box, 'confidence', '?')
            cx = box.x + box.width // 2
            cy = box.y + box.height // 2
            self.log_info(f"  [{name}] conf={conf:.3f} @ ({cx},{cy})")
            og.device_manager.shell(f"input tap {cx} {cy}")
            return True
        return False

    def _find_any_and_tap(self, names: list, **kwargs) -> bool:
        """多模板匹配——任意一个命中就点"""
        for n in names:
            if self._find_and_tap(n, **kwargs):
                return True
        return False

    def _poll_and_tap(self, name, timeout: float = 10, **kwargs) -> bool:
        for _ in range(int(timeout / 0.3)):
            if self.exit_is_set():
                return False
            if isinstance(name, list):
                if self._find_any_and_tap(name, **kwargs):
                    self.sleep(1)
                    return True
            elif self._find_and_tap(name, **kwargs):
                self.sleep(1)
                return True
            self.sleep(0.3)
        return False

    def _should_continue(self) -> bool:
        return not self.exit_is_set() and self.enabled

    def _confirm_home(self) -> bool:
        """快速检查是否在主页。用 time.sleep 避免 sleep_check 干扰。"""
        for _ in range(15):
            if self._find_one_safe("商店") is not None:
                return True
            home = self._find_one_safe("主页")
            if home is not None:
                cx, cy = home.x + home.width // 2, home.y + home.height // 2
                og.device_manager.shell(f"input tap {cx} {cy}")
                time.sleep(0.8)
            time.sleep(0.3)
        return False

    def _click_while_present(self, name: str, timeout: float = 5, interval: float = 0.3) -> bool:
        """模板在就一直点，消失才停。用 time.sleep，不触发 sleep_check。"""
        deadline = time.time() + timeout
        clicked = False
        while time.time() < deadline:
            box = self._find_one_safe(name)
            if box:
                cx, cy = box.x + box.width // 2, box.y + box.height // 2
                og.device_manager.shell(f"input tap {cx} {cy}")
                clicked = True
                time.sleep(interval)
            elif clicked:
                self.log_info(f"  {name} 已消失 ({'点击过' if clicked else '未出现'})")
                return True
            else:
                time.sleep(interval)
        if not clicked:
            self.log_info(f"  {name} 未出现，跳过")
        return clicked

    def _go_home(self):
        """回到主页"""
        for _ in range(30):
            if not self._should_continue():
                return
            if self._find_one_safe("商店") is not None:
                self.log_info("  主页已出现")
                return
            if self._find_and_tap("主页"):
                self.log_info("  主页已出现")
                return
            og.device_manager.shell("input tap 355 59")
            self.sleep(1)
        self.log_info("  回主页超时")

    # ==================================================================
    # 登录
    # ==================================================================

    def ensure_main_screen(self):
        """幂等地确保在游戏主页"""
        # 预检：商店在 = 已在主页
        if self._find_one_safe("商店") is not None:
            self.log_info("已在主页，跳过登录")
            return

        # 预检：主页在 = 在游戏里，点一下回家
        home_btn = self._find_one_safe("主页")
        if home_btn is not None:
            self.log_info("检测到主页按钮，点击回主页...")
            self.click_box(home_btn)
            self.sleep(1)
            self.log_info("已回到主页，跳过登录")
            return

        self.log_info("开始登录流程...")

        # Step 1: 启动游戏
        self.log_info(f"Step 1: ADB 启动游戏 ({GAME_PACKAGE})")
        try:
            og.device_manager.shell(
                f"monkey -p {GAME_PACKAGE} -c android.intent.category.LAUNCHER 1"
            )
        except Exception as e:
            self.log_info(f"  启动失败: {e}")
            og.device_manager.adb_ensure_in_front()
        self.sleep(6)

        # Step 2: 等启动画面，看到了就点右下直到消失
        self.log_info("Step 2: 等待启动16 (超时120s)...")
        waited = 0
        splash_seen = False
        while self._should_continue() and waited < 120:
            for popup in ["更新确定", "公告X"]:
                b = self._find_one_safe(popup)
                if b:
                    self.click_box(b)
                    self.sleep(0.5)
            if self._find_one_safe("启动16") is not None:
                splash_seen = True
                og.device_manager.shell("input tap 1842 851")
                self.sleep(0.35)
            elif splash_seen:
                # 启动16出现了又消失 = 加载完了
                self.log_info("  启动16 已消失，进入游戏")
                break
            self.sleep(0.3)
            waited += 0.3

        if not self._should_continue():
            return

        # Step 3: 点击出击位置快速进主页，同时处理弹窗
        if self._should_continue():
            self.log_info("  点击出击位置 15 秒...")
            cx, cy = 1842, 851
            for i in range(15):
                if not self._should_continue():
                    break
                for popup in ["更新确定", "公告X", "登录补给X"]:
                    b = self._find_one_safe(popup)
                    if b:
                        self.log_info(f"  检测到{popup}，点击关闭")
                        self.click_box(b)
                        self.sleep(0.5)
                # 先检查到家没，避免在主页上误点出击跳到别的界面
                if self._confirm_home():
                    self.log_info("  已进主页，停止点击")
                    break
                og.device_manager.shell(f"input tap {cx} {cy}")
                self.log_info(f"  [{i+1}/15]")
                if i < 14:
                    self.sleep(1)
            self.log_info("  15 秒点击完成")

        # Step 4: 关公告X (click_while_present)
        self.log_info("Step 4: 清理公告X...")
        if self._should_continue():
            n_clicks = 0
            while self._should_continue() and n_clicks < 20:
                box = self._find_one_safe("公告X")
                if box:
                    self.click_box(box)
                    n_clicks += 1
                    self.sleep(0.3)
                elif n_clicks > 0:
                    # 之前点过，现在已经消失
                    self.log_info(f"  公告X 已消失 (点击 {n_clicks} 次)")
                    break
                else:
                    self.log_info("  公告X 未出现，跳过")
                    break

        # Step 5: 关登录补给X (click_while_present)
        self.log_info("Step 5: 清理登录补给X...")
        if self._should_continue():
            n_clicks = 0
            while self._should_continue() and n_clicks < 20:
                box = self._find_one_safe("登录补给X")
                if box:
                    self.click_box(box)
                    n_clicks += 1
                    self.sleep(0.3)
                elif n_clicks > 0:
                    self.log_info(f"  登录补给X 已消失 (点击 {n_clicks} 次)")
                    break
                else:
                    self.log_info("  登录补给X 未出现，跳过")
                    break

        # Step 6: 最终确认主页
        self.log_info("Step 6: 确认主页...")
        while self._should_continue():
            if self._confirm_home():
                self.log_info("  已进主页，登录完成!")
                break
            og.device_manager.shell("input tap 1842 851")
            self.sleep(1)

    # ==================================================================
    # 领油 (x2)
    # ==================================================================

    def do_oil(self):
        """领油 + 排班"""
        self.log_info("--- 开始领油 ---")
        for i, name in enumerate(OIL_STEPS):
            if self.exit_is_set():
                return
            self.log_info(f"  Step {i+1}: {name}")
            found = False
            for _ in range(20):
                if self.exit_is_set():
                    return
                if self._find_and_tap(name):
                    self.sleep(1)
                    found = True
                    break
                self.sleep(0.5)
            if found and name in OIL_CONFIRM:
                last_step = (name == OIL_STEPS[-2])  # 一键领取是最后一个需要确认的步骤
                home_reached = False
                for _ in range(10):
                    # 先处理确认弹窗
                    box = self._find_one_safe("确定") or self._find_one_safe("点击继续")
                    if box:
                        self.log_info(f"    已点击{box.name}")
                        self.click_box(box)
                        self.sleep(0.3)
                        continue
                    if last_step:
                        # 一键领取后尝试回主页 — 能回去说明流程完成了
                        self._find_and_tap("主页")
                        if self._find_one_safe("商店") is not None:
                            self.log_info("    已回主页")
                            home_reached = True
                            break
                    else:
                        # 非最后一步，弹窗消失即可继续
                        break
                    self.sleep(0.3)
                if home_reached:
                    break
            elif not found:
                self.log_info(f"    {name} 未找到，跳过")
        self.sleep(2)
        self._go_home()
        self.log_info("--- 领油完成 ---")

    # ==================================================================
    # 出击 → 日常 (6卡扫荡)
    # ==================================================================

    def do_daily(self):
        """出击 → 日常 → 逐个扫荡6张卡"""
        self.log_info("--- 出击-日常 ---")
        for step in ["出击", "日常"]:
            if self.exit_is_set():
                return
            self.log_info(f"  >> {step}")
            for _ in range(20):
                if self.exit_is_set():
                    return
                if self._find_and_tap(step):
                    self.sleep(1)
                    break
                self.sleep(0.3)
            else:
                self.log_info(f"    {step} 未找到，退出")
                return

        self.sleep(3)
        done = set()
        while self._should_continue():
            name, box = None, None
            for card in DAILY_CARDS:
                if card in done:
                    continue
                try:
                    box = self.find_one(card, vertical_variance=0.1)
                    name = card
                    break
                except ValueError:
                    pass
            if name is None:
                self.log_info("  所有卡片已处理")
                break

            if box is None:
                self.log_info(f"  !! box is None for {name}, 跳过")
                done.add(name)  # 标记已处理，不再重试
                continue
            self.log_info(f"  >> {name}")
            cx = box.x + box.width // 2
            cy = box.y + box.height // 2
            og.device_manager.shell(f"input tap {cx} {cy}")
            self.sleep(1)

            if self._find_and_tap("确定"):
                self.log_info("    首次点击已弹出确定")
            else:
                og.device_manager.shell(f"input tap {cx} {cy}")
                self.sleep(3)
                self._find_and_tap("确定")

            self.sleep(3)
            for _ in range(40):
                if self._any_card(done):
                    self.sleep(1.5)
                    break
                self.sleep(0.2)
            else:
                self.sleep(3)
            done.add(name)
            self.log_info(f"    {name} 完成 ({len(done)}/6)")

        self._go_home()
        self.log_info("--- 出击-日常完成 ---")

    def _any_card(self, done: set):
        for name in DAILY_CARDS:
            if name in done:
                continue
            try:
                self.find_one(name, vertical_variance=0.1)
                return True
            except ValueError:
                pass
        return False

    # ==================================================================
    # 出击 → 演习
    # ==================================================================

    def do_exercise(self):
        """出击→演习→连战→点更换对手→有确认=还能刷→没确认=次数用完退出"""
        self.log_info("--- 出击-演习 ---")
        for step in ["出击", "演习"]:
            if self.exit_is_set():
                return
            self.log_info(f"  >> {step}")
            if not self._poll_and_tap(step, 10):
                self.log_info(f"    {step} 未找到，退出")
                return

        round_num = 0
        while self._should_continue():
            round_num += 1
            self.log_info(f"  >> 第 {round_num} 轮")

            # 连战
            for step in ["连续挑战", "全选", "开始托管"]:
                if self.exit_is_set():
                    return
                self.log_info(f"    {step}")
                if not self._poll_and_tap(step, 10):
                    self.log_info(f"      {step} 未找到")

            # 等战斗结束——确定出现
            self.log_info("  等待战斗结束...")
            while self._should_continue():
                if self._find_one_safe("确定") is not None:
                    self.log_info("  战斗结束，点击确定")
                    self._find_and_tap("确定")
                    self.sleep(1)
                    break
                self.sleep(3)

            # 点更换对手，如果没弹确认框 = 次数用完了
            self.log_info("  尝试更换对手...")
            if not self._poll_and_tap("更换对手", 10):
                self.log_info("  更换对手未找到")
                break
            # 等确认弹窗，最多3秒
            confirmed = False
            for _ in range(10):
                if self.exit_is_set():
                    return
                if self._find_one_safe("确定") is not None:
                    self.log_info("  更换对手确认弹窗出现")
                    self._find_and_tap("确定")
                    self.sleep(0.5)
                    confirmed = True
                    break
                self.sleep(0.3)
            if not confirmed:
                self.log_info("  更换对手无确认弹窗，次数已用完，退出")
                break

            self.log_info(f"  第 {round_num} 轮完成")

        self._go_home()
        self.log_info(f"--- 出击-演习完成 ({round_num}轮) ---")

    # ==================================================================
    # 出击 → 竞技
    # ==================================================================

    def do_arena(self):
        """出击→竞技→[争锋/普通]→等20s→回主页"""
        mode = self.config.get("竞技线路", "争锋")
        self.log_info(f"--- 出击-竞技 ({mode}) ---")
        if mode == "普通":
            self.log_info("普通线路占位，跳过")
            return
        for name in ["出击", "竞技", "争锋竞技", "无畏舰队"]:
            if self.exit_is_set():
                return
            self.log_info(f"  >> {name}")
            if not self._poll_and_tap(name, 10):
                self.log_info(f"    {name} 未找到")
            elif name == "无畏舰队":
                self.sleep(0.5)
                for _ in range(10):
                    if self._find_and_tap("确定"):
                        self.log_info("    已点击确定")
                        break
                    self.sleep(0.3)

        self.log_info("  等待战斗结束 (20s)...")
        self.sleep(20)
        self._go_home()
        self.log_info("--- 出击-竞技完成 ---")

    # ==================================================================
    # 远征
    # ==================================================================

    def do_expedition(self):
        """出击→远征→领取→12小时→远征1~4出征→回主页"""
        self.log_info("--- 远征 ---")
        self._go_home()
        for step in ["出击", "远征"]:
            if self.exit_is_set():
                return
            self.log_info(f"  >> {step}")
            if not self._poll_and_tap(step, 10):
                self.log_info(f"    {step} 未找到，退出")
                return

        self.log_info("  >> 远征全部领取")
        self._poll_and_tap("远征全部领取", 10)
        self.sleep(5)

        self.log_info("  >> 12小时")
        self._poll_and_tap(HOUR12, 10)
        self.sleep(0.5)

        for exp_name in ["远征1", "远征2", "远征3"]:
            if self.exit_is_set():
                return
            self._dispatch_one(exp_name)

        self.log_info("  >> 拉列表露出远征4")
        self.swipe_relative(0.69, 0.72, 0.69, 0.35, duration=0.5)
        self.sleep(1)
        self._dispatch_one("远征4")

        self.sleep(3)
        self._go_home()
        self.log_info("--- 远征完成 ---")

    def _dispatch_one(self, exp_name: str):
        self.log_info(f"    >> {exp_name}")
        if not self._poll_and_tap(exp_name, 10):
            self.log_info(f"      {exp_name} 未找到，跳过")
            return
        self.sleep(0.5)
        self._poll_and_tap("出征", 10)

    # ==================================================================
    # 倒油 (活动 / 主线)
    # ==================================================================

    def do_event(self):
        """倒油——活动或主线"""
        mode = self.config.get("倒油线路", "活动")
        if mode in ("20-5", "20-1", "20-10"):
            self._run_event_main_story(mode)
        else:
            self._run_event_activity()

    def _run_event_activity(self):
        """活动倒油"""
        self.log_info("--- 倒油-活动 ---")
        # 确认主页
        for _ in range(10):
            if self.exit_is_set():
                return
            if self._find_one_safe("商店") is not None:
                break
            og.device_manager.shell("input tap 355 59")
            self.sleep(1)

        while self._should_continue():
            for name in EVENT_STEPS:
                if self.exit_is_set():
                    return

                if name == "开始委托":
                    if self._find_and_tap("委托完成", use_gray_scale=True):
                        self.sleep(0.5)
                        for _ in range(10):
                            if self._find_and_tap("委托完成X", use_gray_scale=True):
                                break
                            self.sleep(0.3)
                        self.sleep(1)

                self.log_info(f"  >> {name}")
                if name in EVENT_TAP_COORDS:
                    cx, cy = EVENT_TAP_COORDS[name]
                    og.device_manager.shell(f"input tap {cx} {cy}")
                    self.sleep(3)
                elif name in EVENT_DUAL:
                    if not self._poll_and_tap(EVENT_DUAL[name], 10, use_gray_scale=True):
                        self.log_info(f"    {name} 未找到")
                elif not self._poll_and_tap(name, 10, use_gray_scale=True):
                    self.log_info(f"    {name} 未找到")
                elif name == "活动开始委托":
                    self.sleep(0.5)
                    for _ in range(10):
                        if self._find_and_tap("确定", use_gray_scale=True):
                            break
                        self.sleep(0.3)
                    if self._handle_retire():
                        break  # 退役了 → 外层 while 重新跑
            else:
                break  # for 正常结束 → 退出 while

        self.sleep(5)
        self._go_home()
        self.log_info("--- 倒油-活动完成 ---")

    def _handle_retire(self) -> bool:
        """退役处理，返回 True 表示已处理退役需要重跑"""
        self.log_info("  检查退役...")
        try:
            boxes = self.find_feature(feature_name="退役", limit=1,
                                       use_gray_scale=True, threshold=0.9)
        except ValueError:
            return False
        if not boxes:
            return False

        b = boxes[0]
        self.log_info(f"  !! 退役匹配 conf={b.confidence:.4f}")
        os.makedirs("logs/screenshots", exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        cv2.imwrite(f"logs/screenshots/retire_{ts}.png", self.executor.frame)

        if not self._poll_and_tap("退役", 3):
            return False
        self.sleep(2)

        for i in range(5):
            if self.exit_is_set():
                return True
            self.log_info(f"  退役子步骤 第{i+1}/5轮")
            for name in ["退役一键选择", "退役选择确定", "退役确定"]:
                if self.exit_is_set():
                    return True
                if not self._poll_and_tap(name, 5):
                    self.log_info(f"    {name} 未找到")
                if name == "退役选择确定":
                    self.sleep(2)
                self.sleep(3 if name == "退役确定" else 1)

        self.log_info("退役处理完毕，重新跑倒油...")
        self.log_info("  回主页...")
        for _ in range(30):
            if self.exit_is_set():
                return True
            self._find_and_tap("主页")
            self.sleep(0.5)
            if self._find_one_safe("主页") is None:
                self.log_info("  已回到主页")
                break
        else:
            self.log_info("  回主页超时，继续")
        return True

    def _run_event_main_story(self, level: str):
        """主线倒油 (20-5)"""
        self.log_info(f"--- 倒油-主线 {level} ---")
        if level == "20-1":
            self.log_info("20-1 占位，跳过")
            return

        while self._should_continue():
            # 确认主页
            for _ in range(10):
                if self.exit_is_set():
                    return
                if self._find_one_safe("商店") is not None:
                    break
                og.device_manager.shell("input tap 355 59")
                self.sleep(1)

            for i, name in enumerate(["出击", "主线", level, "托管", "主线开始托管"]):
                if self.exit_is_set():
                    return
                self.log_info(f"  >> Step {i+1}: {name}")
                if name == level:
                    # 20-10 关卡靠右，不滑看不到
                    if level == "20-10":
                        self.log_info("    20-10: 先右滑露出关卡")
                        self.swipe_relative(0.7, 0.55, 0.25, 0.55, duration=0.6)
                        self.sleep(1)
                    found = self._poll_and_tap(name, 10, threshold=0.85,
                                               horizontal_variance=1.0, vertical_variance=1.0)
                else:
                    found = self._poll_and_tap(name, 10)
                if not found:
                    self.log_info(f"    {name} 未找到")

            self.sleep(0.5)
            for _ in range(10):
                if self._find_and_tap("确定"):
                    break
                self.sleep(0.3)

            self.log_info("  托管循环...")
            self.sleep(3)
            last_tap = 0
            retired = False
            while self._should_continue():
                # 离开/主页 → 结束
                if self._find_and_tap("离开") or self._find_and_tap("主页"):
                    self.log_info("  战斗结束")
                    self.sleep(1)
                    break

                # 退役检测
                try:
                    boxes = self.find_feature(feature_name="退役", limit=1,
                                               use_gray_scale=True, threshold=0.9)
                    if boxes:
                        b = boxes[0]
                        self.log_info(f"  !! 退役 conf={b.confidence:.4f}")
                        os.makedirs("logs/screenshots", exist_ok=True)
                        cv2.imwrite(f"logs/screenshots/retire_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png", self.executor.frame)
                        if self._handle_retire():
                            retired = True
                            break
                except ValueError:
                    pass

                for btn, fullscreen in [("主线托管确定", False), ("主线取消", True), ("主线X", False)]:
                    if fullscreen:
                        self._find_and_tap(btn, horizontal_variance=1.0, vertical_variance=1.0)
                    else:
                        self._find_and_tap(btn)

                now = time.time()
                if now - last_tap > 30:
                    og.device_manager.shell("input tap 355 59")
                    last_tap = now
                self.sleep(2)

            if retired:
                continue
            self._go_home()
            break

        self.log_info(f"--- 倒油-主线 {level} 完成 ---")

    # ==================================================================
    # 任务 → 一键领取
    # ==================================================================

    def do_mission(self):
        """任务 → 任务一键领取 → 连点15秒 → 回主页"""
        self.log_info("--- 任务 ---")
        for name in ["任务", "任务一键领取"]:
            if self.exit_is_set():
                return
            self.log_info(f"  >> {name}")
            if not self._poll_and_tap(name, 10):
                self.log_info(f"    {name} 未找到，退出")
                return

        try:
            box = self.find_one("任务一键领取")
            cx, cy = box.x + box.width // 2, box.y + box.height // 2
        except ValueError:
            self.log_info("  任务一键领取 未找到，退出")
            return

        self.log_info(f"  连点 15 秒 @ ({cx},{cy})...")
        for i in range(15):
            if self.exit_is_set():
                return
            og.device_manager.shell(f"input tap {cx} {cy}")
            self.log_info(f"  [{i+1}/15]")
            if i < 14:
                self.sleep(1)

        self._go_home()
        self.log_info("--- 任务完成 ---")

    # ==================================================================
    # 商店 → 每日礼包
    # ==================================================================

    def do_shop(self):
        """商店 → 每日礼包 → 每日启航包 → 免费购买 → 回主页"""
        self.log_info("--- 商店-每日礼包 ---")

        self.log_info("  >> 商店")
        if not self._poll_and_tap("商店", 15):
            self.log_info("    商店未找到，退出")
            return
        self.sleep(1.5)

        self.log_info("  >> 每日礼包")
        if not self._poll_and_tap("每日礼包", 10):
            self.log_info("    每日礼包未找到，退出")
            return
        self.sleep(1.5)

        self.log_info("  >> 每日启航包")
        found = False
        for _ in range(15):
            if self.exit_is_set():
                return
            box = self._find_one_safe("每日启航包")
            if box:
                self.click_box(box)
                self.sleep(1)
                found = True
                break
            self.sleep(0.3)

        if not found:
            self.log_info("    每日启航包 未检测到，跳过")
            self._go_home()
            return

        self.log_info("  >> 免费购买")
        if self._poll_and_tap("免费购买", 10):
            self.sleep(1)
            self.log_info("    免费购买 完成")

        self._go_home()
        self.log_info("--- 商店-每日礼包完成 ---")

    # ==================================================================
    # 贸易商店 → 每日购买
    # ==================================================================

    def do_trade_shop(self):
        """贸易商店 → 每日免费兑换补给"""
        self.log_info("--- 贸易商店 ---")

        # 1. 商店
        self.log_info("  >> 商店")
        if not self._poll_and_tap("商店", 15):
            self.log_info("    商店未找到，退出")
            return
        self.sleep(1.5)

        # 2. 贸易商店（双匹配）
        self.log_info("  >> 贸易商店")
        if not self._poll_and_tap(["贸易商店", "贸易商店2"], 10):
            self.log_info("    贸易商店未找到，退出")
            self._go_home()
            return
        self.sleep(1.5)

        # 3. 补给兑换（双匹配）
        self.log_info("  >> 补给兑换")
        if not self._poll_and_tap(["补给兑换", "补给兑换2"], 10):
            self.log_info("    补给兑换未找到，退出")
            self._go_home()
            return
        self.sleep(1.5)

        # 3.5 识别免费刷新次数，决定循环轮数
        self.log_info("  >> 识别刷新次数")
        free_count = 0
        try:
            for _ in range(3):
                boxes = self.ocr(box="刷新区域")
                if boxes:
                    self.log_info(f"    OCR结果: {[b.name for b in boxes]}")
                    for b in boxes:
                        m = re.search(r'(\d+)\s*/\s*(\d+)', b.name)
                        if m:
                            free_count = int(m.group(1))
                            self.log_info(f"    免费刷新: {m.group(1)}/{m.group(2)}，共 {free_count} 轮")
                            break
                    break
                self.sleep(0.5)
        except Exception as e:
            self.log_info(f"    OCR失败: {e}")

        if free_count <= 0:
            self.log_info("    无免费刷新次数，退出")
            self._go_home()
            self.log_info("--- 贸易商店完成 ---")
            return

        # 4. 首轮（已有道具）+ free_count 轮刷新
        def _do_exchange_round(round_label="", need_multi_select=True):
            """选道具 → 购买。首轮需要点多选，刷新后不需要"""
            self.log_info(f"  == {round_label} ==")
            if need_multi_select:
                self.log_info("  >> 多选")
                if not self._poll_and_tap("多选", 8):
                    self.log_info("    多选未找到")
                    return False
                self.sleep(1)

            total_clicked = 0
            for rn in [1, 2]:
                if rn == 2:
                    self.log_info("  >> 下拉")
                    self.swipe_relative(0.5, 0.7, 0.5, 0.35)
                    self.sleep(1)
                self.log_info(f"  >> 第{rn}轮检索 可兑换1次")
                boxes = self.find_feature("可兑换1次", horizontal_variance=1, vertical_variance=1, limit=0,
                                          use_gray_scale=True)
                self.log_info(f"    找到 {len(boxes)} 个")
                if rn == 2 and boxes:
                    mid_y = sum(b.y for b in boxes) / len(boxes)
                    boxes = [b for b in boxes if b.y > mid_y]
                    self.log_info(f"    过滤后 {len(boxes)} 个(仅下半屏)")
                for box in boxes:
                    if self.exit_is_set():
                        return False
                    self.click_box(box)
                    self.sleep(0.5)
                    total_clicked += 1

            if total_clicked > 0:
                self.log_info("  >> 贸易商店购买")
                if self._poll_and_tap("贸易商店购买", 3):
                    self.sleep(1)
                    self.log_info("  >> 贸易购买确认")
                    if self._poll_and_tap("贸易购买确认", 3):
                        self.sleep(5)
                    else:
                        self.log_info("    贸易购买确认未找到")
                        self.sleep(5)
                    return True
                elif self._find_one_safe("刷新") is not None:
                    self.log_info("    购买未出现，刷新仍在(未选上道具)")
                else:
                    self.log_info("    贸易商店购买未找到")
            else:
                self.log_info("    无可兑换项")
            return False

        # 首轮：刚进页面，道具已存在
        _do_exchange_round("首轮")

        # 后续：点刷新 → 再兑换
        for i in range(free_count):
            if self.exit_is_set():
                return
            # 等 UI 过渡完成（sleep(5) 可能被 sleep_check→click_box 的嵌套 sleep 截断，
            # "点击继续"关闭后游戏需要 ~2s 回到商店列表，否则"刷新确定"弹不出）
            self.sleep(2)
            self.log_info(f"  >> 刷新 ({i + 1}/{free_count})")
            if not self._poll_and_tap("刷新", 8):
                self.log_info("    刷新未找到，退出循环")
                break
            self.sleep(1)
            # 刷新确认
            self.log_info("  >> 刷新确定")
            if self._poll_and_tap("刷新确定", 5):
                self.sleep(1)
            else:
                self.log_info("    刷新确定未找到")
            _do_exchange_round(f"刷新轮 {i + 1}/{free_count}", need_multi_select=False)

        self._go_home()
        self.log_info("--- 贸易商店完成 ---")

    # ==================================================================
    # 主流程
    # ==================================================================

    def run(self):
        import time
        self._run_start = time.time()
        self._run_end = 0
        # 通知 UI 刷新
        from ok.gui.Communicate import communicate
        communicate.task.emit(self)

        self.log_info("=" * 50)
        self.log_info("一条龙启动")
        self.log_info("=" * 50)

        # 登录
        self.ensure_main_screen()

        # 任务列表（每个步骤内 try/except，失败不中断后续）
        steps = [
            ("领油(1)", self.do_oil),
            ("出击-日常", self.do_daily),
            ("出击-演习", self.do_exercise),
            ("出击-竞技", self.do_arena),
            ("远征", self.do_expedition),
            ("倒油", self.do_event),
            ("任务", self.do_mission),
            ("商店", self.do_shop),
            ("领油(2)", self.do_oil),
        ]
        # 贸易商店：开关打开时追加到步骤列表
        if self.config.get("贸易商店", False):
            steps.append(("贸易商店", self.do_trade_shop))

        for label, fn in steps:
            if self.exit_is_set():
                break
            # 单步模式：只跑选中的步骤
            single = self.config.get("单步执行", "全部")
            if single != "全部" and label != single:
                continue
            self.log_info(f"\n{'─' * 30}\n  {label}\n{'─' * 30}")
            try:
                fn()
            except TaskDisabledException:
                self.log_info(f"  !! {label} 用户停止")
                break
            except Exception as e:
                self.log_info(f"  !! {label} 异常: {e}")
                # 尝试回主页继续下一个
                try:
                    self._go_home()
                except Exception:
                    pass

        import time
        self._run_end = time.time()
        from ok.gui.Communicate import communicate
        communicate.task.emit(self)

        self.log_info("=" * 50)
        self.log_info("一条龙完成")
        self.log_info("=" * 50)
