# 人脸识别考勤系统 —— 完整架构文档

---

# 第一层：`config.py` —— 整个系统的大脑

这是整个项目最先应该理解的模块。它不是"一个配置文件"，而是**系统所有决策的唯一来源**。后面每一层模块的行为，追根溯源都能回到这里。

## 第一行：`BASE_DIR`

```python
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
```

这一行的意思是：**无论从哪个目录执行程序，BASE_DIR 永远指向 `config.py` 所在的目录**，也就是 `face_attendance/` 文件夹。

所有其他路径（数据库路径、数据目录）都基于它计算，不存在相对路径的坑。

## 第一组：数据库路径

```python
DATABASE_PATH = os.path.join(BASE_DIR, 'face_attendance.db')
```

就一行。告诉系统 SQLite 数据库文件放在哪：`face_attendance/face_attendance.db`。

## 第二组：人脸识别参数（核心中的核心）

```python
FACE_RECOGNITION_TOLERANCE = 0.5
```

**这是整个识别系统最重要的数字。** 它的含义是：两张脸的 128 维特征向量之间的欧氏距离如果 ≤ 0.5，就判定为同一个人。从 0.6 改成 0.5，意味着更严格——更不容易误认，但也更容易认不出。

```python
FACE_DETECTION_MODEL = 'cnn'
FACE_DETECTION_RESIZE_SCALE = 0.5
FACE_ENCODING_NUM_JITTERS = 3
```

这三行是**非混合模式下的默认值**。但注意——下面马上有一个开关把它们覆盖了。

## 第三组：混合策略（整个系统最精妙的设计决策）

```python
FACE_USE_HYBRID_MODE = True        # 开关：开启混合策略
FACE_REGISTRATION_MODEL = 'cnn'    # 注册时：CNN 模型（高精度）
FACE_ATTENDANCE_MODEL = 'hog'      # 考勤时：HOG 模型（高速度）
FACE_REGISTRATION_JITTERS = 5      # 注册时：采样 5 次取平均
FACE_ATTENDANCE_JITTERS = 1        # 考勤时：只采样 1 次
```

**为什么这样设计？** 因为两个场景的需求完全不同：

| | 注册学生 | 实时考勤 |
|---|---|---|
| 场景 | 一次性操作，管理员在等 | 每帧都要跑，30fps |
| 核心需求 | **越准越好** | **越快越好** |
| 模型 | CNN（深度学习，慢但准） | HOG（传统算法，快但稍糙） |
| 采样次数 | 5 次取平均（特征更稳定） | 1 次（不耽误时间） |

**但是**——匹配阈值 0.5 是共享的。注册时提取的高质量特征存进数据库，考勤时用低质量特征去匹配高质量库特征——这个不对称设计让速度和精度兼得。

## 第四组：摄像头

```python
CAMERA_INDEX = 0
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 30
```

默认打开第 0 号摄像头（笔记本自带那个），分辨率 640×480，帧率 30。这些值会被 `utils/camera.py` 读取。

## 第五组：考勤业务规则

```python
ATTENDANCE_COOLDOWN = 10         # 秒
LATE_THRESHOLD_MINUTES = 15      # 分钟
```

- **10 秒冷却**：同一个学生打完卡后，10 秒内再次识别到不会重复打卡。防止一个人在摄像头前站着不动，系统疯狂写入。
- **15 分钟迟到**：如果当前时间比课程开始时间晚 15 分钟以上，打卡状态标记为 `late` 而不是 `normal`。

## 第六组：GUI 和日志

```python
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
THEME_COLOR = '#2196F3'
REFRESH_INTERVAL_MS = 5000
LOG_LEVEL = 'INFO'
```

窗口默认大小 1200×800，Material Design 蓝色主题，考勤记录每 5 秒自动刷新。

## 小结

```
config.py = 47 行 = 7 组参数

路径     → BASE_DIR, DATABASE_PATH
识别     → 阈值0.5, 缩放0.5, jitters=3 (默认值)
混合策略 → CNN(注册) vs HOG(考勤), 5次采样 vs 1次采样
摄像头   → 640×480, 30fps
业务规则 → 10秒冷却, 15分钟迟到
界面     → 1200×800, 蓝色主题, 5秒刷新
日志     → INFO 级别
```

**关键思想：注册求准，考勤求快。所有模块的行为差异都源于 `FACE_USE_HYBRID_MODE = True` 这一个开关。**

---

# 第二层：`database/` —— 数据骨架

这一层由两个文件组成：`models.py`（定义表结构）和 `db_manager.py`（所有数据操作）。

## 四张表的 ER 关系

```
    Student                    AttendanceRecord               Course
   ┌──────────────┐           ┌──────────────────┐        ┌──────────────┐
   │ id (PK)      │←─────────│ student_id (FK)  │        │ id (PK)      │
   │ student_id   │           │ course_id (FK)   │────────│ course_code  │
   │ name         │           │ check_time       │        │ course_name  │
   │ class_name   │           │ status           │        │ teacher_name │
   │ face_encoding│           │ confidence       │        │ start_time   │
   │ face_img_path│           │ remark           │        │ end_time     │
   └──────────────┘           └──────────────────┘        └──────────────┘

    User (独立表，不参与业务关联)
   ┌──────────────┐
   │ id (PK)      │
   │ username     │
   │ password_hash│
   │ role         │
   └──────────────┘
```

**关系一句话**：Student 和 Course 各自独立存在，AttendanceRecord 是它们的**多对多桥接表**——一个学生可以在多门课打卡，一门课可以有多个学生的打卡记录。User 表完全独立，只负责登录。

## 最关键的数据设计——人脸怎么存？

```python
# Student 表里这一列最关键：
face_encoding = Column(LargeBinary)
```

人脸识别库 `face_recognition` 提取出来的是一个 **128 维 float64 的 numpy 数组**。

这个东西不能直接存进数据库。于是 `db_manager.py` 顶部有两个转换函数：

```python
def encoding_to_blob(encoding):    # numpy数组 → 字节流（写入数据库）
    return encoding.tobytes()       # 128 × 8 = 1024 字节

def blob_to_encoding(blob):        # 字节流 → numpy数组（从数据库读出）
    return np.frombuffer(blob, dtype=np.float64)
```

**每张人脸在数据库里就是 1024 字节的二进制数据。** 后面的 `get_all_face_encodings()` 方法会把整个学生表的人脸全部加载到内存中，供实时匹配用。

## DatabaseManager 的上下文管理器——安全的壳

整个 `db_manager.py` 的核心模式就是这个：

```python
@contextmanager
def get_session(self):
    session = self.Session()
    try:
        yield session        # ← 业务代码在这里执行
        session.commit()     # ← 业务不出错就提交
    except Exception:
        session.rollback()   # ← 出任何错就回滚
        raise
    finally:
        session.close()      # ← 无论如何都会关闭连接
```

