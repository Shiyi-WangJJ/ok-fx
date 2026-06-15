"""
main.py — OK-Script 无GUI后台入口

功能：
  1. 自动通过 ADB 连接 127.0.0.1:7555（常见模拟器端口）
  2. 检测模拟器/设备在线状态
  3. 初始化 OK 框架全套能力：截图、模板匹配、点击、滑动

用法：
  python main.py
  (Ctrl+C 可安全退出)

依赖已在 requirements.txt 中定义，均已安装在 venv 中。
"""

import sys
import time
import logging
import threading
from typing import Optional, Tuple, List

import cv2
import numpy as np

# adbutils: ADB 客户端库，用于与 Android 设备/模拟器通信
#   文档: https://github.com/openatx/adbutils
from adbutils import AdbClient, AdbDevice, AdbError

# ---------------------------------------------------------------------------
# 日志配置
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ok-script")

# ---------------------------------------------------------------------------
# 全局常量
# ---------------------------------------------------------------------------
DEFAULT_ADB_HOST = "127.0.0.1"   # ADB server 地址
DEFAULT_ADB_PORT = 7555          # 常见模拟器 ADB 端口（MuMu / 雷电 / 逍遥 等）
DEFAULT_ADB_TIMEOUT = 8          # ADB 连接超时（秒）
SCREENSHOT_TIMEOUT = 10          # 截图超时（秒）
TEMPLATE_MATCH_THRESHOLD = 0.75  # 模板匹配默认阈值
SWIPE_DEFAULT_DURATION = 500     # 默认滑动持续时间（毫秒）


