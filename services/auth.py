# -*- coding: utf-8 -*-
"""认证服务：基于 Flask-Login 的管理员登录。"""
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from models.database import AdminUser, get_session

login_manager = LoginManager()


class AdminUserWrapper(UserMixin):
    """Flask-Login 用户包装类。"""

    def __init__(self, admin_user):
        self.id = str(admin_user.id)
        self.username = admin_user.username
        self.display_name = admin_user.display_name
        self.role = admin_user.role


@login_manager.user_loader
def load_user(user_id):
    sess = get_session()
    try:
        u = sess.get(AdminUser, int(user_id))
        if u:
            return AdminUserWrapper(u)
    except Exception:
        return None
    finally:
        sess.close()
    return None


def authenticate(username, password):
    """校验账号密码，成功返回 wrapper。"""
    sess = get_session()
    try:
        u = sess.query(AdminUser).filter_by(username=username).first()
        if u and check_password_hash(u.password_hash, password):
            return AdminUserWrapper(u)
    finally:
        sess.close()
    return None


def do_login(username, password):
    """登录，成功返回 True。"""
    user = authenticate(username, password)
    if user:
        login_user(user)
        return True
    return False


def do_logout():
    logout_user()