然后**每一个业务方法**都套在这个壳里：

```python
def get_student(self, student_id):
    with self.get_session() as session:      # ← 这行就是"进壳"
        student = session.query(Student)...  # ← 业务逻辑
        return {...}                         # ← 自动 commit/close
```

这保证了三件事：
1. **不会忘记关连接**（finally 保证）
2. **出错自动回滚**（rollback 保证）
3. **不会出现"提交了一半"的脏数据**（commit 在 try 末尾）

## 关键查询方法

**获取所有人脸特征（考勤匹配的核心查询）：**

```python
def get_all_face_encodings(self):
    with self.get_session() as session:
        students = session.query(Student).filter(
            Student.face_encoding.isnot(None)   # 只查已注册人脸的学生
        ).all()

        encodings = []
        names = []
        student_ids = []

        for s in students:
            encoding = blob_to_encoding(s.face_encoding)  # BLOB还原为numpy数组
            if encoding is not None:
                encodings.append(encoding)
                names.append(s.name)
                student_ids.append(s.student_id)

        return encodings, names, student_ids
```

返回**三个平行的列表**：特征数组列表、姓名列表、学号列表。它们的索引是一一对应的——`encodings[0]` 就是 `names[0]` 这个人的人脸。FaceMatcher 匹配时就是靠这个索引找到姓名和学号。

**多表联查考勤记录：**

```python
query = session.query(AttendanceRecord, Student, Course).join(
    Student, ...         # 内连接：必须有学生
).outerjoin(
    Course, ...          # 外连接：课程可以为空
)
```

考勤记录 JOIN 学生（内连接，因为每条打卡必有学生），LEFT JOIN 课程（外连接，因为打卡可以不指定课程）。这样一条 SQL 就查出"谁在什么课什么时间打了卡、什么状态"。

**检查今日是否已打卡：**

```python
def check_today_attendance(self, student_id, course_id=None):
    # 查询今天 00:00:00 ~ 23:59:59 之间有没有记录
    start = datetime.combine(today, datetime.min.time())  # 00:00:00
    end   = datetime.combine(today, datetime.max.time())  # 23:59:59
    return query.first() is not None  # 有一条就算打过
```

## 小结

```
database/
├── models.py       ← 4张ORM表定义，纯粹的"数据长什么样"
└── db_manager.py   ← 所有CRUD操作，统一的"安全壳"模式

核心设计点：
1. 人脸特征 = numpy数组 ↔ BLOB 互转（1024字节一张脸）
2. get_session() 上下文管理器 → 永不泄漏连接 + 自动回滚
3. get_all_face_encodings() → 三个平行列表，索引对应
4. AttendanceRecord 是 Student 和 Course 的多对多桥接
5. User 表独立，只做登录认证
```

---

# 第三层：`core/` —— 人脸识别三件套

这一层**不碰数据库、不碰界面、不碰摄像头**。它只做一件事：接收 numpy 图像数组，输出识别结果。纯粹的算法管道。

三个文件形成一条流水线：

```
摄像头帧 (BGR numpy数组)
    │
    ▼
FaceDetector.detect()      找脸：图像 → 人脸坐标列表
    │
    ▼
FaceEncoder.encode()       编码：图像 + 人脸坐标 → 128维特征向量
    │
    ▼
FaceMatcher.match()        匹配：特征向量 + 已知人脸库 → 姓名 + 置信度
```

## FaceDetector —— 找脸

**输入**：一张 BGR 格式的 numpy 图像（OpenCV 摄像头直接给的格式）

**输出**：人脸位置列表，每个位置是 `(top, right, bottom, left)`

```python
class FaceDetector:
    def __init__(self, model='hog'):
        self.model = model            # 'hog' 快 或 'cnn' 准
        self.resize_scale = 0.5       # 先把图缩小到50%，速度翻倍

    def detect(self, image):
        # 1. 把图像缩小到50%（640×480 → 320×240）
        small = cv2.resize(image, fx=0.5, fy=0.5)

        # 2. BGR转RGB（OpenCV用BGR，face_recognition库用RGB）
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

        # 3. 调库检测人脸
        face_locations = face_recognition.face_locations(rgb, model=self.model)
        #    返回：[(top, right, bottom, left), ...]

        # 4. 坐标放大回原始尺寸
        return scaled_locations
```

**关键细节**：先缩小再检测。`resize_scale = 0.5` 意味着 640×480 的图先变成 320×240，面积是原来的 1/4，HOG 模型在这个尺寸上跑速度够快。检测出来的坐标再 ×2 映射回原图。

**两个模型的选择逻辑**不在这个类里——它在 services 层。`FaceDetector(model='cnn')` 给注册用，`FaceDetector(model='hog')` 给考勤用。这个类本身不管场景，只管"给你什么模型就用什么模型"。

## FaceEncoder —— 编码

**输入**：图像 + 一个人脸位置坐标

**输出**：128 维 float64 的 numpy 数组（人脸特征向量）

```python
class FaceEncoder:
    def __init__(self, num_jitters=1):
        self.num_jitters = num_jitters   # 采样次数：1=快, 5=准

    def encode(self, image, face_location):
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        encodings = face_recognition.face_encodings(
            rgb,
            known_face_locations=[face_location],
            num_jitters=self.num_jitters     # ← 关键参数
        )
        return encodings[0]  # 128维向量
```

**`num_jitters` 是什么？** 这是整个识别精度的关键：

- `num_jitters=1`：对人脸区域做 1 次采样，生成 1 个 128 维向量。快。
- `num_jitters=5`：对人脸区域做 5 次微小的随机扰动（偏移、旋转），生成 5 个 128 维向量，然后**取平均值**。这个平均值比单次采样稳定得多——脸上一点阴影、一点角度变化不容易影响结果。代价是慢 5 倍。

回到第一层 config 的设计：**注册用 5 次采样，考勤用 1 次采样**。这里就是那个设计决策的落地之处。

## FaceMatcher —— 匹配

**输入**：一个待识别的人脸特征向量 + 已知人脸库（N 个特征向量 + N 个姓名）

**输出**：`(姓名, 置信度)` 或 `(None, 0.0)`

