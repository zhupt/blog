# _*_ coding : utf-8 _*_
# @Date : 2022/10/2 19:48
# @Author : zhupt
# @File : urls
# @Project : blog
from django.urls import path

from users.views import ImageCodeView, SmsCodeView, LoginView, LogoutView, ForgetPwdView, UserCenterView, WriteBlogView
from users.views import RegisterView

urlpatterns = [
    # path的第一个参数：路由
    # path的第二个参数：视图函数名
    # 注册
    path('register/', RegisterView.as_view(), name='register'),
    # 验证码
    path('imagecode/', ImageCodeView.as_view(), name='imagecode'),
    # 短信发送
    path('smscode/', SmsCodeView.as_view(), name='smscode'),
    # 用户登录
    path('login/', LoginView.as_view(), name='login'),
    # 用户注销
    path('logout/', LogoutView.as_view(), name='logout'),
    # 忘记密码
    path('forgetpwd/', ForgetPwdView.as_view(), name='forgetpwd'),
    # 个人中心
    path('center/', UserCenterView.as_view(), name='center'),
    # 写博客
    path('writeblog/', WriteBlogView.as_view(), name='writeblog')
]
