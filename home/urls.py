# _*_ coding : utf-8 _*_
# @Date : 2022/10/8 23:14
# @Author : zhupt
# @File : urls
# @Project : blog
from django.urls import path

from home.views import HomeView, DetailView

urlpatterns = [
    # 首页路由
    path('', HomeView.as_view(), name='index'),
    # 文章详情
    path('detail/', DetailView.as_view(), name='detail'),
    # 404
    path('404/', DetailView.as_view(), name='404')
]