```python
class FaceMatcher:
    def __init__(self, tolerance=0.5):
        self.tolerance = 0.5    # 阈值，来自 config

    def match(self, face_encoding, known_encodings, known_names):
        # 1. 计算待识别向量与库中每一个向量的欧氏距离
        distances = face_recognition.face_distance(known_encodings, face_encoding)
        #    → [0.23, 0.85, 0.41, 0.67, ...]  每个已知人脸一个距离值

        # 2. 找到距离最小的那个（最像的）
        min_index = np.argmin(distances)      # 比如 index=0，距离0.23
        min_distance = distances[min_index]

        # 3. 距离 ≤ 0.5 → 匹配成功；距离 > 0.5 → 陌生人
        if min_distance <= self.tolerance:
            return known_names[min_index], 1.0 - min_distance  # ("张三", 0.77)
        else:
            return None, 1.0 - min_distance                   # (None, 0.35)
```

**这段逻辑的核心直觉**：

```
距离 = 0.0   →   完全一样（同一个人的同一张照片）
距离 = 0.3   →   很像，大概率同一个人
距离 = 0.5   →   阈值线，以下算匹配、以上算陌生人
距离 = 0.8   →   不像，大概率不是一个人
距离 = 1.0   →   完全不像
```

**置信度 = 1.0 - 距离**。距离 0.3 → 置信度 70%；距离 0.8 → 置信度 20%。

## 三个类之间的关系

```
┌─────────────────────────────────────────────────────────┐
│                    core/ 算法管道                         │
│                                                         │
│  FaceDetector         FaceEncoder         FaceMatcher   │
│  ┌──────────┐        ┌──────────┐        ┌──────────┐  │
│  │ model    │        │ jitters  │        │tolerance │  │
│  │ = hog    │        │ = 1 or 5 │        │ = 0.5    │  │
│  │ or cnn   │        │          │        │          │  │
│  └────┬─────┘        └────┬─────┘        └────┬─────┘  │
│       │                   │                   │         │
│  BGR  │  [(t,r,b,l)]     │  128维向量        │  姓名    │
│  ────→│──────────────────→│──────────────────→│────────→│
│  图像 │  人脸坐标          │  特征向量          │  置信度  │
│       │                   │                   │         │
│  配置来源：               │                   │         │
│  config.FACE_ATTENDANCE   │ config.FACE_      │ config. │
│  _MODEL / _REGISTRATION   │ ATTENDANCE_JITTERS│ FACE_   │
│  _MODEL                   │ / _REGISTRATION_  │ RECOGNITION
│                           │ JITTERS           │ _TOLERANCE
└─────────────────────────────────────────────────────────┘
```

**这三个类没有互相调用**。它们各自独立，靠 services 层来串联。每个类都接受 config 参数作为默认值，但也可以在构造时覆盖——这给了 services 层最大的灵活性。

## 小结

```
core/
├── face_detector.py   → "图里有几张脸？在哪？"
├── face_encoder.py    → "这张脸的128维数学特征是什么？"
└── face_matcher.py    → "这张脸是数据库里的谁？多像？"

设计原则：
- 纯函数式：输入 numpy 数组，输出 Python 数据结构
- 零依赖：不 import 数据库、不 import GUI
- 参数可注入：构造函数接受覆盖值，不硬编码
- 混合策略不在此层判断——它只提供能力，由 services 层决定用哪种配置
```

---

# 第四层：`services/` —— 业务中枢

这一层是**编排者**，不做算法也不写数据库，而是把 `core/` 的能力和 `database/` 的存储串联成完整业务流程。

## AuthService + SessionManager —— 登录守卫

```
用户输入 admin / admin123
        │
        ▼
AuthService.verify_password("admin123", "$2b$12$...哈希值...")
        │
        ├── 匹配 → SessionManager.login(user)  → current_user 被赋值
        │
        └── 不匹配 → 返回 None，登录失败
```

**bcrypt 的关键特性**：同样的密码 `admin123`，两次哈希出来的结果**不一样**（因为盐不同）。所以不能直接比字符串，必须用 `bcrypt.checkpw()` 比。

`SessionManager` 是一个**全局单例**（文件底部直接 `session_manager = SessionManager()`），整个程序任何地方 `from services.auth_service import session_manager` 拿到的都是同一个实例。`main.py` 的登录循环就是靠它判断是退出登录还是退出程序：

```python
# main.py 的循环逻辑
session_manager.current_user is None  → 退出登录，回到登录框
session_manager.current_user is not None → 用户直接关了窗口，退出程序
```

## StudentService —— 学生注册

业务流很简单，看 `register_student()` 这个核心方法：

```
输入：学号 + 姓名 + 一张照片
        │
        ▼
    学号重复检查（db.get_student）
        │ 已存在 → return False, "学号已存在"
        ▼
    FaceDetector.detect(img)           ← 用 CNN 模型（注册模式）
        │ 0张脸 → return "未检测到人脸"
        │ >1张脸 → return "检测到多张人脸"
        ▼
    FaceEncoder.encode(img, location)  ← num_jitters=5（注册模式）
        │ 失败 → return "特征提取失败"
        ▼
    db.add_student(...)
        │
        ▼
    return True, "注册成功"
```

**关键：注册时的两步验证**
1. 必须检测到**恰好一张脸**——没脸不行，多张脸也不行
2. 特征提取必须成功——脸太糊、角度太偏都会失败

这样保证了**存进数据库的都是高质量人脸特征**。如果注册时就随便放进去，考勤时的匹配会大量失败。宁可注册时严格，不可考勤时抓瞎。

## AttendanceService —— 最核心的业务（重点讲）

这是整个系统里最复杂的类，考勤全流程都在这里。

### 初始化时的混合策略落地

```python
class AttendanceService:
    def __init__(self, db_manager):
        if config.FACE_USE_HYBRID_MODE:               # config 开关 = True
            self.detector = FaceDetector(model='hog')  # ← 考勤用HOG
            self.encoder  = FaceEncoder(num_jitters=1) # ← 考勤用1次采样
```

对比一下 StudentService 初始化：
```python
# StudentService 注册时
self.detector = FaceDetector(model='cnn')   # 注册用CNN
self.encoder  = FaceEncoder(num_jitters=5)  # 注册用5次采样
```

**同一个 config 开关，两条不同路径**——这就是第一层说的"注册求准、考勤求快"的实际落地点。

### 人脸库缓存机制

每次识别都要和全库比对，如果每次都查数据库太慢了。所以 AttendanceService 在内存里做了缓存：

```python
self._face_encodings   = []   # 所有学生的人脸特征
self._face_names       = []   # 对应姓名
self._face_student_ids = []   # 对应学号
self._last_cache_time  = 0
self._cache_ttl        = 60   # 60秒过期

def refresh_face_database(self):
    with self._cache_lock:           # 线程锁保护
        encodings, names, ids = self.db.get_all_face_encodings()
        self._face_encodings = encodings
        self._face_names = names
        self._face_student_ids = ids
        self._last_cache_time = time.time()
```