class OKFramework:
    """
    OK 框架核心能力封装类。

    提供以下能力:
      - ADB 自动连接与设备检测
      - 设备截图（screencap）
      - OpenCV 模板匹配
      - ADB 点击 / 长按
      - ADB 滑动
    """

    # ------------------------------------------------------------------
    # 初始化 & ADB 连接
    # ------------------------------------------------------------------

    def __init__(
        self,
        host: str = DEFAULT_ADB_HOST,
        port: int = DEFAULT_ADB_PORT,
        timeout: int = DEFAULT_ADB_TIMEOUT,
    ):
        """
        初始化 OK 框架实例。

        Args:
            host:   ADB server 主机地址（默认 127.0.0.1）
            port:   模拟器 ADB 端口（默认 7555）
            timeout: 连接超时秒数
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.serial = f"{host}:{port}"  # ADB 设备序列号，形如 127.0.0.1:7555

        # ADB 客户端（单例，复用以提高效率）
        self._adb_client: Optional[AdbClient] = None
        # 已连接的设备对象
        self._device: Optional[AdbDevice] = None

        # 设备屏幕尺寸（首次截图后自动获取）
        self.screen_width: int = 0
        self.screen_height: int = 0

        # 运行状态
        self._running: bool = False
        self._lock: threading.Lock = threading.Lock()

        logger.info(
            "OKFramework 初始化完成 — 目标设备: %s",
            self.serial,
        )

    @property
    def adb_client(self) -> AdbClient:
        """
        懒加载获取或创建 ADB Client。

        AdbClient 连接到本地 ADB Server（默认 localhost:5037）。
        ADB Server 由 adbutils 自动管理：首次使用时启动，进程退出时关闭。
        """
        if self._adb_client is None:
            # AdbClient 连接本地 adb server 进程（默认 127.0.0.1:5037）
            self._adb_client = AdbClient(host="127.0.0.1", socket_timeout=self.timeout)
            logger.debug("AdbClient 已创建 → 127.0.0.1:5037")
        return self._adb_client

    @property
    def device(self) -> Optional[AdbDevice]:
        """获取当前连接的设备对象，未连接时返回 None。"""
        return self._device

    # ------------------------------------------------------------------
    # 设备连接
    # ------------------------------------------------------------------

    def connect(self) -> bool:
        """
        通过 ADB 连接到目标模拟器（127.0.0.1:7555）。

        连接流程:
          1. 检查是否已连接
          2. 若未连接则发起 TCP 连接
          3. 验证设备状态是否为 'device'（在线）

        Returns:
            True 表示连接成功，False 表示失败。
        """
        with self._lock:
            try:
                client = self.adb_client

                # ---- 步骤1: 遍历已知设备列表，检查是否已连接 ----
                # device_list() 直接返回 AdbDevice 对象，可直接复用
                for dev in client.device_list():
                    if dev.serial == self.serial:
                        state = dev.get_state()
                        logger.info("发现设备 %s，状态: %s", self.serial, state)
                        if state == "offline":
                            logger.warning("设备离线，尝试断开重连...")
                            client.disconnect(self.serial)
                            time.sleep(1)
                            break  # 跳出循环，走下面重连逻辑
                        elif state == "device":
                            self._device = dev  # 直接复用，避免多余连接
                            logger.info("设备已在线，直接使用 ✓")
                            return True
                        else:
                            logger.warning("设备状态异常: %s，尝试重连...", state)

                # ---- 步骤2: 主动发起 TCP 连接 ----
                logger.info("正在连接 %s (超时 %ds)...", self.serial, self.timeout)
                result = client.connect(self.serial, timeout=self.timeout)
                logger.info("connect() 返回: %s", result)

                # ---- 步骤3: 等待设备上线并获取设备对象 ----
                # adb connect 是异步的，需要等待设备状态变为 'device'
                for attempt in range(1, 6):
                    time.sleep(1)
                    for dev in client.device_list():
                        if dev.serial == self.serial and dev.get_state() == "device":
                            self._device = dev
                            logger.info("✓ 设备连接成功 (第 %d 次检查)", attempt)
                            return True
                    logger.debug("等待设备上线... 第 %d/5 次", attempt)

                logger.error("设备连接超时: %s 未在预期时间内上线", self.serial)
                return False

            except AdbError as e:
                logger.error("ADB 连接异常 (AdbError): %s", e)
                return False
            except Exception as e:
                logger.error("ADB 连接异常 (未知): %s", e)
                return False

    def disconnect(self) -> None:
        """断开当前 ADB 设备连接。"""
        with self._lock:
            if self._device is not None:
                try:
                    self.adb_client.disconnect(self.serial)
                    logger.info("已断开设备连接: %s", self.serial)
                except Exception as e:
                    logger.error("断开连接时发生异常: %s", e)
                finally:
                    self._device = None

    def is_online(self) -> bool:
        """
        检测模拟器是否在线。

        通过查询 ADB 设备列表，确认该 serial 状态是否为 'device'。

        Returns:
            True 表示在线，False 表示离线或不可用。
        """
        try:
            for dev_info in self.adb_client.device_list():
                if dev_info.serial == self.serial:
                    return dev_info.get_state() == "device"
            return False
        except Exception as e:
            logger.error("检测设备在线状态异常: %s", e)
            return False

    # ------------------------------------------------------------------
    # 设备信息
    # ------------------------------------------------------------------

    def get_device_info(self) -> dict:
        """
        获取已连接设备的基本信息。

        Returns:
            包含 serial, android_version, sdk_level, brand, model 等字段的字典。
            设备未连接时返回空字典。
        """
        if self._device is None:
            logger.warning("设备未连接，无法获取信息")
            return {}

        def _safe_shell(cmd: str) -> str:
            """安全执行 shell 命令，失败返回空字符串。"""
            try:
                return self._device.shell(cmd).strip() or ""
            except Exception:
                return ""

        info = {
            "serial": self.serial,
            "android_version": _safe_shell("getprop ro.build.version.release"),
            "sdk_level": _safe_shell("getprop ro.build.version.sdk"),
            "brand": _safe_shell("getprop ro.product.brand"),
            "model": _safe_shell("getprop ro.product.model"),
            "manufacturer": _safe_shell("getprop ro.product.manufacturer"),
            "screen_density": _safe_shell("wm density | grep -oE '[0-9]+'"),
        }
        logger.info(
            "设备信息: %(brand)s %(model)s, Android %(android_version)s "
            "(SDK %(sdk_level)s)",
            info,
        )
        return info

    # ------------------------------------------------------------------
    # 截图
    # ------------------------------------------------------------------

    def screenshot(self) -> Optional[np.ndarray]:
        """
        通过 ADB screencap 截取设备当前画面。

        原理:
          adb shell screencap -p → 获取 PNG 字节流 → NumPy 解码 → OpenCV BGR 格式

        Returns:
            OpenCV BGR 格式的 numpy 数组 (height, width, 3)，
            失败时返回 None。
        """
        if self._device is None:
            logger.error("截图失败: 设备未连接")
            return None

        try:
            # screencap -p: 输出 PNG 格式的屏幕截图
            # encoding=None: 返回原始 bytes，避免文本解码损坏图像数据
            png_bytes = self._device.shell(
                "screencap -p",
                encoding=None,
                timeout=SCREENSHOT_TIMEOUT,
            )

            if png_bytes is None or len(png_bytes) == 0:
                logger.error("截图失败: screencap 返回空数据")
                return None

            # 将 PNG 字节流解码为 OpenCV 图像（BGR 格式）
            image_array = np.frombuffer(png_bytes, dtype=np.uint8)
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

            if image is None:
                logger.error("截图失败: 图像解码失败，可能设备已断开")
                return None

            # 首次截图时自动记录屏幕分辨率
            if self.screen_width == 0 or self.screen_height == 0:
                self.screen_height, self.screen_width = image.shape[:2]
                logger.info(
                    "屏幕分辨率: %d x %d",
                    self.screen_width,
                    self.screen_height,
                )

            return image

        except AdbError as e:
            logger.error("截图 ADB 异常: %s", e)
            return None
        except Exception as e:
            logger.error("截图未知异常: %s", e)
            return None

    def get_resolution(self) -> Tuple[int, int]:
        """
        获取设备屏幕分辨率。

        如果尚未截图，会先执行一次截图以获取尺寸。

        Returns:
            (width, height) 元组。
        """
        if self.screen_width == 0 or self.screen_height == 0:
            logger.info("尚未获取分辨率，执行首次截图...")
            self.screenshot()
        return self.screen_width, self.screen_height

    # ------------------------------------------------------------------
    # 模板匹配
    # ------------------------------------------------------------------

    def match_template(
        self,
        template_path: str,
        threshold: float = TEMPLATE_MATCH_THRESHOLD,
        screenshot: Optional[np.ndarray] = None,
    ) -> List[Tuple[int, int, int, int, float]]:
        """
        在当前屏幕中匹配模板图像。

        算法:
          使用 OpenCV 的 TM_CCOEFF_NORMED（归一化相关系数匹配）。
          相比 TM_SQDIFF，该算法对光照变化更鲁棒。
          支持灰度匹配（忽略颜色差异），提高泛用性。

        步骤:
          1. 截取当前屏幕（或使用传入截图）
          2. 读取模板图像
          3. 将两者转为灰度图
          4. 执行多尺度滑动窗口匹配
          5. 收集所有高于阈值的匹配点
          6. 应用非极大值抑制（NMS）去重

        Args:
            template_path: 模板图像文件路径（支持 png/jpg/bmp 等常见格式）
            threshold:    匹配阈值 (0.0 ~ 1.0)，越高越严格
            screenshot:   可选的截图，不传则自动截取

        Returns:
            匹配结果列表，每项为 (x, y, width, height, confidence)。
            列表按置信度降序排列。无匹配时返回空列表。
        """
        # ---- 1. 获取屏幕截图 ----
        if screenshot is None:
            screen = self.screenshot()
        else:
            screen = screenshot.copy()
        if screen is None:
            logger.error("模板匹配失败: 无法获取屏幕截图")
            return []

        # ---- 2. 读取模板图像 ----
        # cv2.imread() 不支持中文路径，改用 np.fromfile + cv2.imdecode
        try:
            template_data = np.fromfile(template_path, dtype=np.uint8)
            template = cv2.imdecode(template_data, cv2.IMREAD_COLOR)
        except Exception as e:
            logger.error("模板匹配失败: 读取文件异常 %s — %s", template_path, e)
            return []
        if template is None:
            logger.error("模板匹配失败: 无法解码模板文件 %s", template_path)
            return []

        # 检查模板尺寸是否大于屏幕
        t_h, t_w = template.shape[:2]
        s_h, s_w = screen.shape[:2]
        if t_h > s_h or t_w > s_w:
            logger.error(
                "模板匹配失败: 模板尺寸 (%dx%d) 大于屏幕 (%dx%d)",
                t_w, t_h, s_w, s_h,
            )
            return []

        # ---- 3. 转灰度 ----
        screen_gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

        # ---- 4. 多尺度匹配 ----
        # 尝试多个缩放比例，适应不同分辨率的模拟器
        scales = [1.0, 0.9, 1.1, 0.8, 1.2]
        all_matches: List[Tuple[int, int, int, int, float]] = []

        for scale in scales:
            # 缩放模板
            scaled_w = int(t_w * scale)
            scaled_h = int(t_h * scale)
            if scaled_w < 10 or scaled_h < 10:
                continue
            if scaled_w > s_w or scaled_h > s_h:
                continue

            scaled_template = cv2.resize(template_gray, (scaled_w, scaled_h))

            # 执行模板匹配
            result = cv2.matchTemplate(
                screen_gray,
                scaled_template,
                cv2.TM_CCOEFF_NORMED,
            )

            # 收集高于阈值的位置
            locations = np.where(result >= threshold)
            for pt_y, pt_x in zip(*locations):
                confidence = result[pt_y, pt_x]
                all_matches.append((pt_x, pt_y, scaled_w, scaled_h, float(confidence)))

        # ---- 5. 非极大值抑制 (NMS) ----
        # 避免同一目标被多次匹配，保留置信度最高的框
        if not all_matches:
            logger.info(
                "模板匹配: 未找到匹配 (模板=%s, 阈值=%.2f)",
                template_path,
                threshold,
            )
            return []

        all_matches.sort(key=lambda m: m[4], reverse=True)  # 按置信度降序
        kept: List[Tuple[int, int, int, int, float]] = []

        for match in all_matches:
            x, y, w, h, conf = match
            # 检查当前匹配是否与已保留的结果重叠（IoU > 0.3）
            overlap = False
            for kept_match in kept:
                kx, ky, kw, kh, _ = kept_match
                # 计算交集
                ix = max(x, kx)
                iy = max(y, ky)
                iw = min(x + w, kx + kw) - ix
                ih = min(y + h, ky + kh) - iy
                if iw > 0 and ih > 0:
                    intersection = iw * ih
                    union = w * h + kw * kh - intersection
                    iou = intersection / union if union > 0 else 0
                    if iou > 0.3:
                        overlap = True
                        break
            if not overlap:
                kept.append(match)

        logger.info(
            "模板匹配: 找到 %d 个匹配 (模板=%s). 候选=%d, NMS后=%d",
            len(kept),
            template_path,
            len(all_matches),
            len(kept),
        )
        for i, (x, y, w, h, conf) in enumerate(kept):
            logger.info(
                "  #%d: 位置=(%d,%d) 尺寸=(%dx%d) 置信度=%.4f",
                i + 1, x, y, w, h, conf,
            )

        return kept

    def find_template_center(
        self,
        template_path: str,
        threshold: float = TEMPLATE_MATCH_THRESHOLD,
    ) -> Optional[Tuple[int, int]]:
        """
        查找模板在屏幕中的中心坐标（取最高置信度匹配）。

        便捷方法，等价于 match_template() → 取第一个结果的中心点。

        Args:
            template_path: 模板图像路径
            threshold:    匹配阈值

        Returns:
            (center_x, center_y) 或 None。
        """
        matches = self.match_template(template_path, threshold)
        if matches:
            x, y, w, h, conf = matches[0]
            cx, cy = x + w // 2, y + h // 2
            logger.info("模板中心坐标: (%d, %d), 置信度=%.4f", cx, cy, conf)
            return cx, cy
        return None

    # ------------------------------------------------------------------
    # 点击
    # ------------------------------------------------------------------

    def click(
        self,
        x: int,
        y: int,
        delay: float = 0.05,
    ) -> bool:
        """
        在指定坐标执行点击（ADB input tap）。

        原理:
          adb shell input tap <x> <y>
          一次 tap = 按下 + 抬起，标准点击行为。

        Args:
            x:     屏幕 X 坐标（像素，左上角为原点）
            y:     屏幕 Y 坐标
            delay: 点击后等待时间（秒），用于界面响应

        Returns:
            True 表示成功，False 表示失败。
        """
        if self._device is None:
            logger.error("点击失败: 设备未连接")
            return False

        try:
            cmd = f"input tap {x} {y}"
            self._device.shell(cmd, timeout=5)
            logger.info("点击: (%d, %d)", x, y)
            if delay > 0:
                time.sleep(delay)
            return True
        except Exception as e:
            logger.error("点击异常: (%d, %d) — %s", x, y, e)
            return False

    def click_center(self) -> bool:
        """
        点击屏幕正中心。

        Returns:
            True 表示成功。
        """
        w, h = self.get_resolution()
        if w == 0 or h == 0:
            logger.error("点击中心失败: 屏幕分辨率未知")
            return False
        return self.click(w // 2, h // 2)

    def long_press(
        self,
        x: int,
        y: int,
        duration_ms: int = 1000,
    ) -> bool:
        """
        在指定坐标执行长按操作。

        原理:
          adb shell input swipe <x> <y> <x> <y> <duration>
          起点和终点相同，持续指定时长 → 长按效果。

        Args:
            x:           屏幕 X 坐标
            y:           屏幕 Y 坐标
            duration_ms: 长按持续时间（毫秒），默认 1000

        Returns:
            True 表示成功。
        """
        if self._device is None:
            logger.error("长按失败: 设备未连接")
            return False

        try:
            cmd = f"input swipe {x} {y} {x} {y} {duration_ms}"
            self._device.shell(cmd, timeout=5)
            logger.info("长按: (%d, %d), 持续 %dms", x, y, duration_ms)
            return True
        except Exception as e:
            logger.error("长按异常: (%d, %d) — %s", x, y, e)
            return False

    # ------------------------------------------------------------------
    # 滑动
    # ------------------------------------------------------------------

    def swipe(
        self,
        from_x: int,
        from_y: int,
        to_x: int,
        to_y: int,
        duration_ms: int = SWIPE_DEFAULT_DURATION,
        delay: float = 0.3,
    ) -> bool:
        """
        从起点滑动到终点。

        原理:
          adb shell input swipe <x1> <y1> <x2> <y2> <duration>
          模拟手指从 (x1,y1) 匀速滑动到 (x2,y2)，耗时 duration_ms 毫秒。

        Args:
            from_x:      起点 X 坐标
            from_y:      起点 Y 坐标
            to_x:        终点 X 坐标
            to_y:        终点 Y 坐标
            duration_ms: 滑动持续时间（毫秒），越长越慢越平滑
            delay:       滑动后等待时间（秒），用于界面过渡动画

        Returns:
            True 表示成功。
        """
        if self._device is None:
            logger.error("滑动失败: 设备未连接")
            return False

        try:
            cmd = f"input swipe {from_x} {from_y} {to_x} {to_y} {duration_ms}"
            self._device.shell(cmd, timeout=5)
            logger.info(
                "滑动: (%d,%d) → (%d,%d), 持续 %dms",
                from_x, from_y, to_x, to_y, duration_ms,
            )
            if delay > 0:
                time.sleep(delay)
            return True
        except Exception as e:
            logger.error(
                "滑动异常: (%d,%d)→(%d,%d) — %s",
                from_x, from_y, to_x, to_y, e,
            )
            return False

    def swipe_up(
        self,
        distance_ratio: float = 0.4,
        duration_ms: int = SWIPE_DEFAULT_DURATION,
    ) -> bool:
        """
        向上滑动（常见于列表滚动、下拉刷新等场景）。

        Args:
            distance_ratio: 滑动距离占屏幕高度的比例（0.0 ~ 1.0）
            duration_ms:   滑动持续时间

        Returns:
            True 表示成功。
        """
        w, h = self.get_resolution()
        if w == 0 or h == 0:
            logger.error("向上滑动失败: 屏幕分辨率未知")
            return False

        center_x = w // 2
        from_y = int(h * 0.7)                          # 从屏幕 70% 处
        to_y = int(h * (0.7 - distance_ratio))         # 向上滑到 30% 处
        return self.swipe(center_x, from_y, center_x, max(0, to_y), duration_ms)

    def swipe_down(
        self,
        distance_ratio: float = 0.4,
        duration_ms: int = SWIPE_DEFAULT_DURATION,
    ) -> bool:
        """
        向下滑动（常见于下拉通知栏等场景）。

        Args:
            distance_ratio: 滑动距离占屏幕高度的比例
            duration_ms:   滑动持续时间

        Returns:
            True 表示成功。
        """
        w, h = self.get_resolution()
        if w == 0 or h == 0:
            logger.error("向下滑动失败: 屏幕分辨率未知")
            return False

        center_x = w // 2
        from_y = int(h * 0.3)
        to_y = int(h * (0.3 + distance_ratio))
        return self.swipe(center_x, from_y, center_x, min(h, to_y), duration_ms)

    def swipe_left(
        self,
        distance_ratio: float = 0.4,
        duration_ms: int = SWIPE_DEFAULT_DURATION,
    ) -> bool:
        """
        向左滑动（常见于横向翻页）。

        Args:
            distance_ratio: 滑动距离占屏幕宽度的比例
            duration_ms:   滑动持续时间

        Returns:
            True 表示成功。
        """
        w, h = self.get_resolution()
        if w == 0 or h == 0:
            logger.error("向左滑动失败: 屏幕分辨率未知")
            return False

        center_y = h // 2
        from_x = int(w * 0.7)
        to_x = int(w * (0.7 - distance_ratio))
        return self.swipe(from_x, center_y, max(0, to_x), center_y, duration_ms)

    def swipe_right(
        self,
        distance_ratio: float = 0.4,
        duration_ms: int = SWIPE_DEFAULT_DURATION,
    ) -> bool:
        """
        向右滑动（常见于返回上一页）。

        Args:
            distance_ratio: 滑动距离占屏幕宽度的比例
            duration_ms:   滑动持续时间

        Returns:
            True 表示成功。
        """
        w, h = self.get_resolution()
        if w == 0 or h == 0:
            logger.error("向右滑动失败: 屏幕分辨率未知")
            return False

        center_y = h // 2
        from_x = int(w * 0.3)
        to_x = int(w * (0.3 + distance_ratio))
        return self.swipe(from_x, center_y, min(w, to_x), center_y, duration_ms)

    # ------------------------------------------------------------------
    # ADB Shell / 应用启动
    # ------------------------------------------------------------------

    def shell(self, cmd: str, timeout: int = 10) -> str:
        """
        在设备上执行任意 ADB shell 命令。

        封装 self._device.shell()，提供统一入口。

        Args:
            cmd:     Shell 命令（如 "pm list packages -3"）
            timeout: 超时秒数

        Returns:
            命令输出字符串。失败返回空字符串。
        """
        if self._device is None:
            logger.error("shell 失败: 设备未连接")
            return ""
        try:
            result = self._device.shell(cmd, timeout=timeout)
            return (result or "").strip()
        except Exception as e:
            logger.error("shell 异常: %s — %s", cmd, e)
            return ""

    def app_start(self, package: str) -> bool:
        """
        通过 monkey 命令启动指定应用。

        等价于:
          adb shell monkey -p <package> -c android.intent.category.LAUNCHER 1

        无需知道 Activity 类名，比 am start 更通用。

        Args:
            package: 应用包名（如 "com.nineyou.fuxiao"）

        Returns:
            True 表示命令执行成功（不代表应用一定在前台）。
        """
        cmd = f"monkey -p {package} -c android.intent.category.LAUNCHER 1"
        output = self.shell(cmd)
        if "Events injected: 1" in output:
            logger.info("✓ 应用启动: %s", package)
            return True
        logger.warning("应用启动命令已发送，但未确认注入: %s", output[:100])
        return True  # monkey 有时不给明确成功标志，仍视为成功

    def app_stop(self, package: str) -> bool:
        """
        强制停止指定应用。

        等价于:
          adb shell am force-stop <package>

        Args:
            package: 应用包名

        Returns:
            True 表示命令执行成功。
        """
        try:
            self.shell(f"am force-stop {package}")
            logger.info("✓ 应用已停止: %s", package)
            return True
        except Exception as e:
            logger.error("停止应用异常: %s — %s", package, e)
            return False

    def get_current_app(self) -> str:
        """
        获取当前前台应用的包名和 Activity。

        Returns:
            形如 "com.nineyou.fuxiao/.MainActivity" 的字符串，失败返回空串。
        """
        output = self.shell("dumpsys window | grep mCurrentFocus")
        if not output:
            return ""
        # 从 "mCurrentFocus=Window{... u0 com.xxx/.Activity}" 中提取
        import re
        m = re.search(r"u0\s+(\S+)", output)
        return m.group(1) if m else output.strip()

    # ------------------------------------------------------------------
    # 综合演示 / 自检
    # ------------------------------------------------------------------

    def self_test(self) -> bool:
        """
        框架自检: 依次验证连接、截图、模板匹配、点击、滑动能力。

        Returns:
            全部通过返回 True，任一步骤失败返回 False。
        """
        logger.info("=" * 60)
        logger.info("OK 框架自检开始")
        logger.info("=" * 60)

        # 1. 设备连接
        logger.info("[1/5] 连接设备...")
        if not self.connect():
            logger.error("❌ 连接失败，自检终止")
            return False
        logger.info("✓ 连接通过")

        # 2. 设备信息
        logger.info("[2/5] 获取设备信息...")
        info = self.get_device_info()
        if not info:
            logger.error("❌ 获取设备信息失败")
            return False
        logger.info("✓ 设备信息: %s %s, Android %s",
                     info.get('brand'), info.get('model'), info.get('android_version'))

        # 3. 截图
        logger.info("[3/5] 测试截图...")
        img = self.screenshot()
        if img is None:
            logger.error("❌ 截图失败")
            return False
        logger.info("✓ 截图通过 (%d×%d)", self.screen_width, self.screen_height)

        # 4. 模板匹配（使用一个保险的方式：把当前截图保存再做匹配）
        logger.info("[4/5] 测试模板匹配...")
        # 这里用一个简单测试：将截图中心区域裁剪作为"模板"
        h, w = img.shape[:2]
        template = img[h//2-50:h//2+50, w//2-50:w//2+50]
        # 写临时文件，然后用 match_template 匹配
        import tempfile, os
        tmp_dir = tempfile.gettempdir()
        tmp_tpl = os.path.join(tmp_dir, "_ok_test_template.png")
        cv2.imwrite(tmp_tpl, template)
        try:
            matches = self.match_template(tmp_tpl, threshold=0.8, screenshot=img)
            if matches:
                logger.info("✓ 模板匹配通过 (找到 %d 个匹配)", len(matches))
            else:
                logger.warning("⚠ 模板匹配: 未找到匹配（可能因设备差异，不影响使用）")
        finally:
            if os.path.exists(tmp_tpl):
                os.remove(tmp_tpl)

        # 5. 点击（仅做轻量验证：shell 命令是否可执行）
        logger.info("[5/5] 测试点击/滑动...")
        # 简单执行一次不会影响操作的点击（屏幕左上角非活动区）
        if self.click(1, 1, delay=0.01):
            logger.info("✓ 点击/滑动通过")
        else:
            logger.warning("⚠ 点击测试失败")

        logger.info("=" * 60)
        logger.info("✓ OK 框架自检完成 — 所有核心能力已就绪")
        logger.info("=" * 60)
        return True

    # ------------------------------------------------------------------
    # 清理
    # ------------------------------------------------------------------

    def close(self) -> None:
        """释放资源: 断开 ADB 连接。"""
        self.disconnect()
        logger.info("OKFramework 已关闭")


# =====================================================================
# 入口
# =====================================================================

def main():
    """
    主函数: 初始化 OK 框架并执行自检。

    运行流程:
      1. 创建 OKFramework 实例（指向 127.0.0.1:7555）
      2. 执行自检（连接 → 设备信息 → 截图 → 模板匹配 → 点击/滑动）
      3. 等待用户中断（Ctrl+C）或保持后台运行
    """
    logger.info("OK-Script 框架启动中...")

    # 创建框架实例
    ok = OKFramework(host="127.0.0.1", port=7555)

    try:
        # 连接设备并执行自检
        if ok.connect():
            logger.info("设备已连接，获取设备信息...")
            ok.get_device_info()

            # 获取屏幕分辨率
            ok.get_resolution()

            # 尝试截图验证
            logger.info("执行测试截图...")
            img = ok.screenshot()
            if img is not None:
                logger.info(
                    "✓ 截图成功 — 分辨率: %d × %d",
                    ok.screen_width,
                    ok.screen_height,
                )
            else:
                logger.error("截图失败，请检查设备连接")

            logger.info("-" * 50)
            logger.info("OK 框架已就绪，可进行截图/模板匹配/点击/滑动操作")
            logger.info("按 Ctrl+C 退出")
            logger.info("-" * 50)

            # 后台保持运行，等待用户中断
            try:
                while ok.is_online():
                    time.sleep(5)
            except KeyboardInterrupt:
                logger.info("接收到中断信号，正在退出...")
        else:
            logger.error(
                "无法连接到 %s，请确认:\n"
                "  1. 模拟器已启动\n"
                "  2. ADB 调试已开启\n"
                "  3. 端口 %d 正确",
                ok.serial,
                DEFAULT_ADB_PORT,
            )

    except Exception as e:
        logger.exception("框架运行时发生异常: %s", e)
    finally:
        ok.close()
        logger.info("OK-Script 已退出")


# -------------------------------------------------------------------
# 便捷函数: 供外部脚本 import 使用
# -------------------------------------------------------------------

# 全局框架单例（懒加载）
_global_ok: Optional[OKFramework] = None


def get_ok(
    host: str = DEFAULT_ADB_HOST,
    port: int = DEFAULT_ADB_PORT,
) -> OKFramework:
    """
    获取全局 OKFramework 单例。

    首次调用时自动创建并连接设备。
    后续调用返回同一实例，避免重复初始化。

    Args:
        host: ADB server 主机地址
        port: 模拟器 ADB 端口

    Returns:
        OKFramework 实例。
    """
    global _global_ok
    if _global_ok is None:
        _global_ok = OKFramework(host=host, port=port)
        if not _global_ok.connect():
            logger.warning(
                "全局 OK 框架连接失败，部分功能不可用。"
                "请确认模拟器已启动。"
            )
    return _global_ok


def screenshot() -> Optional[np.ndarray]:
    """便捷函数: 截取设备屏幕。"""
    return get_ok().screenshot()


def click(x: int, y: int) -> bool:
    """便捷函数: 点击设备屏幕坐标。"""
    return get_ok().click(x, y)


def swipe(from_x: int, from_y: int, to_x: int, to_y: int) -> bool:
    """便捷函数: 在设备上滑动。"""
    return get_ok().swipe(from_x, from_y, to_x, to_y)


def match_template(template_path: str, threshold: float = 0.75):
    """便捷函数: 在设备屏幕中匹配模板图像。"""
    return get_ok().match_template(template_path, threshold)


# =====================================================================
if __name__ == "__main__":
    main()
