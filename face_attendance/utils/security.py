"""
密码安全工具
纯工具函数，不依赖任何项目模块
"""
import bcrypt


def hash_password(password: str) -> str:
    """对密码进行bcrypt哈希"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(password: str, hashed_password: str) -> bool:
    """验证密码是否匹配"""
    try:
        return bcrypt.checkpw(
            password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False


def is_hashed(password: str) -> bool:
    """判断密码是否已经哈希过"""
    return password.startswith('$2b$') or password.startswith('$2a$')
