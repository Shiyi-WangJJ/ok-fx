# ok-fx · 拂晓自动化

基于 [ok-script](https://github.com/ok-oldking/ok-py) 图像识别框架的《拂晓》自动化工具。

通过 ADB 截图 + OpenCV 模板匹配操控安卓模拟器，**不读取游戏内存、不修改游戏文件**。

> 开发者群：938132715

---

## ⚠️ 免责声明

本软件为开源、免费的外部辅助工具，仅供学习与交流使用。完全通过模拟用户界面交互，不修改任何游戏文件或数据。

**拂晓官方严禁使用任何第三方工具**，使用本软件可能面临冻结或封禁账号的风险。使用者需自行承担一切潜在风险。

---

## ✨ 主要功能

| 分类 | 功能 |
|------|------|
| **每日一条龙** | 登录 → 领油 → 出击日常(6卡) → 演习 → 竞技 → 远征 → 倒油 → 任务 → 商店 → 领油 |
| **无尽海域** | 每周 60 关自动推图，自动编队 |
| **弹窗处理** | 自动关闭公告、登录补给、更新确认弹窗 |
| **退役处理** | 船舱满时自动退役 |
| **商店** | 每日礼包、启航包免费购买、贸易商店兑换 |
| **多线路** | 活动 / 主线 (20-10 / 20-5 / 20-1) 双线路倒油 |
| **单步调试** | 支持单独执行某个模块 |

---

## 🖥️ 运行环境

| 项目 | 要求 |
|------|------|
| **操作系统** | Windows |
| **Python** | 3.12 |
| **模拟器** | MuMuPlayer 12 |
| **分辨率** | 1920×1080 (16:9) |
| **游戏** | 拂晓 `com.nineyou.fuxiao` |

---

## 📦 快速开始

1. 安装 [MuMuPlayer 12](https://mumu.163.com/) 模拟器，分辨率设为 1920×1080
2. 在模拟器中安装《拂晓》，确保 ADB 调试已开启
3. 下载安装包（推荐）或从源码运行

### 安装包（推荐）

从 [GitHub Releases](https://github.com/Shiyi-WangJJ/ok-fx/releases) 下载 `ok-fx-win32-Global-setup.exe`，双击安装。

### 从源码运行

```bash
git clone https://github.com/Shiyi-WangJJ/ok-fx.git
cd ok-fx
python -m venv venv
venv\Scripts\pip install -r requirements.txt
```

### 启动

```bash
# GUI 模式
venv\Scripts\python.exe launch_gui.py

# 无头模式
venv\Scripts\python.exe run.py
```

启动后自动连接 MuMu 模拟器 `127.0.0.1:16384`，按 **F9** 启动/停止任务。

---

## ❓ 常见问题

1. 模拟器必须开启 **ADB 调试**，端口默认 `16384`
2. 游戏分辨率必须为 **1920×1080**
3. 软件路径不要含中文字符
4. 任务文件在 `src/tasks/` 下有**热加载**，改代码不需要重启
5. F9 可能被其他程序占用（微信等），可在设置中修改快捷键
6. 模板匹配失败：检查 `ok_templates/` 中的模板图是否为**白底**（非原始截图）

---

## 🛠️ 开发

```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 标注工具推荐 X-AnyLabeling，标注后跑白底
python scripts/whiteout_templates.py
```

项目结构：

```
ok-fx/
├── launch_gui.py           # GUI 入口
├── run.py                  # 无头入口
├── src/tasks/
│   ├── orchestrator.py     # 一条龙编排器
│   └── weekly.py           # 无尽海域 60 关
├── ok/                     # ok-script 框架
├── ok_templates/           # 模板图 + COCO 标注 (110+ 类特征)
├── configs/                # 任务配置文件
└── assets/                 # 原始截图留底
```

---

## 📂 使用 ok-script 的项目

* 鸣潮 [https://github.com/ok-oldking/ok-wuthering-waves](https://github.com/ok-oldking/ok-wuthering-waves)
* 少前2 [https://github.com/ok-oldking/ok-gf2](https://github.com/ok-oldking/ok-gf2)
* 星铁 [https://github.com/Shasnow/ok-starrailassistant](https://github.com/Shasnow/ok-starrailassistant)
* 星痕共鸣 [https://github.com/Sanheiii/ok-star-resonance](https://github.com/Sanheiii/ok-star-resonance)
* 二重螺旋 [https://github.com/BnanZ0/ok-duet-night-abyss](https://github.com/BnanZ0/ok-duet-night-abyss)
* 终末地 [https://github.com/AliceJump/ok-end-field](https://github.com/AliceJump/ok-end-field)
* 异环 [https://github.com/BnanZ0/ok-nte](https://github.com/BnanZ0/ok-nte)
* 鸣潮-okww [https://github.com/See-1e/okww](https://github.com/See-1e/okww)
