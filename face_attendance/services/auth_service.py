"""
认证服务
提供用户认证和会话管理功能
"""
from typing import Optional, Dict
from datetime import datetime
from utils.security import verify_password, hash_password


class AuthService:
    """认证服务 — 实例化使用，由 AppContext 注入 db"""

    def __init__(self, db):
        self.db = db

    def login(self, username: str, password: str) -> Optional[Dict]:
        """验证用户登录，成功返回用户信息，失败返回 None"""
        user = self.db.get_user(username)
        if user is None:
            return None
        if verify_password(password, user['password_hash']):
            return user
        return None

    def create_user(self, username: str, password: str, role: str = 'teacher') -> Dict:
        """创建新用户（自动哈希密码）"""
        return self.db.add_user(username, hash_password(password), role)


class SessionManager:
    """会话管理类"""

    def __init__(self):
        self._current_user: Optional[Dict] = None
        self._login_time = None

    def login(self, user: Dict) -> None:
        self._current_user = user
        self._login_time = datetime.now()

    def logout(self) -> None:
        self._current_user = None
        self._login_time = None

    @property
    def current_user(self) -> Optional[Dict]:
        return self._current_user

    @property
    def is_logged_in(self) -> bool:
        return self._current_user is not None

    @property
    def login_time(self):
        return self._login_time

    def get_user_display_name(self) -> str:
        if self._current_user:
            return self._current_user.get('username', '未知用户')
        return '未登录'
