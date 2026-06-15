"""
login_task.py — 游戏登录自动化步骤编排脚本

从 main.py 引入 OKFramework，按声明式步骤列表依次执行：
  find_and_click — 截图 → 模板匹配 → 点击匹配位置中心
  wait          — 纯等待（用于游戏加载）
  swipe         — 滑动操作

用法：
  python login_task.py          # 执行 STEPS 中定义的全部步骤
  python login_task.py --step 1 # 只执行第1步（1-based）

新增步骤只需往 STEPS 列表追加一个 dict，无需改任何代码。
"""

import os
import sys
import time
import logging
import threading
from typing import List, Dict, Optional, Tuple, Any

# 从 main.py 引入框架层能力
from main import (
    OKFramework,
    get_ok,
    DEFAULT_ADB_HOST,
    DEFAULT_ADB_PORT,
)

# ---------------------------------------------------------------------------
# 日志
# ---------------------------------------------------------------------------
logger = logging.getLogger("login_task")
# 如果作为独立脚本运行，确保 level 生效
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger("login_task")

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
# 模板图片存放目录（相对于本文件所在项目根目录）
IMG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "img")

# 默认值
DEFAULT_THRESHOLD = 0.70
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_INTERVAL = 1.0  # 秒
DEFAULT_WAIT_AFTER = 2.0       # 秒
DEFAULT_TIMEOUT = 30.0          # 秒
DEFAULT_ON_FAIL = "abort"

# 游戏包名 — adb shell monkey 直接启动，无需截图找桌面图标
# 获取方式: adb shell pm list packages -3 | grep 关键词
GAME_PACKAGE = "com.nineyou.fuxiao"

# =====================================================================
# 步骤定义（声明式 — 新增步骤只需追加 dict 到此列表）
# =====================================================================

