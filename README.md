# 人脸识别考勤系统

基于 **InsightFace (ArcFace + SCRFD)** 的课堂考勤系统，支持实时人脸检测识别、自动打卡、手动补签、考勤报表导出等功能。使用 **PyQt5** 构建桌面GUI，**SQLAlchemy + SQLite** 持久化数据。

## 功能特性

- **实时人脸识别考勤** — 摄像头实时检测人脸，自动匹配数据库并记录打卡
- **多目标跟踪** — IoU + 投票机制平滑识别结果，消除单帧误识别
- **手动补签** — 教师可从名单中批量选择未打卡学生进行补签，支持搜索过滤
- **学生管理** — 人脸注册（多角度质量加权编码）、增删改查、批量导入
- **课程管理** — 创建课程、设定上课时间，按时段自动判断迟到
- **考勤报表** — 按课程/日期/班级统计出勤率，导出Excel
- **班级筛选** — 按班级过滤人脸库，适配合班上课场景
- **教师/学生登录** — bcrypt密码哈希，角色权限分离

## 技术栈

| 类别 | 技术 |
|------|------|
| 人脸识别 | InsightFace (buffalo_l: SCRFD检测 + ArcFace ResNet50编码) |
| 推理引擎 | ONNX Runtime |
| GUI框架 | PyQt5 (Apple风格自定义样式) |
| 数据库 | SQLite + SQLAlchemy ORM |
| 图像处理 | OpenCV + PIL |
| 数据导出 | openpyxl (Excel) |
| 密码安全 | bcrypt |

## 系统架构

```
face_attendance/
├── main.py                 # 程序入口
├── config.py               # 全局配置（阈值、摄像头、模型等）
├── app_context.py          # 依赖注入容器
├── core/                   # 人脸识别核心
│   ├── face_detector.py    #   人脸检测 (SCRFD)
│   ├── face_encoder.py     #   特征提取 (ArcFace) + 质量评估
│   ├── face_aligner.py     #   人脸对齐
│   └── face_matcher.py     #   人脸比对 + 预计算矩阵
├── database/               # 数据持久化
│   ├── models.py           #   ORM模型 (Student/Course/AttendanceRecord/User)
│   └── db_manager.py       #   数据库管理器
├── services/               # 业务逻辑层
│   ├── attendance_service.py  # 考勤流程（检测→比对→打卡→跟踪）
│   ├── student_service.py     # 学生管理 + 批量注册
│   ├── course_service.py      # 课程管理
│   └── auth_service.py        # 登录认证
├── gui/                    # 图形界面 (Apple风格)
│   ├── main_window.py         # 主窗口（侧边栏导航）
│   ├── attendance_panel.py    # 考勤打卡面板
│   ├── teacher_panel.py       # 教师管理面板（报表/导出）
│   ├── register_dialog.py     # 学生注册对话框
│   ├── makeup_checkin_dialog.py  # 手动补签对话框
│   ├── login_dialog.py        # 登录对话框
│   ├── edit_student_dialog.py # 学生编辑对话框
│   ├── edit_course_dialog.py  # 课程编辑对话框
│   ├── apple_style.py         # Apple设计系统样式
│   └── widgets/               # 自定义控件
└── utils/                  # 工具模块
    ├── camera.py           #   摄像头线程
    ├── excel_exporter.py   #   Excel导出
    ├── security.py         #   密码哈希
    └── preprocessing.py    #   图像预处理 (CLAHE等)
```

## 核心流程

```
摄像头帧 → 人脸检测(SCRFD) → 特征提取(ArcFace 512维)
    → 预计算矩阵比对 → IoU跟踪器 + 投票平滑
    → 去重 + 冷却检查 → 写入考勤记录 → UI更新
```

人脸编码使用 **质量加权平均**：注册时采集多角度照片，通过5点关键点评估姿态质量，过滤非正面/模糊人脸，离群值剔除后加权融合，生成鲁棒模板。

## 快速开始

### 环境要求

- Python 3.10+（推荐 3.12）
- Windows / macOS / Linux
- 摄像头（用于实时考勤）

### 安装

```bash
# 1. 克隆仓库
git clone https://github.com/yourusername/face-attendance-system.git
cd face-attendance-system/face_attendance

# 2. 安装依赖
pip install -r requirements.txt

# 3. 首次运行（InsightFace模型会自动下载到 ~/.insightface/）
python main.py
```

### 快速体验

```bash
# 使用GUI注册几个学生（打开摄像头采集人脸）
python main.py
# → 登录（默认账号: admin / admin123）
# → 学生管理 → 注册学生 → 打开摄像头拍照

# 或者用演示脚本生成测试数据
python demo_setup.py
```

## 数据导入

支持批量导入：将学生照片按 `学号_姓名/` 格式组织，支持 `train/test/val` 子目录结构。

```
班级目录/
├── train/ 或 test/ 或 val/
│   ├── 1_张三/
│   │   ├── 001.jpg
│   │   └── 002.jpg
│   └── 2_李四/
│       └── ...
```

## 配置

`config.py` 中的关键参数：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `FACE_RECOGNITION_TOLERANCE` | 0.55 | 人脸匹配置信阈值 |
| `ATTENDANCE_COOLDOWN` | 10 | 同一学生打卡冷却时间(秒) |
| `LATE_THRESHOLD_MINUTES` | 15 | 迟到判定阈值(分钟) |
| `ATTENDANCE_FRAME_SKIP` | 10 | 每N帧处理一次识别 |
| `FACE_MODEL_NAME` | buffalo_l | InsightFace模型 (高精度) |

## License

MIT License — 详见 [LICENSE](LICENSE) 文件。
