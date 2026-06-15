# OK-Script 项目指南

## 项目简介

基于计算机视觉的游戏自动化框架。通过 ADB 截图 + OpenCV 模板匹配，自动操作安卓模拟器/手机。

## 协作约定

- **改完 GUI 相关代码（`ok/gui/`、任务文件）直接重启，不用问。**
- 重启方式：`TaskStop` 停当前进程 → `Bash launch_gui.py run_in_background=true`
- 任务文件在 `src/tasks/` 有热加载，但 GUI 框架代码改完必须重启

## 启动方式

```bash
# GUI 模式（调试，含截图/Overlay/代码运行）
./venv/Scripts/python.exe launch_gui.py

# 无头模式（命令行跑任务）
./venv/Scripts/python.exe run.py              # 全跑
./venv/Scripts/python.exe run.py LoginTask    # 指定任务
```

**注意事项：**
- 用 `run_in_background: true` 启动，方便后续管理进程
- 启动后自动连接 MuMu 模拟器 `127.0.0.1:16384`
- 窗口标题 `ok-fx`，调试模式开启，F9 启动/停止（可能冲突）

## 目录结构

```
ok-script/
├── launch_gui.py          # GUI 入口（debug=True, use_gui=True）
├── run.py                 # 无头入口（headless）
├── ok/                    # 框架核心
│   ├── __init__.py         # OK 类、App 类、OK 初始化
│   ├── cli.py              # CLI 入口
│   ├── task/task.py        # BaseTask — find_one/find_feature/swipe/click
│   ├── feature/            # FeatureSet — 模板匹配引擎
│   ├── device/             # DeviceManager — ADB 连接/截图/交互
│   └── gui/                # PySide6 + QFluentWidgets GUI
├── src/tasks/              # 任务脚本（用户开发）
│   ├── login.py            # 1. 登录游戏
│   ├── oil.py              # 2. 领油
│   ├── daily.py            # 3. 出击-日常
│   ├── exercise.py         # 4. 出击-演习
│   ├── arena.py            # 5. 出击-竞技
│   ├── event.py            # 6. 活动
│   ├── expedition.py       # 7. 远征
│   ├── mission.py          # 8. 任务
│   ├── match_test.py       # 匹配测试
│   └── popups.py           # 弹窗处理（TriggerTask，后台常驻）
├── ok_templates/           # 模板图片 + COCO 标注
│   ├── coco_annotations.json  # 所有特征定义（类别+bbox）
│   └── *.png               # 29 张 1920×1080 标注截图
└── configs/                # 任务配置文件（JSON）
```

## 任务开发约定

### 文件模板
```python
class XxxTask(BaseTask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "序号. 名称"
        self.description = "描述"
        self.sleep_check_interval = 0.5

    def sleep_check(self):
        for name in ["点击继续"]:
            box = self.find_one(name)
            if box:
                self.click_box(box)
                return

    def run(self):
        # 步骤逻辑
        ...
```

### 核心 API

**匹配查找：**
- `self.find_one(name)` → 返回匹配度最高的 Box 或 None（找不到抛 ValueError）
- `self.find_one(name, threshold=0.6)` → 降低阈值
- `self.find_feature(feature_name=["A", "B"], limit=1)` → 支持列表，多模板一起搜
- `self.find_one(name, use_gray_scale=True)` → 灰度匹配（文字可用，但实测效果有限）
- `self.find_one(name, canny_lower=50, canny_higher=150)` → Canny 边缘匹配

**交互：**
- `og.device_manager.shell(f"input tap {x} {y}")` → 直接 ADB 点击
- `self.click_box(box)` → 点击 Box 中心
- `self.swipe_relative(0.5, 0.7, 0.5, 0.4)` → 相对坐标滑动
- `self.sleep(seconds)`

**Poll 模式（循环检测 + 超时）：**
```python
def _poll_and_tap(self, name, timeout=10):
    for _ in range(int(timeout / 0.2)):
        try:
            box = self.find_one(name)
            if box:
                click...
                return True
        except ValueError:
            pass
        self.sleep(0.2)
    return False
```

### 注册新任务
在 `launch_gui.py` 和 `run.py` 的 `onetime_tasks` 列表中加入：
```python
["src.tasks.xxx", "XxxTask"],
```

### 添加新标注
1. GUI → 截图测试 → 截取当前画面
2. 用 X-AnyLabeling 标注 → 导出 COCO
3. 放入 `ok_templates/`，更新 `coco_annotations.json`

## 模板匹配参数

`launch_gui.py` 中的默认值：
- `default_threshold`: 0.70
- `default_horizontal_variance`: 0.002（≈4px @1920）
- `default_vertical_variance`: 0.002（≈2px @1080）
- 匹配方法: `cv2.TM_CCOEFF_NORMED`
- 默认不转灰度、不用 Canny

## 已知问题

- Python 3.13（venv），项目要求 3.12，目前运行正常但非官方支持
- F9 快捷键注册失败（被其他程序占用）
- `launch_gui.py` 没有 `if __name__ == "__main__"` 守卫，直接执行
- 翻译文件 `zh_CN` 安装有警告，不影响使用
- 小文字模板（如 81×31 的"12小时"）背景变化时匹配不稳定，需要多模板兜底

## 环境

- 模拟器: MuMuPlayer 12 @ 127.0.0.1:16384
- 游戏: com.nineyou.fuxiao, 分辨率 1920×1080
- 系统: Windows 11