ROUTES: List[Dict[str, Any]] = [
    # ================================================================
    # Route 1: 登录流程
    # ================================================================
    {
        "name": "login",
        "label": "登录流程",
        "enabled": True,
        "img_dir": "img",
        "steps": [
            {
                "name": "启动游戏(ADB)",
                "action": "shell",
                "command": f"monkey -p {GAME_PACKAGE} -c android.intent.category.LAUNCHER 1",
                "wait_after": 6.0, "timeout": 15.0, "on_fail": "abort",
            },
            {
                "name": "点击屏幕中心进入游戏",
                "template": "tap_to_start.png",
                "action": "find_and_click",
                "click_target": "screen_center",
                "click_while_present": True, "click_interval": 0.35,
                "max_clicks": 500, "threshold": 0.70, "max_retries": 10,
                "retry_interval": 2.0, "wait_after": 2.0,
                "timeout": 60.0, "on_fail": "abort",
            },
            {
                "name": "关闭公告弹窗",
                "template": "close_notice.png",
                "action": "find_and_click",
                "click_target": "match",
                "click_while_present": True, "click_interval": 0.4,
                "max_clicks": 20, "threshold": 0.70, "max_retries": 8,
                "retry_interval": 2.0, "wait_after": 1.0,
                "timeout": 45.0, "on_fail": "abort",
            },
            {
                "name": "领取每日奖励（如有）",
                "template": ["daily_dark_x.png", "daily_light_x.png"],
                "action": "find_and_click",
                "click_target": "match",
                "click_while_present": True, "click_interval": 0.5,
                "max_clicks": 5, "threshold": 0.70, "max_retries": 6,
                "retry_interval": 2.0, "wait_after": 2.0,
                "timeout": 45.0, "on_fail": "skip",
                "extra_clicks": 3, "extra_clicks_target": "screen_center",
                "extra_clicks_interval": 0.3,
            },
            {
                "name": "找商店或回主页",
                "template": "shop.png",
                "fallback_template": "home.png",
                "action": "find_and_click",
                "click_target": "match", "threshold": 0.70,
                "max_retries": 8, "retry_interval": 2.0,
                "wait_after": 2.0, "timeout": 50.0, "on_fail": "abort",
            },
        ],
    },
    # ================================================================
    # Route 2: 领油（日常）
    # ================================================================
    {
        "name": "oil",
        "label": "领油",
        "enabled": True,
        "img_dir": "img/领油",
        "steps": [
            {
                "name": "快速领取",
                "template": "quick_claim.png",
                "action": "find_and_click",
                "click_target": "match", "threshold": 0.70,
                "max_retries": 5, "retry_interval": 1.5,
                "wait_after": 2.0, "timeout": 30.0, "on_fail": "abort",
            },
            # Step 2: 点击炼油厂
            {
                "name": "点击炼油厂",
                "template": "refinery.png",
                "action": "find_and_click",
                "click_target": "match", "threshold": 0.70,
                "max_retries": 5, "retry_interval": 1.5,
                "wait_after": 2.0, "timeout": 30.0, "on_fail": "abort",
            },
            # Step 3: 点击排班 → 触发确定（看门狗处理）
            {
                "name": "点击排班",
                "template": "schedule.png",
                "action": "find_and_click",
                "click_target": "match", "threshold": 0.70,
                "max_retries": 5, "retry_interval": 1.5,
                "wait_after": 3.0, "timeout": 30.0, "on_fail": "abort",
            },
            # Step 4: 点击编辑 → 触发确定（看门狗处理）
            {
                "name": "点击编辑",
                "template": "edit.png",
                "action": "find_and_click",
                "click_target": "match", "threshold": 0.70,
                "max_retries": 5, "retry_interval": 1.5,
                "wait_after": 3.0, "timeout": 30.0, "on_fail": "abort",
            },
            # Step 5: 点击进行排班 → 触发确定（看门狗处理）
            {
                "name": "点击进行排班",
                "template": "do_schedule.png",
                "action": "find_and_click",
                "click_target": "match", "threshold": 0.70,
                "max_retries": 5, "retry_interval": 1.5,
                "wait_after": 3.0, "timeout": 30.0, "on_fail": "abort",
            },
            # Step 6: 点击一键领取
            {
                "name": "点击一键领取",
                "template": "claim_all_new.png",
                "action": "find_and_click",
                "click_target": "match", "threshold": 0.70,
                "max_retries": 5, "retry_interval": 1.5,
                "wait_after": 4.0, "timeout": 30.0, "on_fail": "abort",
            },
            # Step 7: 回主页 — 图片在就一直点，消失才算真正回到主页
            {
                "name": "回主页",
                "template": "home.png",
                "action": "find_and_click",
                "click_target": "match", "threshold": 0.75,
                "click_while_present": True,     # 图片消失才停
                "click_interval": 2.0,
                "max_clicks": 10,
                "max_retries": 10, "retry_interval": 2.0,
                "wait_after": 2.0, "timeout": 60.0,
                "on_fail": "skip",
            },
        ],
    },
    # ================================================================
    # Route 3: 出击-日常线
    # ================================================================
    {
        "name": "sortie",
        "label": "出击-日常",
        "enabled": True,
        "img_dir": "img/出击",
        "steps": [
            # 出击 → 日常
            {
                "name": "点击出击",
                "template": "sortie.png",
                "action": "find_and_click",
                "click_target": "match", "threshold": 0.70,
                "max_retries": 5, "retry_interval": 1.5,
                "wait_after": 2.0, "timeout": 30.0, "on_fail": "abort",
            },
            {
                "name": "点击日常",
                "template": "daily_tab.png",
                "action": "find_and_click",
                "click_target": "match", "threshold": 0.70,
                "max_retries": 5, "retry_interval": 1.5,
                "wait_after": 2.0, "timeout": 30.0, "on_fail": "abort",
            },
            # 通商护航 → 快速扫荡
            {
                "name": "通商护航",
                "template": "trade_escort.png",
                "action": "find_and_click",
                "click_target": "match", "threshold": 0.70,
                "max_retries": 5, "retry_interval": 1.5,
                "wait_after": 6.0, "timeout": 30.0, "on_fail": "abort",
            },
            {
                "name": "快速扫荡-通商",
                "template": "quick_sweep.png",
                "action": "find_and_click",
                "click_target": "match", "threshold": 0.70,
                "max_retries": 5, "retry_interval": 1.5,
                "wait_after": 6.0, "timeout": 30.0, "on_fail": "abort",
            },
            # 战术训练 → 快速扫荡
            {
                "name": "战术训练",
                "template": "tactical_training.png",
                "action": "find_and_click",
                "click_target": "match", "threshold": 0.70,
                "max_retries": 5, "retry_interval": 1.5,
                "wait_after": 6.0, "timeout": 30.0, "on_fail": "abort",
            },
            {
                "name": "快速扫荡-战术",
                "template": "quick_sweep.png",
                "action": "find_and_click",
                "click_target": "match", "threshold": 0.70,
                "max_retries": 5, "retry_interval": 1.5,
                "wait_after": 6.0, "timeout": 30.0, "on_fail": "abort",
            },
            # 军备科技 → 快速扫荡
            {
                "name": "军备科技",
                "template": "armament_tech.png",
                "action": "find_and_click",
                "click_target": "match", "threshold": 0.70,
                "max_retries": 5, "retry_interval": 1.5,
                "wait_after": 6.0, "timeout": 30.0, "on_fail": "abort",
            },
            {
                "name": "快速扫荡-军备",
                "template": "quick_sweep.png",
                "action": "find_and_click",
                "click_target": "match", "threshold": 0.70,
                "max_retries": 5, "retry_interval": 1.5,
                "wait_after": 6.0, "timeout": 30.0, "on_fail": "abort",
            },
            # 前3个地点完成后 → 左滑 → 战场探索 → 快速扫荡
            {
                "name": "左滑找战场探索",
                "action": "swipe",
                "swipe_direction": "left",
                "swipe_distance": 0.4,
                "swipe_duration": 500,
                "wait_after": 3.0,
                "on_fail": "skip",
            },
            {
                "name": "战场探索",
                "template": "battlefield_explore.png",
                "action": "find_and_click",
                "click_target": "match", "threshold": 0.70,
                "max_retries": 5, "retry_interval": 1.5,
                "wait_after": 6.0, "timeout": 30.0, "on_fail": "abort",
            },
            {
                "name": "快速扫荡-战场",
                "template": "quick_sweep.png",
                "action": "find_and_click",
                "click_target": "match", "threshold": 0.70,
                "max_retries": 5, "retry_interval": 1.5,
                "wait_after": 6.0, "timeout": 30.0, "on_fail": "abort",
            },
            # 回主页
            {
                "name": "回主页",
                "template": "home.png",
                "action": "find_and_click",
                "click_target": "match", "threshold": 0.75,
                "max_retries": 5, "retry_interval": 1.5,
                "wait_after": 3.0, "timeout": 30.0, "on_fail": "skip",
            },
            # TODO: 还有 2 个地点待用户补充截图
        ],
    },
    # ================================================================
    # Route 4: 出击-演习
    # ================================================================
    {
        "name": "exercise",
        "label": "出击-演习",
        "enabled": True,
        "loop": 2,             # 每天2次刷新机会，跑2轮
        "loop_restart_from": 3,  # 第二轮从第3步（更换对手）开始
        "img_dir": "img/出击-演习",
        "steps": [
            # 出击（共用图片，走回退到 img/出击）
            {
                "name": "点击出击",
                "template": "sortie.png",
                "action": "find_and_click",
                "click_target": "match", "threshold": 0.70,
                "max_retries": 5, "retry_interval": 1.5,
                "wait_after": 6.0, "timeout": 30.0, "on_fail": "abort",
            },
            # 演习
            {
                "name": "点击演习",
                "template": "exercise.png",
                "action": "find_and_click",
                "click_target": "match", "threshold": 0.70,
                "max_retries": 5, "retry_interval": 1.5,
                "wait_after": 2.5, "timeout": 30.0, "on_fail": "abort",
            },
            # 更换对手（每天2次机会，用完了会找不到）
            {
                "name": "更换对手",
                "template": "change_opponent.png",
                "action": "find_and_click",
                "click_target": "match", "threshold": 0.70,
                "max_retries": 5, "retry_interval": 1.5,
                "wait_after": 2.5, "timeout": 30.0, "on_fail": "skip",
            },
            # 连续挑战
            {
                "name": "连续挑战",
                "template": "consecutive_challenge.png",
                "action": "find_and_click",
                "click_target": "match", "threshold": 0.70,
                "max_retries": 5, "retry_interval": 1.5,
                "wait_after": 6.0, "timeout": 30.0, "on_fail": "abort",
            },
            # 全选
            {
                "name": "全选",
                "template": "select_all.png",
                "action": "find_and_click",
                "click_target": "match", "threshold": 0.70,
                "max_retries": 5, "retry_interval": 1.5,
                "wait_after": 6.0, "timeout": 30.0, "on_fail": "abort",
            },
            # 开始托管 → 长时间等待自动战斗（看门狗捕获"确定"即结束）
            {
                "name": "开始托管",
                "template": "start_auto.png",
                "action": "find_and_click",
                "click_target": "match", "threshold": 0.70,
                "max_retries": 5, "retry_interval": 1.5,
                "wait_after": 300.0,    # 等 5 分钟，看门狗每 1s 检查 confirm
                "timeout": 30.0, "on_fail": "abort",
            },
        ],
    },
]