**缓存逻辑**：
- 第一次识别 → 查数据库，加载所有人脸到内存
- 接下来 60 秒内的识别 → 直接用内存缓存
- 60 秒后 → 重新查数据库刷新

这意味着**新注册的学生最多 60 秒后就能被识别到**，不需要重启程序。

### 核心方法：process_frame()

这是**每一帧图像的处理流程**：

```python
def process_frame(self, frame, course_id):
    # 1. 检查缓存是否过期
    self._check_cache()

    # 2. 检测人脸
    face_locations = self.detector.detect(frame)    # HOG模型，快

    # 3. 提取特征
    face_encodings = self.encoder.encode_faces(frame, face_locations)  # jitters=1

    # 4. 从缓存获取人脸库（加锁保护）
    with self._cache_lock:
        known_encodings = list(self._face_encodings)
        known_names     = list(self._face_names)
        known_ids       = list(self._face_student_ids)

    # 5. 逐个匹配
    for encoding in face_encodings:
        name, confidence = self.matcher.match(
            encoding, known_encodings, known_names
        )
        # 找到对应学号
        idx = known_names.index(name)
        student_id = known_ids[idx]

        results.append({
            'name': name,
            'student_id': student_id,
            'confidence': confidence,
            'bbox': (left, top, width, height)
        })

    return results
```

### 打卡方法：check_in()

`process_frame` 只负责"这是谁"，`check_in` 负责"能不能打卡"：

```python
def check_in(self, student_id, course_id, confidence):
    # 1. 冷却检查（加锁）
    with self._cooldown_lock:
        if time.time() - last_check[student_id] < 10:     # config 的10秒
            return False, 'cooldown', "请等待X秒"

    # 2. 今日重复检查
    if db.check_today_attendance(student['id'], course_id):
        return False, 'duplicate', "今天已打卡"

    # 3. 判断是否迟到
    now = datetime.now()
    课程开始时间 = course['start_time']  # 如 "08:00"
    if now > 课程开始时间 + 15分钟:       # config 的15分钟
        status = 'late'
    else:
        status = 'normal'

    # 4. 写入数据库
    db.add_attendance_record(student_id, course_id, status, confidence)

    # 5. 更新冷却时间
    self._last_check_time[student_id] = now

    return True, status, "张三 打卡成功（正常）"
```

### 三个线程锁的作用

```python
self._cache_lock = RLock()       # 可重入锁，保护人脸库缓存
self._cooldown_lock = Lock()     # 保护冷却时间字典
```

- **RLock（可重入锁）**：同一个线程可以多次 acquire 不会死锁。用于缓存读写。
- **Lock（普通锁）**：保护 `_last_check_time` 字典，防止两个识别线程同时判断同一个人"没打过卡"然后都写入。

## 小结

```
services/
├── auth_service.py        → 登录：bcrypt验密 + 会话状态
├── student_service.py     → 注册：CNN+5次采样 → 检测人脸 → 提取特征 → 写入DB
├── attendance_service.py  → 考勤：HOG+1次采样 → 60秒人脸库缓存 → 匹配 → 打卡（冷却+判迟到）
└── course_service.py      → 课程：简单CRUD

关键设计：
- 混合策略在此层落地：StudentService用CNN+5jitters，AttendanceService用HOG+1jitter
- 人脸库缓存60秒TTL，新注册学生无需重启即可被识别
- 三个锁：RLock保护缓存，Lock保护冷却，保证多线程安全
- 打卡三道防线：冷却(10秒) → 今日重复 → 迟到判定
```

---

# 第五层：`main.py` —— 心脏

只有 76 行，但它是整个程序的**生命周期管理者**。

## 启动前奏（28-47 行）

```python
# 高 DPI
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

# 创建应用 + 全局配置
app = QApplication(sys.argv)
app.setStyle('Fusion')           # Qt 内置的跨平台统一风格
font.setFamily("Microsoft YaHei") # 全局中文字体

# 数据库 + 默认账户
db = DatabaseManager()           # 建表（如果不存在）
ensure_default_admin(db)         # 首次运行创建 admin/admin123
```

这四步只执行一次。`app = QApplication(sys.argv)` 是整个 Qt 世界的**唯一全局入口**，后面所有窗口都依附于它。

## 心脏循环（49-70 行）—— 核心中的核心

```python
while True:                          # ← 无限循环
    # ── 第一阶段：登录 ──
    login_dialog = LoginDialog(db)
    if login_dialog.exec_() != LoginDialog.Accepted:
        break                        # 用户点了 × 关闭 → 退出程序

    # ── 第二阶段：主窗口 ──
    window = MainWindow()
    window.show()                    # 显示主窗口
    app.exec_()                      # ← 程序在这里"停住"，进入 Qt 事件循环
                                     #    直到窗口关闭，这行才会返回

    # ── 第三阶段：判断去向 ──
    if session_manager.current_user is None:
        continue                     # → 回到循环开头，重新弹出登录框
    else:
        break                        # → 退出程序
```

### 为什么说它是"心脏"？

因为整个程序的生命节奏就是这个循环决定的：

```
登录框 → 主窗口 → 判断 → 登录框 → 主窗口 → 判断 → ...
  │                  │
  └──── 退出登录 ────┘    (continue)
  
  └──── 直接关闭程序 ────┘ (break)
```

**关键：`session_manager.current_user is None` 怎么变成 None 的？**

当用户在 MainWindow 里点"退出登录"时，GUI 层会调用：

```python
session_manager.logout()   # → 把 current_user 设为 None
```

然后关闭 MainWindow。MainWindow 关闭后 `app.exec_()` 返回，回到 while 循环，检查 `current_user is None` → True → `continue` 回到登录界面。

当用户直接点 MainWindow 的 × 关闭时，`current_user` 没有被清除（还是登录状态），`app.exec_()` 返回后检查 → `current_user is not None` → `break` 退出程序。

## main.py 在整个架构中的位置

```
main.py
  │
  ├── 创建 QApplication (Qt世界的唯一入口)
  ├── 创建 DatabaseManager (数据库建表)
  ├── ensure_default_admin (首次启动创建账户)
  │
  └── while True:  ← 心脏循环
        │
        ├── LoginDialog  ← 调 gui/
        │     └── 内部调 AuthService + SessionManager  ← 调 services/
        │
        ├── MainWindow   ← 调 gui/
        │     ├── AttendancePanel → AttendanceService → core/ + database/
        │     └── TeacherPanel    → StudentService/CourseService → core/ + database/
        │
        └── 判断循环方向 (session_manager.current_user)
```

`main.py` 自己**不写任何业务逻辑**，它唯一的职责是：**初始化全局资源，然后编排登录和主窗口之间的循环节奏。**

## 小结

