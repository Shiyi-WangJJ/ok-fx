# OK-Script 项目指南

## 项目简介

基于计算机视觉的游戏自动化框架。通过 ADB 截图 + OpenCV 模板匹配，自动操作安卓模拟器/手机。

## 协作约定

- **改完 GUI 相关代码（`ok/gui/`、`launch_gui.py`）才需要重启，不用问。**
- 重启方式：`TaskStop` 停当前进程 → `Bash launch_gui.py run_in_background=true`
- 任务文件在 `src/tasks/` 有热加载，改任务代码不需要重启
- **用户手动关闭窗口不要自动重启！** 只有用户明确要求启动时才启动
- **每次提交代码改动，必须打新 tag 推送发版**（PyAppify 按 tag 判定更新，不打 tag 用户收不到，CI 也不会触发打包）。流程：commit → tag → push
  ```bash
  git tag v1.0.XX && git push origin master && git push origin v1.0.XX
  ```

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
├── pyappify.yml           # PyAppify 打包配置
├── requirements.txt       # 用户运行时依赖
├── requirements-dev.txt   # 开发依赖（mypy, pytest 等）
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
1. GUI → 截图测试 → 截取当前画面（截图自动保存到 `assets/screenshots/`）
2. 用 X-AnyLabeling 标注 → 导出 COCO
3. 放入 `ok_templates/`，更新 `coco_annotations.json`
4. **每次更新标注/截图后必须跑白底**：`python scripts/whiteout_templates.py`
   否则彩色截图直接提交会破坏模板匹配效果

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

## 打包发布

### 概述

使用 **PyAppify** 打包为 Windows 安装程序（`.exe`），通过 GitHub Actions 自动构建，推 `v*` tag 触发。

打包产物分两种：
- `ok-fx-win32-Global-setup.exe`（~420 MB）：完整安装包，包含 Python + 所有依赖，离线可用
- `ok-fx-win32-online-setup.exe`（~4 MB）：在线安装包，首次运行自动下载依赖

安装后体积约 1.2 GB（PySide6 占 ~634 MB，OpenCV ~108 MB，numpy ~49 MB）。

### 触发方式

```bash
git tag v1.0.0 && git push origin v1.0.0
```

### 关键配置文件

**`pyappify.yml`** — PyAppify 打包配置：
```yaml
name: "ok-fx"
uac: true                          # 请求管理员权限
profiles:
  - name: "Global"
    git_url: "https://github.com/Shiyi-WangJJ/ok-fx.git"  # 自动更新源
    main_script: "launch_gui.py"    # 入口脚本
    requires_python: "3.12"         # 嵌入的 Python 版本
    requirements: "requirements.txt"
```

- `git_url` 同时用作自动更新检查地址（启动时检查最新 tag）
- China profile 暂注释（需要 cnb.cool 镜像仓库）
- 启用 China profile 后可打出国内版安装包

**`.github/workflows/build.yml`** — CI 构建流程：
1. Checkout → 安装 Python 3.12 → 装依赖 → 跑测试 → PyAppify 打包 → Release 发布
2. `use_release` 指向上一个稳定 Release，复用 Rust 启动器跳过编译（加速构建）
3. `permissions: contents: write` 必须有（否则无法创建 Release）

### 依赖拆分

- `requirements.txt` — 用户运行时依赖（PyAppify 打包用这个）
- `requirements-dev.txt` — 开发/构建额外依赖（mypy, twine, pytest 等），CI 装这个

### 自动更新原理

PyAppify 打包的 exe 内置 `pyappify` 库，启动时从 `git_url` 检查最新 tag。检测到新版本后自动下载替换，下次启动显示更新日志（`ok/gui/util/pyappify_startup.py`）。

### 常见打包问题

- **pyappify.yml 缺少 main_script / requires_python** → PyAppify 报 `Invalid version format`
- **git_url 指向不存在的仓库** → PyAppify clone 失败 401
- **Release 403** → 缺少 `permissions: contents: write`
- **`dist/*-setup.exe` 找不到文件** → PyAppify 输出在 `pyappify_dist/`，不是 `dist/`
- **Node.js 20 警告** → 加 `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: "true"`
- **use_release 报 zip not found** → 上一个 Release 缺少 `ok-fx-win32.zip`（`files` 要写 `pyappify_dist/*` 而非 `*setup.exe`）

### 日常更新 vs 重新打包

**不需要重新打包的情况**（大多数）：
- 改任务脚本、修 bug、改模板图
- 只需 `git push` + `git tag`，用户重启应用自动拉取

**需要重新打包的情况**：
- `requirements.txt` 新增/变更依赖
- Python 版本要求变化
- 第一次发给新用户

### 截图 & 白底模板工作流

**每次标注后必须处理白底，否则彩色截图直接提交会破坏模板匹配。**

完整流程：
1. GUI → 截图测试 → 截取当前画面 → 截图存入 `assets/screenshots/`（原始彩图）
2. X-AnyLabeling 标注 → 导出 COCO → 覆盖 `ok_templates/coco_annotations.json`
3. **跑白底脚本**：`python scripts/whiteout_templates.py`

脚本逻辑：读取 `assets/screenshots/` 中的彩图 + `coco_annotations.json` 的 bbox，框外填纯白，输出到 `ok_templates/` 覆盖原图。

目录分工：
- `assets/screenshots/` — 原始彩图（`.gitignore`，不提交，留档用）
- `ok_templates/` — 白底模板 + COCO JSON（提交到 git）

⚠️ **Claude 规则：每次 annotations 变更后必须自动跑白底，不需要用户提醒。** 如果 `assets/screenshots/` 缺少源图，检查 `ok_templates/` 里是否有彩图可复用为源图。

### 应用图标

- `ok/gui/icon.ico` — Qt 资源编译进 `resources.py`，窗口标题栏显示
- `icon.ico`（根目录）— PyAppify 打包时嵌入 exe
- 图标路径：`:/icon.ico`（Qt 资源路径，所有引用已统一）

### debug/release 自动切换

`launch_gui.py` 启动时检测 `PYAPPIFY_APP_VERSION` 环境变量：
- 存在（PyAppify 打包后）→ `debug: False`，隐藏开发者工具
- 不存在（本地开发）→ `debug: True`，显示全部面板

### 关于页面

修改 `ok/gui/about/AboutTab.py`：
- 去掉了"其他项目"链接
- 底部加了红字免责声明

### 白底抠图函数

`ok/util/color.py` → `crop_white_outer(image, x1, y1, x2, y2)`：保留原图尺寸，框外全白，框内原样。

## 环境

- 模拟器: MuMuPlayer 12 @ 127.0.0.1:16384
- 游戏: com.nineyou.fuxiao, 分辨率 1920×1080
- 系统: Windows 11