# =====================================================================
# 全局弹窗规则：嵌入步间等待中检查，命中则点击
# =====================================================================

GLOBAL_WATCHERS: List[Dict[str, Any]] = [
    {
        "name": "点击继续",
        "template": "tap_to_continue.png",
        "click_target": "match",
        "threshold": 0.75,
        "stop_wait": True,         # 命中后立即结束当前等待
    },
    {
        "name": "确定",
        "template": "confirm.png",
        "click_target": "match",
        "threshold": 0.75,
        "stop_wait": True,         # 命中后立即结束当前等待
    },
]

# 看门狗检查间隔（嵌入步间等待中，每 1s 检查一次）
_WATCH_INTERVAL = 1.0


# =====================================================================
# 步骤运行器
# =====================================================================


class LoginTaskRunner:
    """
    按声明式步骤列表依次执行的登录任务运行器。

    使用方式:
        framework = get_ok()                    # 获取 ADB 框架
        runner = LoginTaskRunner(framework, STEPS, global_watchers=GLOBAL_WATCHERS)
        success = runner.run()                  # 顺序执行所有步骤
    """

    def __init__(
        self,
        framework: OKFramework,
        route: Dict[str, Any],
        global_watchers: List[Dict[str, Any]] | None = None,
    ):
        """
        Args:
            framework:       已连接设备的 OKFramework 实例
            route:           线路定义 dict（含 name, label, enabled, img_dir, steps）
            global_watchers: 全局看门狗规则列表（可选）
        """
        self.framework = framework
        self.route = route
        self.steps = route.get("steps", [])
        self.img_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            route.get("img_dir", "img"),
        )
        self.global_watchers = global_watchers or GLOBAL_WATCHERS

        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._watcher_hits = 0  # 看门狗命中计数

        self.results: List[Dict[str, Any]] = []
        self.current_step_index: int = 0

        logger.info(
            "LoginTaskRunner initialized — route '%s' (%s), %d step(s), %d watcher rule(s)",
            route.get("name"),
            route.get("label"),
            len(self.steps),
            len(self.global_watchers),
        )
        for i, s in enumerate(self.steps, 1):
            logger.info("  Step %d: %s (action=%s)", i, s.get("name"), s.get("action"))
        for i, w in enumerate(self.global_watchers, 1):
            logger.info("  Watcher %d: %s", i, w.get("template"))

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------

    def run(self, start_from: int = 0) -> bool:
        """
        按顺序执行所有步骤。

        Args:
            start_from: 从第几步开始（0-based 索引），默认 0 从头开始。

        Returns:
            True 表示全部步骤成功（或被跳过的非关键步骤不影响），
            False 表示某个 abort 步骤失败导致流程终止。
        """
        # 线路循环控制: loop=-1 无限循环, loop=1 跑一次 (默认)
        loop_count = self.route.get("loop", 1)
        if loop_count == 0:
            loop_count = 1

        overall_start = time.time()
        all_ok = True
        current_loop = 0

        while loop_count == -1 or current_loop < loop_count:
            current_loop += 1
            if loop_count != 1:
                logger.info("")
                logger.info(">>> Loop %d/%s <<<", current_loop, "∞" if loop_count == -1 else str(loop_count))

            for idx in range(start_from, len(self.steps)):
                if self._stop_event.is_set():
                    logger.warning("Stop event set, aborting remaining steps")
                    all_ok = False
                    break

                step = self.steps[idx]
                self.current_step_index = idx

                step_name = step.get("name", f"Step {idx + 1}")
                logger.info("-" * 50)
                logger.info(
                    ">>> Step %d/%d: %s",
                    idx + 1,
                    len(self.steps),
                    step_name,
                )

                step_start = time.time()
                success = self._run_step(step)
                step_elapsed = time.time() - step_start

                self.results.append({
                    "index": idx,
                    "name": step_name,
                    "success": success,
                    "elapsed": step_elapsed,
                    "on_fail": step.get("on_fail", DEFAULT_ON_FAIL),
                })

                if success:
                    logger.info(
                        "<<< Step '%s' SUCCESS (%.1fs)",
                        step_name,
                        step_elapsed,
                    )
                    wait_after = step.get("wait_after", DEFAULT_WAIT_AFTER)
                    if wait_after > 0:
                        self._watch_and_wait(wait_after)
                else:
                    on_fail = step.get("on_fail", DEFAULT_ON_FAIL)
                    logger.error(
                        "<<< Step '%s' FAILED (%.1fs), on_fail=%s",
                        step_name, step_elapsed, on_fail,
                    )
                    if on_fail == "abort":
                        all_ok = False
                        break
                    elif on_fail == "skip":
                        logger.warning("Skipping failed step and continuing...")
                    else:
                        logger.error("Unknown on_fail policy: %s, treating as abort", on_fail)
                        all_ok = False
                        break

            # 循环重置：默认从头开始，可配置 loop_restart_from
            start_from = self.route.get("loop_restart_from", 0) - 1
            start_from = max(0, start_from)  # 转为 0-based
            if not all_ok:
                break

        overall_elapsed = time.time() - overall_start
        self._print_summary(overall_elapsed)

        return all_ok

    def stop(self) -> None:
        """设置停止信号，当前步骤完成后退出。"""
        logger.info("Stop requested — will exit after current step completes")
        self._stop_event.set()

    def run_single_step(self, step_index: int) -> bool:
        """
        执行单个步骤（供单独调试使用），同时启动看门狗。

        Args:
            step_index: 0-based 步骤索引。

        Returns:
            True 表示该步骤成功。
        """
        if step_index < 0 or step_index >= len(self.steps):
            logger.error(
                "Invalid step index %d. Available: 0-%d",
                step_index,
                len(self.steps) - 1,
            )
            return False

        step = self.steps[step_index]
        logger.info("Running single step: %s", step.get("name"))
        return self._run_step(step)

    # ------------------------------------------------------------------
    # 看门狗管理
    # ------------------------------------------------------------------

    def _watch_and_wait(self, seconds: float) -> None:
        """
        步间等待 + 内嵌看门狗检查。

        替代独立的后台线程：在等待期间每 1s 截一次屏，
        检查 GLOBAL_WATCHERS 规则，命中则点击。
        无额外线程开销，不重复截屏，不抢主流程节奏。
        """
        if seconds <= 0:
            return
        elapsed = 0.0
        while elapsed < seconds:
            if self._stop_event.is_set():
                return
            chunk = min(1.0, seconds - elapsed)
            time.sleep(chunk)
            elapsed += chunk
            # 检查全局弹窗
            if self.global_watchers:
                try:
                    screen = self.framework.screenshot()
                    if screen is not None:
                        for rule in self.global_watchers:
                            if self._check_trigger_rule(rule, screen):
                                logger.info("  Watcher stop_wait → ending wait early (%.1fs elapsed)", elapsed)
                                return  # 命中 stop_wait 规则，立即结束等待
                except Exception as e:
                    logger.debug("Watcher check error: %s", e)

    # ------------------------------------------------------------------
    # 步骤分发 & 具体动作实现
    # ------------------------------------------------------------------

    def _run_step(self, step: Dict[str, Any]) -> bool:
        """
        分发器：根据 step["action"] 调用对应的处理方法，并施加超时控制。

        Args:
            step: 步骤 dict。

        Returns:
            True 表示步骤成功。
        """
        action = step.get("action", "find_and_click")
        timeout = step.get("timeout", DEFAULT_TIMEOUT)

        # 由于 ADB 命令可能阻塞，这里用简单的 deadline 检查（非抢占式）
        deadline = time.time() + timeout

        try:
            if action == "find_and_click":
                return self._find_and_click(step, deadline)
            elif action == "wait":
                return self._wait(step)
            elif action == "swipe":
                return self._swipe(step)
            elif action == "shell":
                return self._shell(step)
            else:
                logger.error("Unknown action type: %s", action)
                return False
        except Exception as e:
            logger.exception("Step '%s' raised exception: %s", step.get("name"), e)
            return False

    # ------------------------------------------------------------------
    # find_and_click
    # ------------------------------------------------------------------

    def _find_and_click(self, step: Dict[str, Any], deadline: float) -> bool:
        """
        截图 → 模板匹配 → 点击匹配中心，带重试。

        流程:
          1. 根据 template 文件名(或列表)构造完整路径
          2. 循环 max_retries 次:
             a. 检查超时 deadline
             b. 截取当前屏幕
             c. 对每个模板依次执行多尺度模板匹配（列表时为 OR 关系）
             d. 取所有模板中置信度最高的匹配
             e. 若匹配成功 → 点击目标 → 返回 True
             f. 若全部模板都不匹配 → sleep(retry_interval) → 重试
          3. 所有重试耗尽 → 返回 False

        Args:
            step:    步骤 dict
            deadline: 超时时间戳

        Returns:
            True 表示找到并点击成功。
        """
        template_names = step.get("template", "")
        # 支持单个模板字符串或列表（匹配任意一个即可）
        if isinstance(template_names, str):
            template_names = [template_names]
        if not template_names:
            logger.error("find_and_click requires 'template' field")
            return False

        # 预检查所有模板文件是否存在（线路目录优先，找不到回退到共享 img/）
        template_paths = []
        for tpl_name in template_names:
            tpl_path = os.path.join(self.img_dir, tpl_name)
            if not os.path.isfile(tpl_path):
                # 回退到共享 img/ 目录
                tpl_path = os.path.join(IMG_DIR, tpl_name)
                if os.path.isfile(tpl_path):
                    logger.debug("  Using shared template: %s", tpl_path)
                else:
                    logger.error("Template file not found: %s (checked both route and shared dir)", tpl_name)
                    return False
            template_paths.append(tpl_path)

        threshold = step.get("threshold", DEFAULT_THRESHOLD)
        max_retries = step.get("max_retries", DEFAULT_MAX_RETRIES)
        retry_interval = step.get("retry_interval", DEFAULT_RETRY_INTERVAL)

        # 检查超时
        if time.time() >= deadline:
            logger.error("Step '%s' timed out before first attempt", step["name"])
            return False

        for attempt in range(1, max_retries + 1):
            if self._stop_event.is_set():
                logger.info("Stop requested, aborting retries")
                return False

            if time.time() >= deadline:
                logger.error(
                    "Step '%s' timed out after %d attempt(s)",
                    step["name"],
                    attempt - 1,
                )
                return False

            logger.info(
                "  Attempt %d/%d: matching %d template(s) (threshold=%.2f)...",
                attempt,
                max_retries,
                len(template_paths),
                threshold,
            )

            # 截图
            screen = self.framework.screenshot()
            if screen is None:
                logger.warning("  Screenshot returned None, retrying in %.1fs...", retry_interval)
                self._interruptible_sleep(retry_interval)
                continue

            # 模板匹配 — 遍历所有模板，取置信度最高的
            all_matches = []
            for tpl_path in template_paths:
                tpl_name = os.path.basename(tpl_path)
                tpl_matches = self.framework.match_template(
                    tpl_path,
                    threshold=threshold,
                    screenshot=screen,
                )
                if tpl_matches:
                    logger.debug("    '%s' → %d match(es)", tpl_name, len(tpl_matches))
                    all_matches.extend(tpl_matches)
                else:
                    logger.debug("    '%s' → no match", tpl_name)

            # ---- 模式: click_all — 按顺序点一遍所有匹配 ----
            click_all = step.get("click_all", False)
            if click_all and all_matches:
                click_order = step.get("click_order", "top_to_bottom")
                if click_order == "top_to_bottom":
                    all_matches.sort(key=lambda m: m[1])  # 按 Y 升序
                elif click_order == "bottom_to_top":
                    all_matches.sort(key=lambda m: -(m[1] + m[3]))
                elif click_order == "left_to_right":
                    all_matches.sort(key=lambda m: m[0])
                elif click_order == "right_to_left":
                    all_matches.sort(key=lambda m: -(m[0] + m[2]))
                logger.info(
                    "  click_all: %d matches, order=%s",
                    len(all_matches), click_order,
                )
                for i, m in enumerate(all_matches):
                    if self._stop_event.is_set():
                        return False
                    mx, my, mw, mh, mconf = m
                    cx, cy = mx + mw // 2, my + mh // 2
                    logger.info(
                        "    [%d/%d] (%d,%d) conf=%.4f -> click (%d,%d)",
                        i + 1, len(all_matches), mx, my, mconf, cx, cy,
                    )
                    self.framework.click(cx, cy, delay=0)
                    if i < len(all_matches) - 1:
                        time.sleep(step.get("click_interval", 0.3))
                # 点完后额外等待
                after_delay = step.get("click_all_after_delay", 1.0)
                logger.info("  click_all done, wait %.1fs for popups...", after_delay)
                self._interruptible_sleep(after_delay)
                return True

            # ---- 模式: 单匹配 — 按 pick 策略选最佳 ----
            matches = self._pick_best(all_matches, step.get("pick", "best"))

            if matches:
                # 取置信度最高的匹配
                best = matches[0]
                x, y, w, h, conf = best

                # 根据 click_target 决定点击坐标
                click_target = step.get("click_target", "match")

                if click_target == "match":
                    # 默认: 点击模板匹配框的中心
                    cx, cy = x + w // 2, y + h // 2
                elif click_target == "screen_center":
                    # 点击整个屏幕的正中心（用于"点击任意位置进入游戏"场景）
                    cx, cy = self.framework.screen_width // 2, self.framework.screen_height // 2
                elif isinstance(click_target, (list, tuple)) and len(click_target) == 2:
                    # 指定像素坐标 [x, y]
                    cx, cy = int(click_target[0]), int(click_target[1])
                else:
                    logger.error("Unknown click_target: %s", click_target)
                    return False

                logger.info(
                    "  Match found: (%d,%d,%d,%d) confidence=%.4f | click_target=%s → (%d,%d)",
                    x, y, w, h, conf, click_target, cx, cy,
                )

                # ---- 执行点击 ----
                click_while_present = step.get("click_while_present", False)
                click_count = step.get("click_count", 1)
                click_interval = step.get("click_interval", 0.3)
                max_clicks = step.get("max_clicks", 500)

                # ---- 主点击 ----
                if click_while_present:
                    click_num = 0
                    still_visible = True
                    while still_visible and click_num < max_clicks:
                        if self._stop_event.is_set():
                            return False
                        if not self.framework.click(cx, cy, delay=0):
                            logger.warning("  Click %d failed", click_num + 1)
                            break
                        click_num += 1
                        logger.info("  Clicked %d (%d, %d)", click_num, cx, cy)
                        self._interruptible_sleep(click_interval)
                        screen = self.framework.screenshot()
                        if screen is None:
                            logger.warning("  Screenshot failed during click_while_present, stopping")
                            break
                        still_visible = False
                        for tpl_path in template_paths:
                            if self.framework.match_template(
                                tpl_path, threshold=threshold, screenshot=screen
                            ):
                                still_visible = True
                                break
                        if still_visible:
                            logger.info("  Image still present, clicking again...")
                        else:
                            logger.info("  Image disappeared after %d clicks, done!", click_num)
                    if click_num >= max_clicks:
                        logger.warning("  Reached max_clicks limit (%d), stopping", max_clicks)
                else:
                    all_clicked = True
                    for i in range(click_count):
                        if self._stop_event.is_set():
                            return False
                        if not self.framework.click(cx, cy, delay=0):
                            logger.warning("  Click %d/%d failed", i + 1, click_count)
                            all_clicked = False
                            break
                        logger.info("  Clicked %d/%d (%d, %d)", i + 1, click_count, cx, cy)
                        if i < click_count - 1:
                            time.sleep(click_interval)
                    if not all_clicked:
                        logger.warning("  Some clicks failed, retrying...")
                        self._interruptible_sleep(retry_interval)
                        continue

                # ---- 补点: 主点击结束后，在指定位置额外多点几下 ----
                extra_clicks = step.get("extra_clicks", 0)
                if extra_clicks > 0:
                    ect = step.get("extra_clicks_target", "screen_center")
                    eci = step.get("extra_clicks_interval", 0.3)
                    if ect == "screen_center":
                        ecx, ecy = self.framework.screen_width // 2, self.framework.screen_height // 2
                    elif ect == "match":
                        ecx, ecy = cx, cy
                    elif isinstance(ect, (list, tuple)) and len(ect) == 2:
                        ecx, ecy = int(ect[0]), int(ect[1])
                    else:
                        ecx, ecy = cx, cy
                    logger.info("  Extra clicks: %d x (%d,%d)", extra_clicks, ecx, ecy)
                    for ei in range(extra_clicks):
                        if self._stop_event.is_set():
                            return False
                        self.framework.click(ecx, ecy, delay=0)
                        logger.info("    Extra click %d/%d (%d, %d)", ei + 1, extra_clicks, ecx, ecy)
                        if ei < extra_clicks - 1:
                            time.sleep(eci)

                return True

            else:
                logger.info(
                    "  No match found (attempt %d/%d)",
                    attempt,
                    max_retries,
                )
                if attempt < max_retries:
                    logger.debug("  Retrying in %.1fs...", retry_interval)
                    self._interruptible_sleep(retry_interval)

        # ---- 所有重试耗尽：尝试 fallback_template ----
        fallback_names = step.get("fallback_template", "")
        if fallback_names:
            if isinstance(fallback_names, str):
                fallback_names = [fallback_names]
            logger.info(
                "  Primary template(s) not found, trying fallback: %s",
                fallback_names,
            )
            for fb_name in fallback_names:
                fb_path = os.path.join(self.img_dir, fb_name)
                if not os.path.isfile(fb_path):
                    fb_path = os.path.join(IMG_DIR, fb_name)
                if not os.path.isfile(fb_path):
                    logger.warning("Fallback template not found: %s", fb_name)
                    continue
                fb_screen = self.framework.screenshot()
                if fb_screen is None:
                    continue
                fb_matches = self.framework.match_template(
                    fb_path, threshold=threshold, screenshot=fb_screen
                )
                if fb_matches:
                    best = fb_matches[0]
                    fx, fy, fw, fh, fconf = best
                    fcx, fcy = fx + fw // 2, fy + fh // 2
                    logger.info(
                        "  Fallback match: '%s' (%d,%d) confidence=%.4f → clicking (%d,%d)",
                        fb_name, fx, fy, fconf, fcx, fcy,
                    )
                    self.framework.click(fcx, fcy, delay=0.1)
                    return True
                else:
                    logger.info("  Fallback '%s' not found", fb_name)

        logger.error(
            "Step '%s': all %d retries exhausted, template(s) %s not found",
            step["name"],
            max_retries,
            template_names,
        )
        return False

    # ------------------------------------------------------------------
    # wait
    # ------------------------------------------------------------------

    def _wait(self, step: Dict[str, Any]) -> bool:
        """
        纯等待步骤（用于游戏加载、动画过渡等）。

        使用 step["wait_after"] 决定等待时长。
        """
        wait_seconds = step.get("wait_after", DEFAULT_WAIT_AFTER)
        logger.info("  Waiting %.1f seconds...", wait_seconds)
        self._interruptible_sleep(wait_seconds)
        return True

    # ------------------------------------------------------------------
    # swipe
    # ------------------------------------------------------------------

    def _swipe(self, step: Dict[str, Any]) -> bool:
        """
        滑动步骤。

        支持两种模式:
          1. 方向模式: swipe_direction = "left"/"right"/"up"/"down"
             + swipe_distance = 滑动距离占比（默认 0.4）
          2. 坐标模式: swipe_from / swipe_to 指定像素坐标
        """
        direction = step.get("swipe_direction", "")
        if direction:
            # 方向模式
            w = self.framework.screen_width
            h = self.framework.screen_height
            dist = step.get("swipe_distance", 0.4)
            cx, cy = w // 2, h // 2
            if direction == "left":
                from_x, from_y = int(w * 0.7), cy
                to_x, to_y = int(w * (0.7 - dist)), cy
            elif direction == "right":
                from_x, from_y = int(w * 0.3), cy
                to_x, to_y = int(w * (0.3 + dist)), cy
            elif direction == "up":
                from_x, from_y = cx, int(h * 0.7)
                to_x, to_y = cx, int(h * (0.7 - dist))
            elif direction == "down":
                from_x, from_y = cx, int(h * 0.3)
                to_x, to_y = cx, int(h * (0.3 + dist))
            else:
                logger.error("Unknown swipe_direction: %s", direction)
                return False
        else:
            from_x, from_y = step.get("swipe_from", (0, 0))
            to_x, to_y = step.get("swipe_to", (0, 0))

        duration = step.get("swipe_duration", 500)

        if from_x == to_x and from_y == to_y:
            logger.warning("swipe_from == swipe_to, no-op swipe")
            return True

        logger.info(
            "  Swiping (%d,%d) -> (%d,%d), duration=%dms",
            from_x, from_y, to_x, to_y, duration,
        )
        return self.framework.swipe(from_x, from_y, to_x, to_y, duration_ms=duration)

    # ------------------------------------------------------------------
    # shell — 执行 ADB shell 命令
    # ------------------------------------------------------------------

    def _shell(self, step: Dict[str, Any]) -> bool:
        """
        执行 ADB shell 命令步骤。

        支持的 step 字段:
          command    — str: 要执行的 shell 命令
                     — List[str]: 多个命令，依次执行，任一失败则返回 False

        示例:
          {"action": "shell", "command": "monkey -p com.x.y -c android.intent.category.LAUNCHER 1"}
          {"action": "shell", "command": ["input keyevent 4", "input keyevent 4"]}
        """
        commands = step.get("command", "")
        if isinstance(commands, str):
            commands = [commands]
        if not commands:
            logger.error("shell action requires 'command' field")
            return False

        for i, cmd in enumerate(commands):
            if self._stop_event.is_set():
                return False
            logger.info("  shell [%d/%d]: %s", i + 1, len(commands), cmd)
            output = self.framework.shell(cmd)
            if output:
                logger.debug("    → %s", output[:200])

        return True

    # ------------------------------------------------------------------
    # 多匹配选择器
    # ------------------------------------------------------------------

    @staticmethod
    def _pick_best(
        matches: List[Tuple[int, int, int, int, float]],
        strategy: str = "best",
    ) -> List[Tuple[int, int, int, int, float]]:
        """
        从多个模板匹配结果中按指定策略选出最佳的一个。

        策略选项:
          "best"              — 默认：置信度最高（兼容旧行为）
          "topmost"           — Y 坐标最小的（最靠上）
          "bottommost"        — Y+height 最大的（最靠下）
          "leftmost"          — X 坐标最小的（最靠左）
          "rightmost"         — X+width 最大的（最靠右）
          "best_topmost"      — 在同置信度(±0.02)中挑最靠上的
          "best_bottommost"   — 在同置信度(±0.02)中挑最靠下的

        Args:
            matches:  匹配列表 [(x, y, w, h, conf), ...]
            strategy: 选择策略

        Returns:
            只包含被选中匹配的列表（保持接口兼容）
        """
        if not matches:
            return []
        if len(matches) == 1:
            return matches

        if strategy == "best":
            matches.sort(key=lambda m: m[4], reverse=True)
        elif strategy == "topmost":
            matches.sort(key=lambda m: m[1])  # 按 y 升序
        elif strategy == "bottommost":
            matches.sort(key=lambda m: -(m[1] + m[3]))  # 按 y+h 降序
        elif strategy == "leftmost":
            matches.sort(key=lambda m: m[0])  # 按 x 升序
        elif strategy == "rightmost":
            matches.sort(key=lambda m: -(m[0] + m[2]))  # 按 x+w 降序
        elif strategy == "best_topmost":
            # 置信度 top 2% 内挑最靠上的
            top_conf = max(m[4] for m in matches)
            candidates = [m for m in matches if m[4] >= top_conf - 0.02]
            candidates.sort(key=lambda m: m[1])
            return candidates[:1]
        elif strategy == "best_bottommost":
            # 置信度 top 2% 内挑最靠下的
            top_conf = max(m[4] for m in matches)
            candidates = [m for m in matches if m[4] >= top_conf - 0.02]
            candidates.sort(key=lambda m: -(m[1] + m[3]))
            return candidates[:1]
        else:
            logger.warning("Unknown pick strategy '%s', falling back to 'best'", strategy)
            matches.sort(key=lambda m: m[4], reverse=True)

        return matches[:1]

    def _check_trigger_rule(self, rule: Dict[str, Any], screen) -> bool:
        """检查单条看门狗规则，命中则点击。返回 True 表示命中且 stop_wait 为真。"""
        template_names = rule.get("template", "")
        if isinstance(template_names, str):
            template_names = [template_names]
        threshold = rule.get("threshold", 0.75)
        for tpl_name in template_names:
            tpl_path = os.path.join(IMG_DIR, tpl_name)
            if not os.path.isfile(tpl_path):
                continue
            matches = self.framework.match_template(
                tpl_path, threshold=threshold, screenshot=screen
            )
            if matches:
                best = matches[0]
                x, y, w, h, conf = best
                click_target = rule.get("click_target", "match")
                if click_target == "match":
                    cx, cy = x + w // 2, y + h // 2
                elif click_target == "screen_center":
                    cx, cy = self.framework.screen_width // 2, self.framework.screen_height // 2
                else:
                    cx, cy = x + w // 2, y + h // 2
                self._watcher_hits += 1
                logger.info(
                    "🔔 Watcher hit #%d: '%s' @ (%d,%d) conf=%.4f → click (%d,%d)",
                    self._watcher_hits, tpl_name, x, y, conf, cx, cy,
                )
                self.framework.click(cx, cy, delay=0.1)
                # stop_wait: 命中此规则后立即结束当前等待
                return rule.get("stop_wait", False)

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def _interruptible_sleep(self, seconds: float) -> None:
        """
        可被 _stop_event 中断的 sleep。

        每秒检查一次 stop 信号，避免在长时间 sleep 中无法退出。
        """
        if seconds <= 0:
            return
        remaining = seconds
        while remaining > 0:
            if self._stop_event.is_set():
                logger.debug("Sleep interrupted by stop event")
                return
            chunk = min(1.0, remaining)
            time.sleep(chunk)
            remaining -= chunk

    def _print_summary(self, overall_elapsed: float) -> None:
        """打印全部步骤的执行汇总。"""
        logger.info("=" * 60)
        logger.info("Execution Summary (total %.1fs):", overall_elapsed)

        success_count = sum(1 for r in self.results if r["success"])
        fail_count = len(self.results) - success_count

        for r in self.results:
            status = "OK" if r["success"] else "FAIL"
            logger.info(
                "  [%s] %s (%.1fs)",
                status,
                r["name"],
                r["elapsed"],
            )

        logger.info(
            "Total: %d step(s) — %d succeeded, %d failed",
            len(self.results),
            success_count,
            fail_count,
        )
        logger.info("=" * 60)