```
main.py = 76行 = 3个阶段

阶段一（一次性）：QApplication → 数据库建表 → 默认管理员
阶段二（循环体）：登录框 → 主窗口 → 判断去向
阶段三（结束）  ：sys.exit(0)

心脏节律：
  点击"退出登录" → session_manager.current_user = None → continue → 回到登录
  点击 × 关闭    → session_manager.current_user 还在  → break    → 退出程序
```

---

# 第六层：`gui/` —— 界面层（双手）

这一层文件最多，但骨架清晰。共 8 个文件，分三个角色：

```
apple_style.py    ← 设计系统（唯一的外观定义源）
login_dialog.py   ← 登录入口
main_window.py    ← 主框架（侧边栏 + 内容区）
attendance_panel.py ← 考勤面板（摄像头 + 实时识别）
teacher_panel.py   ← 教师面板（4 个子页面）
register_dialog.py ← 注册对话框
edit_*.py          ← 编辑对话框
widgets/           ← 通用组件（LoadingOverlay、Toast 等）
```

## `apple_style.py` —— 设计宪法

866 行，没有一句业务逻辑。它定义了整个系统的**视觉语言**：

```
COLORS      → 苹果配色：蓝 #007AFF、绿 #34C759、红 #FF3B30、深灰侧边栏 #1D1D1F
FONTS       → 苹方优先，微软雅黑兜底
RADIUS      → 6/10/14/20px 四档圆角
SHADOWS     → 4 档阴影深度
ANIMATION   → 缓动曲线
GRADIENTS   → 渐变配色
ICONS       → emoji 图标映射

QSS 样式片段：
  NAVIGATION_STYLE   → 侧边栏
  get_button_style() → 按钮（primary/success/danger/secondary/ghost 五档）
  INPUT_STYLE        → 输入框
  TABLE_STYLE        → 表格
  TAB_STYLE          → 标签页
```

**为什么重要？** 所有 GUI 文件都 `from .apple_style import COLORS, RADIUS, ...`，没有人自己写颜色。要换主题色，只改这一个文件。

## `login_dialog.py` —— 登录门

```
┌──────────────────────────────┐
│                          [×] │  ← 无边框窗口，可拖动
│                              │
│         📷 (Logo)            │
│    人脸识别考勤系统            │
│   Face Attendance System     │
│                              │
│   用户名 [_______________]   │
│   密码   [_______________]   │
│                              │
│   [        登 录         ]   │
│                              │
│   默认账号: admin / admin123  │
└──────────────────────────────┘
```

核心逻辑只有 `login()` 一个方法：

```python
def login(self):
    user = self.db.verify_user(username, password)  # 走 bcrypt 验证
    if user:
        session_manager.login(user)   # 记入全局会话
        self.accept()                 # 关闭对话框，返回 Accepted
    else:
        self._show_error("用户名或密码错误")
```

`self.accept()` → `login_dialog.exec_()` 返回 `Accepted` → `main.py` 的 while 循环进入下一阶段。

## `main_window.py` —— 主框架

**布局结构**：水平分割，左窄右宽。

```
┌─────────────┬──────────────────────────────────────┐
│  侧边栏      │         内容区 (QStackedWidget)        │
│  (220px)    │                                      │
│             │  第0页: AttendancePanel (考勤打卡)      │
│  📅 考勤打卡  │  第1页: TeacherPanel    (学生管理)      │
│  👥 学生管理  │  第2页: TeacherPanel    (课程管理)      │
│  📚 课程管理  │  第3页: TeacherPanel    (考勤记录)      │
│  📊 考勤记录  │  第4页: TeacherPanel    (数据导出)      │
│  📤 数据导出  │                                      │
│             │                                      │
│  [用户信息]  │                                      │
│  [退出登录]  │                                      │
└─────────────┴──────────────────────────────────────┘
```

**关键设计：5 个侧边栏按钮，只切换 2 个面板。**

```python
def switch_page(self, index):
    if index == 0:
        self.content_stack.setCurrentWidget(self.attendance_panel)  # 考勤面板
    else:
        self.content_stack.setCurrentWidget(self.teacher_panel)     # 教师面板
        self.teacher_panel.switch_tab(index - 1)  # 内部切标签页
```

侧边栏按钮 0 对应 AttendancePanel，按钮 1-4 对应 TeacherPanel 的 4 个内部标签页。`TeacherPanel` 的标签栏是隐藏的（`tabBar().hide()`），用户只看到侧边栏来控制。

**退出登录的精妙设计**：

```python
def logout(self):
    self._is_logging_out = True       # 设标志位
    self.attendance_panel.stop_camera() # 停摄像头
    session_manager.logout()           # 清会话
    self.close()                       # 关窗口

def closeEvent(self, event):
    if self._is_logging_out:           # 退出登录 → 不弹确认框，直接关
        event.accept()
        return
    # 直接 × 关闭 → 弹框确认 → 不清除 session
    if reply == Yes:
        event.accept()                 # session 保留 → main.py 的 break 退出程序
```

## `attendance_panel.py` —— 实时考勤核心

这是最复杂的面板，核心是**双线程架构**：

```
          CameraThread                     FaceRecognitionThread
         ┌─────────────┐                  ┌─────────────────────┐
摄像头 ──→│ 采集帧       │── frame_ready ──→│ add_frame()         │
         │ 30fps       │   (pyqtSignal)   │ 只保留最新1帧(Queue)  │
         │ 水平翻转     │                  │                      │
         └─────────────┘                  │ process_frame()      │
                                          │  → detect (HOG)     │
                │                         │  → encode (jitters=1)│
                │                         │  → match (tolerance) │
                ▼                         │                      │
         AttendancePanel                  │ result_ready ────────→│
         绘制人脸框 + 显示画面              └─────────────────────┘
                                                   │
                                                   ▼
                                      on_recognition_result()
                                          │
                                          ▼
                                      check_in() 自动打卡
                                          │
                                          ▼
                                      refresh_records() 刷新右侧表格
```

**为什么拆两个线程？**

- CameraThread 专注采集帧，30fps，不能卡
- FaceRecognitionThread 专注识别，每帧可能耗时 50-100ms
- 如果放一个线程，识别期间摄像头丢帧，画面卡顿
- Queue 容量只有 1（`maxsize=1`），新帧来就丢旧帧——保证识别永远处理最新帧

**自动打卡流程**：

```python
def on_recognition_result(self, results):
    for result in results:
        if result['student_id']:
            success, status, message = self.attendance_service.check_in(
                student_id, result['student_id'],
                course_id=course_id,
                confidence=result['confidence']
            )
```

识别到 → 自动写入数据库 → 右侧表格刷新。用户什么都不用点，站在摄像头前就行。

## `teacher_panel.py` —— 数据管理中心

4 个标签页（tabBar 隐藏，由侧边栏控制）：

