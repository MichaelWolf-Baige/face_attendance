# 人脸识别考勤系统

基于 **InsightFace (ArcFace + SCRFD)** 的课堂考勤系统。支持实时人脸检测识别、自动打卡、手动补签、考勤报表导出。

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

## 功能特性

- **实时人脸识别考勤** — 摄像头实时检测人脸，自动匹配数据库并记录打卡
- **多目标跟踪** — IoU + 投票机制平滑识别结果，消除单帧误识别
- **手动补签** — 教师可从名单中批量选择未打卡学生进行补签，支持搜索过滤
- **学生管理** — 人脸注册（多角度质量加权编码）、增删改查、批量导入
- **课程管理** — 创建课程、设定上课时间，按时段自动判断迟到
- **考勤报表** — 按课程/日期/班级统计出勤率，导出 Excel
- **班级筛选** — 按班级过滤人脸库，适配合班上课场景
- **教师/学生登录** — bcrypt 密码哈希，角色权限分离

## 技术栈

| 类别 | 技术 |
|------|------|
| 人脸识别 | InsightFace (buffalo_l: SCRFD 检测 + ArcFace ResNet50 编码) |
| 推理引擎 | ONNX Runtime |
| GUI 框架 | PyQt5 |
| 数据库 | SQLite + SQLAlchemy ORM |
| 图像处理 | OpenCV + PIL |
| 数据导出 | openpyxl (Excel) |
| 密码安全 | bcrypt |

## 快速开始

### 环境要求

- **Python 3.10 或更高版本**（推荐 3.12）
- Windows / macOS / Linux 均可
- 摄像头（用于实时考勤，非必须——无摄像头也能用管理功能）

### 三步启动

**第一步：克隆代码**

```bash
git clone https://github.com/MichaelWolf-Baige/face_attendance.git
cd face_attendance/face_attendance
```

**第二步：安装依赖**

Windows 用户双击运行 `setup_env.bat`，Mac/Linux 用户运行：

```bash
chmod +x setup_env.sh && ./setup_env.sh
```

或者手动安装：

```bash
pip install -r requirements.txt
```

国内用户如安装速度慢，建议用清华镜像：

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

**第三步：启动**

```bash
python main.py
```

或 Windows 直接双击 `start.bat`。

首次启动 InsightFace 会自动下载模型文件（约 200MB），放在 `~/.insightface/` 目录，仅需下载一次。

### 登录

默认管理员账号：**`admin`** / **`admin123`**

---

## 安装常见问题

### Q: 提示 `Unable to import dependency onnxruntime`

```bash
pip install onnxruntime insightface
```

如果还不行，**不要用 Python 3.13**（onnxruntime 目前不兼容 Python 3.13），改用 Python 3.10-3.12。

### Q: pip 安装报错 / 速度极慢

国内网络用清华镜像：

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Q: 启动后摄像头黑屏

- Windows：检查系统"隐私设置 → 摄像头"是否允许桌面应用访问
- 多摄像头：编辑 `config.py` 改 `CAMERA_INDEX`（0 → 1 或 2）
- Linux 虚拟机：检查 USB 设备是否已透传

### Q: 人脸识别不到

- 确保光线充足，人脸正对摄像头
- 先在"学生管理"里注册人脸
- 检查 `config.py` 中 `FACE_RECOGNITION_TOLERANCE`（默认 0.55，越低越宽松）

### Q: 退出登录后界面卡住（已知的 PyQt bug）

直接关闭窗口，重新运行 `python main.py` 即可。

---

## 使用流程

### 学生人脸注册

1. 登录 → 左侧导航"学生管理" → "注册学生"
2. 填写学号、姓名、班级
3. 打开摄像头，点击"拍照"捕捉 3-5 张不同角度的人脸
4. 确认注册

### 考勤打卡

1. 左侧导航"考勤打卡"
2. 选择课程和班级
3. 点击"开始考勤"
4. 学生面向摄像头，系统自动识别并记录
5. 右侧实时显示今日考勤统计

### 手动补签（人脸识别漏掉时）

1. 考勤面板点击"手动补签"
2. 对话框列出今日未打卡学生
3. 搜索框输入学号或姓名快速定位
4. 勾选学生 → 选择状态（正常/迟到）→ 确认

### 导出报表

1. 左侧导航"教师管理" → "考勤记录"
2. 筛选课程和日期
3. 点击"导出 Excel"

---

## 系统架构

```
face_attendance/
├── main.py                 # 程序入口
├── config.py               # 全局配置
├── app_context.py          # 依赖注入容器
├── core/                   # 人脸识别核心
│   ├── face_detector.py    #   SCRFD 人脸检测
│   ├── face_encoder.py     #   ArcFace 特征提取 + 质量评估
│   ├── face_aligner.py     #   人脸对齐
│   └── face_matcher.py     #   预计算矩阵比对
├── database/
│   ├── models.py           #   ORM 模型
│   └── db_manager.py       #   数据库管理器
├── services/               # 业务逻辑层
│   ├── attendance_service.py  # 考勤流程 + 跟踪器
│   ├── student_service.py     # 学生管理 + 批量注册
│   ├── course_service.py      # 课程管理
│   └── auth_service.py        # 登录认证
├── gui/                    # PyQt5 图形界面
│   ├── main_window.py         # 主窗口（侧边栏导航）
│   ├── attendance_panel.py    # 考勤打卡面板
│   ├── teacher_panel.py       # 教师管理面板（报表/导出）
│   ├── register_dialog.py     # 学生注册对话框
│   ├── makeup_checkin_dialog.py  # 手动补签对话框
│   ├── login_dialog.py        # 登录对话框
│   ├── apple_style.py         # Apple 设计系统样式
│   └── widgets/               # 自定义控件
└── utils/                  # 工具模块
    ├── camera.py           #   摄像头线程
    ├── excel_exporter.py   #   Excel 导出
    ├── security.py         #   密码哈希
    └── preprocessing.py    #   图像预处理
```

## 核心流程

```
摄像头帧 → SCRFD 人脸检测 → ArcFace 512维特征提取
    → 预计算矩阵批量比对 → IoU 跟踪器 + 投票平滑去误识别
    → 冷却去重 → 迟到判定 → 写入考勤记录 → UI 实时更新
```

人脸编码使用**质量加权平均**：注册时采集多角度照片，通过 5 点关键点评估姿态质量，过滤非正面/模糊人脸，离群值剔除后加权融合。

## 配置参考

`config.py` 中的关键参数：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `FACE_RECOGNITION_TOLERANCE` | 0.55 | 人脸匹配置信阈值（降低=更宽松） |
| `ATTENDANCE_COOLDOWN` | 10 | 同一学生打卡冷却时间(秒) |
| `LATE_THRESHOLD_MINUTES` | 15 | 上课后多少分钟算迟到 |
| `ATTENDANCE_FRAME_SKIP` | 10 | 每 N 帧做一次识别 |
| `FACE_MODEL_NAME` | buffalo_l | InsightFace 模型（高精度） |
| `CAMERA_INDEX` | 0 | 摄像头编号（多摄像头时修改） |

## License

MIT License — 详见 [LICENSE](LICENSE)