# =====================================================================
# 入口
# =====================================================================

def main():
    """
    主函数：连接设备，初始化框架，执行登录步骤序列。

    命令行参数:
        --step N   只执行第 N 步（1-based），用于单步调试
        --host H   指定 ADB host（默认 127.0.0.1）
        --port P   指定 ADB port（默认 7555）
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Game Login Automation — step-based task runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python login_task.py              # Run all steps
  python login_task.py --step 1     # Run only step 1
  python login_task.py --host 127.0.0.1 --port 62001  # Custom ADB port
        """,
    )
    parser.add_argument(
        "--route", type=str, default="",
        help="Run only the specified route by name (e.g. 'login', 'oil'). Empty = run all enabled.",
    )
    parser.add_argument(
        "--step", type=int, default=0,
        help="(requires --route) Run only the specified step (1-based) within the route.",
    )
    parser.add_argument(
        "--host", type=str, default=DEFAULT_ADB_HOST,
        help=f"ADB server host (default: {DEFAULT_ADB_HOST})",
    )
    parser.add_argument(
        "--port", type=int, default=DEFAULT_ADB_PORT,
        help=f"Emulator ADB port (default: {DEFAULT_ADB_PORT})",
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List all routes and exit.",
    )
    args = parser.parse_args()

    # --list: 列出所有线路
    if args.list:
        print(f"{'Route':<12} {'Label':<16} {'Enabled':<8} {'Steps':<6} {'Img Dir'}")
        print("-" * 65)
        for r in ROUTES:
            print(f"{r['name']:<12} {r['label']:<16} {str(r['enabled']):<8} {len(r['steps']):<6} {r['img_dir']}")
        print(f"\nGlobal Watchers: {len(GLOBAL_WATCHERS)} rule(s)")
        sys.exit(0)

    # --step 需要配合 --route 使用
    if args.step > 0 and not args.route:
        logger.error("--step requires --route. Use --list to see available routes.")
        sys.exit(1)

    # ---- 1. 获取框架单例并连接设备 ----
    logger.info("Connecting to device at %s:%d...", args.host, args.port)
    framework = get_ok(host=args.host, port=args.port)

    if not framework.is_online():
        logger.error(
            "Device %s:%d is offline.",
            args.host, args.port,
        )
        sys.exit(1)

    logger.info("Device online: %s", framework.serial)

    # ---- 2. 选择要执行的线路 ----
    if args.route:
        # 单独跑指定线路
        routes_to_run = [r for r in ROUTES if r["name"] == args.route]
        if not routes_to_run:
            logger.error("Route '%s' not found. Use --list to see available routes.", args.route)
            sys.exit(1)
    else:
        # 跑所有 enabled 的线路
        routes_to_run = [r for r in ROUTES if r.get("enabled", True)]

    if not routes_to_run:
        logger.info("No enabled routes to run.")
        sys.exit(0)

    logger.info(
        "Routes to run: %s",
        ", ".join(f"{r['name']}({r['label']})" for r in routes_to_run),
    )

    overall_success = True

    try:
        for route in routes_to_run:
            logger.info("")
            logger.info("=" * 60)
            logger.info(">>> Route: %s (%s)", route["name"], route["label"])
            logger.info("=" * 60)

            runner = LoginTaskRunner(framework, route, global_watchers=GLOBAL_WATCHERS)

            if args.step > 0:
                step_idx = args.step - 1
                if step_idx >= len(route["steps"]):
                    logger.error("Step %d out of range for route '%s'", args.step, route["name"])
                    sys.exit(1)
                route_ok = runner.run_single_step(step_idx)
            else:
                route_ok = runner.run()

            if not route_ok:
                logger.warning("Route '%s' completed with failures", route["name"])
                overall_success = False
                # 单线路失败不终止其他线路

        if overall_success:
            logger.info("All routes completed successfully")
            sys.exit(0)
        else:
            logger.warning("Some routes had failures")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Interrupted by user (Ctrl+C)")
        sys.exit(130)
    except Exception as e:
        logger.exception("Unhandled exception: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