| 标签页 | 功能 | 关键技术点 |
|--------|------|-----------|
| 学生管理 | 增删改查 + 搜索 + 批量导入 | 新增/编辑/删除后自动刷新考勤服务的人脸缓存 |
| 课程管理 | 增删改查 + 搜索 | 对话框式编辑，时间格式校验 |
| 考勤记录 | 按课程+日期+状态筛选查询 | 统计卡片（正常/迟到/缺勤/总计），支持修改状态和删除 |
| 数据导出 | Excel/CSV 导出 | 同步查询条件到导出界面，支持按课程+日期范围导出 |

**每个操作都刷新人脸缓存**：

```python
def add_student(self):
    dialog = RegisterDialog(...)
    if dialog.exec_():
        self.refresh_students()
        self.attendance_service.refresh_face_database()  # ← 关键
```

新增学生后立刻刷新 AttendanceService 的人脸缓存，这样考勤面板 60 秒缓存 TTL 到期前也能识别新学生。

## `camera.py` —— 摄像头线程

三个关键设计：

**1. 错误退避**：连续读取失败不立即崩溃，而是指数退避重试（0.1s → 0.2s → 0.4s → ... 最多 2s），连续失败 10 次才停止。

**2. 镜像效果**：`cv2.flip(frame, 1)` 水平翻转，让画面像照镜子一样自然。

**3. 安全停止**：

```python
def stop(self):
    self._stop_event.set()
    with self._cap_lock:
        if self._cap:
            self._cap.release()   # 先释放摄像头 → 阻塞的 read() 会立即返回
            self._cap = None
    self._thread.join(timeout=3)  # 最多等 3 秒
```

## GUI 层小结

```
gui/
├── apple_style.py       ← 设计宪法：颜色、字体、圆角、阴影、QSS片段
├── login_dialog.py      ← 登录门：无边框 + 可拖动 + bcrypt验证
├── main_window.py       ← 主框架：侧边栏(220px) + QStackedWidget(2面板)
├── attendance_panel.py  ← 考勤：双线程(CameraThread + FaceRecognitionThread) + 自动打卡
├── teacher_panel.py     ← 管理：4标签页(学生/课程/记录/导出) + 操作后刷新缓存
├── register_dialog.py   ← 注册：摄像头拍照/选文件 + CNN人脸检测
├── edit_*.py            ← 编辑对话框
└── widgets/             ← 通用组件：LoadingOverlay, EmptyState, Toast

线程架构：
  CameraThread ──frame_ready──→ UI显示画面
       │
       └──→ FaceRecognitionThread ──result_ready──→ 自动打卡 → 刷新表格

关键信号链：
  摄像头帧 → 识别 → 打卡 → 写入DB → 刷新UI
```

---

# 第七层：`utils/` —— 工具箱

四个文件，各自独立，给上层提供通用能力。

## `logger.py` —— 统一日志

```python
def get_logger(name):
    logger = logging.getLogger(name)
    if logger.handlers:          # 防重复——同一个 name 不会重复添加 handler
        return logger

    handler = logging.StreamHandler()
    handler.setFormatter(...)    # 格式：时间 - 模块名 - 级别 - 消息

    level = getattr(logging, config.LOG_LEVEL.upper())  # 'INFO' → logging.INFO
    logger.setLevel(level)
    return logger
```

全项目任何一个 `.py` 文件里写 `logger = get_logger(__name__)` 就能拿到一个配置好的 logger。改 `config.LOG_LEVEL = 'DEBUG'` 就能全局切换日志级别。

## `exceptions.py` —— 异常层次

```
AttendanceSystemError          ← 根基类
├── DatabaseError              ← 数据库问题
├── StudentNotFoundError       ← 学生不存在（带 student_id 属性）
├── CourseNotFoundError        ← 课程不存在
├── FaceDetectionError         ← 检测失败
├── FaceEncodingError          ← 编码失败
├── FaceMatchingError          ← 匹配失败
├── CameraError                ← 摄像头问题
├── AuthenticationError        ← 登录认证失败
├── DuplicateRecordError       ← 重复打卡
└── CooldownError              ← 冷却中（带 remaining_seconds）
```

层次已经搭好——将来如果要改成抛异常的模式，不需要重新设计异常类型。

## `excel_exporter.py` —— 数据导出

所有方法都是 `@staticmethod`，纯粹的**数据 → Excel 文件**转换：

```python
ExcelExporter.export_attendance_records(records, file_path)
    → 蓝色表头 + 状态列自动着色（绿=正常, 黄=迟到, 红=缺勤）+ 自适应列宽

ExcelExporter.export_student_list(students, file_path)
    → 学号/姓名/班级/注册时间 四列

ExcelExporter.generate_report(records, course_name, start, end, file_path)
    → 带标题、统计汇总的报告格式
```

底层用 `openpyxl`，不依赖 Excel 软件本身。

## `camera.py` —— 摄像头线程

在 GUI 层中已详细讲过。补充：`CameraManager` 单例类保证全程序只有一个摄像头实例，防止重复打开。

## 小结

```
utils/
├── logger.py         → get_logger(name) 统一日志，级别从 config 读取
├── exceptions.py     → 11个自定义异常，层次清晰
├── excel_exporter.py → openpyxl 导出，纯静态方法
└── camera.py         → CameraThread (线程采集) + CameraManager (单例)
```

---

# 全系统互联关系图

## 一、静态依赖（import 关系）

```
config.py
  └── import os                          （零项目依赖，最底层）

utils/
  ├── logger.py      → import config
  ├── exceptions.py  → （零项目依赖）
  ├── camera.py      → （零项目依赖，只依赖 cv2 + PyQt5）
  └── excel_exporter.py → （零项目依赖，只依赖 openpyxl）

database/
  ├── models.py      → （零项目依赖，只依赖 SQLAlchemy）
  └── db_manager.py  → from .models import *
                     → from services.auth_service import AuthService  ← 注意！环形引用

core/
  ├── face_detector.py → import config
  ├── face_encoder.py  → import config
  │                     → from utils.logger import get_logger
  └── face_matcher.py  → import config

services/
  ├── auth_service.py     → import bcrypt （零项目依赖）
  ├── student_service.py  → from core.face_detector import FaceDetector
  │                       → from core.face_encoder import FaceEncoder
  │                       → from database.db_manager import DatabaseManager
  │                       → import config
  ├── attendance_service.py → from core.* import FaceDetector, FaceEncoder, FaceMatcher
  │                          → from database.db_manager import DatabaseManager
  │                          → import config
  │                          → from utils.logger import get_logger
  └── course_service.py    → from database.db_manager import DatabaseManager

gui/
  ├── apple_style.py  → （零项目依赖，纯 CSS 字符串）
  ├── login_dialog.py → from database.db_manager import DatabaseManager
  │                   → from services.auth_service import session_manager
  │                   → from .apple_style import COLORS, RADIUS, ...
  ├── main_window.py  → import config
  │                   → from database.db_manager import DatabaseManager
  │                   → from services.auth_service import session_manager
  │                   → from .apple_style import ...
  │                   → from .attendance_panel import AttendancePanel
  │                   → from .teacher_panel import TeacherPanel
  ├── attendance_panel.py → from database.db_manager import DatabaseManager
  │                       → from services.attendance_service import AttendanceService
  │                       → from utils.camera import CameraThread
  │                       → from utils.logger import get_logger
  │                       → import config
  │                       → from .apple_style import ...
  │                       → from .widgets import LoadingOverlay, EmptyStateWidget
  ├── teacher_panel.py    → from database.db_manager import DatabaseManager
  │                       → from services.student_service import StudentService
  │                       → from services.course_service import CourseService
  │                       → from services.attendance_service import AttendanceService
  │                       → from utils.excel_exporter import ExcelExporter
  │                       → from .apple_style import ...
  │                       → from .register_dialog import RegisterDialog
  │                       → from .edit_student_dialog import EditStudentDialog
  │                       → from .edit_course_dialog import EditCourseDialog
  │                       → from .widgets import ...
  ├── register_dialog.py  → 同上模式
  └── widgets/            → from .apple_style import ...

main.py
  ├── from gui.main_window import MainWindow
  ├── from gui.login_dialog import LoginDialog
  ├── from database.db_manager import DatabaseManager
  └── from services.auth_service import session_manager
```

## 二、唯一的一处"环形引用"及其解法

`database/db_manager.py` 里有一处特殊的 import：

```python
# db_manager.py 的 add_user() 方法内部：
from services.auth_service import AuthService
hashed = AuthService.hash_password(password)
```

这个 import 写在**方法内部**，不是在文件顶部。为什么？

```
database/db_manager.py  ← 如果顶部 import services.auth_service
    ↓
services/auth_service.py
    ↓ (没有引用 database)
    
但 services/attendance_service.py 引用了 database/db_manager.py
    ↓
database/db_manager.py 已经 import 了 services.auth_service
    ↓
形成循环：database → services → database
```

解法就是**延迟 import**——把 `from services.auth_service import AuthService` 写在方法体里而不是文件头。Python 在方法第一次被调用时才执行这行 import，此时的循环依赖链已经被打破（因为 `database` 模块本身已经加载完了）。

这是全项目**唯一需要这种技巧的地方**。

## 三、运行时调用链（三条主流程）

### 流程 1：启动

```
main.py: main()
  │
  ├─→ QApplication()                         Qt 初始化
  ├─→ DatabaseManager()                      建表（SQLAlchemy）
  ├─→ ensure_default_admin(db)               首次创建 admin/admin123
  │     └─→ db.add_user() ──→ AuthService.hash_password() ──→ bcrypt
  │
  └─→ while True:
        ├─→ LoginDialog(db).exec_()
        │     └─→ login()
        │           ├─→ db.verify_user(username, password)
        │           │     └─→ AuthService.verify_password()  ← bcrypt
        │           └─→ session_manager.login(user)
        │
        ├─→ MainWindow()
        │     ├─→ AttendancePanel(db)
        │     │     ├─→ AttendanceService(db)
        │     │     │     ├─→ FaceDetector(model='hog')
        │     │     │     ├─→ FaceEncoder(jitters=1)
        │     │     │     └─→ FaceMatcher(tolerance=0.5)
        │     │     └─→ refresh_face_database()
        │     │           └─→ db.get_all_face_encodings()
        │     │
        │     └─→ TeacherPanel(db)
        │           ├─→ StudentService(db)
        │           │     ├─→ FaceDetector(model='cnn')
        │           │     └─→ FaceEncoder(jitters=5)
        │           ├─→ CourseService(db)
        │           └─→ AttendanceService(db)   ← 第二个实例！
        │
        └─→ app.exec_()                        进入 Qt 事件循环
```

### 流程 2：考勤识别（实时循环）

```
用户点击 "开始考勤"
  │
  └─→ AttendancePanel.start_camera()
        │
        ├─→ CameraThread(camera_index=0, 640x480)
        │     └─→ start() ──→ 新线程 _run()
        │           └─→ while running:
        │                 frame = cap.read()
        │                 frame = cv2.flip(frame, 1)
        │                 frame_ready.emit(frame)        ← 信号① 发射
        │
        ├─→ FaceRecognitionThread(attendance_service)
        │     └─→ start() ──→ 新线程 run()
        │           └─→ refresh_face_database()
        │               while running:
        │                 frame = queue.get()
        │                 results = attendance_service.process_frame(frame)
        │                    │
        │                    ├─→ detector.detect(frame)      ← HOG 模型
        │                    ├─→ encoder.encode_faces(...)    ← jitters=1
        │                    └─→ matcher.match(encoding, 缓存人脸库)
        │                 result_ready.emit(results)          ← 信号② 发射
        │
        │  信号① → on_frame_ready(frame)
        │            ├─→ recognition_thread.add_frame(frame)  ← 投喂给识别线程
        │            └─→ draw_results(frame)                  ← 画人脸框
        │                  └─→ display_image(frame)             ← 显示画面
        │
        │  信号② → on_recognition_result(results)
        │            └─→ 遍历每个识别结果:
        │                  attendance_service.check_in(student_id, course_id, confidence)
        │                    │
        │                    ├─→ 冷却检查 (10秒)
        │                    ├─→ 今日重复检查
        │                    ├─→ 迟到判定 (15分钟)
        │                    └─→ db.add_attendance_record(...)
        │                  
        │                  refresh_records()              ← 刷新右侧表格
```

**双线程信息流图**：

```
CameraThread (子线程)              FaceRecognitionThread (子线程)
     │                                      │
     │ frame_ready.emit()                   │ result_ready.emit()
     │   (跨线程信号)                          │   (跨线程信号)
     ▼                                      ▼
AttendancePanel (主线程)              AttendancePanel (主线程)
  on_frame_ready()                     on_recognition_result()
     │                                      │
     ├─→ 投喂到 Queue ──────────────────→ 取帧处理
     │                                      │
     └─→ 绘制上一轮的识别结果               └─→ 自动打卡 → 写DB → 刷新表格
     └─→ 显示画面到 QLabel
```

### 流程 3：学生注册

```
用户点击 "添加学生"
  │
  └─→ TeacherPanel.add_student()
        └─→ RegisterDialog(db).exec_()
              │
              ├── 方式A：摄像头拍照
              │     └─→ camera.capture_image()
              │
              ├── 方式B：选择文件
              │     └─→ cv2.imdecode(中文路径读取)
              │
              └─→ student_service.register_student(student_id, name, image=img)
                    │
                    ├─→ FaceDetector(model='cnn').detect(img)   ← CNN模型
                    │     ├─→ 0张脸 → 报错
                    │     └─→ >1张脸 → 报错
                    │
                    ├─→ FaceEncoder(jitters=5).encode(img, location)  ← 5次采样
                    │
                    └─→ db.add_student(..., face_encoding=特征向量)
                          └─→ encoding_to_blob() → LargeBinary 写入
              
              返回 TeacherPanel:
                ├─→ refresh_students()                          ← 刷新学生表格
                └─→ attendance_service.refresh_face_database()  ← 刷新考勤人脸缓存
```

## 四、全局单例的共享关系

有三个对象是全局共享的：

| 单例 | 定义位置 | 谁在用 | 用途 |
|------|---------|--------|------|
| `session_manager` | `services/auth_service.py` 底部 | `main.py`、`LoginDialog`、`MainWindow` | 记录 "当前谁登录了" |
| `DatabaseManager` | 每个服务/面板各自 `new` 一个 | 全部 | 实际不是单例，但底层共享同一个 SQLite 文件 |
| `CameraManager` | `utils/camera.py` | 不常用，实际直接用 CameraThread | 备用单例 |

注意：`DatabaseManager` 在每个面板和服务里都各自 `new` 了一个实例，但它们底层都连接同一个 `face_attendance.db` 文件。SQLite 本身支持多连接并发读，所以虽然实例不同，数据是一致的。

## 五、config.py 的参数被谁消费

```
config.FACE_USE_HYBRID_MODE ──→ StudentService.__init__()     → 决定 CNN/HOG
                              ──→ AttendanceService.__init__() → 决定 HOG/CNN

config.FACE_RECOGNITION_TOLERANCE ──→ FaceMatcher(tolerance=0.5)

config.FACE_REGISTRATION_MODEL ──→ StudentService → FaceDetector(model='cnn')
config.FACE_REGISTRATION_JITTERS ──→ StudentService → FaceEncoder(jitters=5)

config.FACE_ATTENDANCE_MODEL ──→ AttendanceService → FaceDetector(model='hog')
config.FACE_ATTENDANCE_JITTERS ──→ AttendanceService → FaceEncoder(jitters=1)

config.CAMERA_INDEX/WIDTH/HEIGHT ──→ AttendancePanel.start_camera()
                                     ──→ CameraThread(camera_index=0, width=640, height=480)

config.ATTENDANCE_COOLDOWN ──→ AttendanceService.check_in() → 冷却判断
config.LATE_THRESHOLD_MINUTES ──→ AttendanceService.check_in() → 迟到判定

config.WINDOW_WIDTH/HEIGHT ──→ MainWindow.setGeometry()
config.THEME_COLOR ──→ apple_style.COLORS['primary'] (实际上 apple_style 有自己的 #007AFF)

config.LOG_LEVEL ──→ utils/logger.py → get_logger() → logger.setLevel()
config.REFRESH_INTERVAL_MS ──→ AttendancePanel → QTimer(5000) → 自动刷新记录
```

## 六、依赖层级自底向上

```
第0层（零项目依赖）:
  config.py
  database/models.py
  utils/exceptions.py
  gui/apple_style.py

第1层（只依赖第0层）:
  utils/logger.py         → config
  utils/camera.py         → (仅三方库)
  utils/excel_exporter.py → (仅三方库)
  core/face_detector.py   → config
  core/face_encoder.py    → config + logger
  core/face_matcher.py    → config

第2层（依赖第0-1层 + 同层）:
  database/db_manager.py  → models + services.auth_service (延迟import)
  services/auth_service.py → (仅 bcrypt)

第3层（依赖第0-2层）:
  services/student_service.py    → core + database + config
  services/attendance_service.py → core + database + config + logger
  services/course_service.py     → database

第4层（依赖所有下层）:
  gui/login_dialog.py       → database + services + apple_style
  gui/attendance_panel.py   → database + services + utils + apple_style
  gui/teacher_panel.py      → database + services + utils + apple_style
  gui/main_window.py        → config + database + services + gui子面板
  gui/register_dialog.py    → database + services + apple_style

第5层（顶层入口，依赖所有）:
  main.py → gui + database + services
```

## 七层全景回顾

```
                         ┌──────────────┐
                         │   main.py    │  ← 心脏：登录循环，编排生命周期
                         │   (76行)     │
                         └──────┬───────┘
                                │ 调用
                ┌───────────────┼───────────────┐
                ▼               ▼               ▼
        ┌──────────────┐ ┌───────────┐ ┌──────────────┐
        │  services/   │ │   gui/    │ │   utils/     │
        │  业务编排     │ │  用户界面  │ │   工具箱      │
        │──────────────│ │───────────│ │──────────────│
        │ AuthService  │ │ LoginDlg  │ │ logger       │
        │ StudentSvc   │ │ MainWin   │ │ camera       │
        │ AttendanceSvc│ │ AttendPnl │ │ excel_export │
        │ CourseSvc    │ │ TeacherPnl│ │ exceptions   │
        │ SessionMgr   │ │ apple_style│              │
        └──┬───────┬───┘ └───────────┘ └──────────────┘
           │       │
           ▼       ▼
    ┌──────────┐ ┌──────────────┐
    │  core/   │ │  database/   │
    │  算法层   │ │   数据层      │
    │──────────│ │──────────────│
    │Detector  │ │ models (4表) │
    │Encoder   │ │ db_manager   │
    │Matcher   │ │              │
    └──────────┘ └──────────────┘
           ▲               ▲
           └───────┬───────┘
                   │ 都依赖
           ┌───────┴───────┐
           │   config.py   │  ← 大脑：47行，所有决策的唯一来源
           │   (47行)      │
           └───────────────┘
```

**数据流向一句话**：

> `config` 定规则 → `core` 做算法 → `database` 存数据 → `services` 串联业务 → `gui` 展示交互 → `main` 循环驱动 → `utils` 辅助支撑

---

# 总结：七层互联三句话

1. **config 是单向信息流起点** —— 参数从 config 流出，被 core/services/gui/utils 消费，没有任何模块反向写入 config。

2. **core 和 database 是平行的底层** —— 它们互不认识、互不引用。services 层是唯一同时认识两者的"媒人"。

3. **gui 是顶层的消费者** —— 它引用 services（业务）、database（查询）、utils（工具）、config（参数），但没有任何下层模块引用 gui。信息是单向向上流动、再通过 Qt 信号/槽在 gui 内部横向传播的。
