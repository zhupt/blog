import logging
import re
from random import randint

from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http.response import HttpResponse, JsonResponse
from django.http.response import HttpResponseBadRequest
from django.shortcuts import render, redirect
# Create your views here.
from django.urls import reverse
from django.views import View
from django_redis import get_redis_connection

from home.models import ArticleCategory, Article
from libs.captcha.captcha import captcha
from libs.yuntongxun.sms import CCP
from users.models import User
from utils.response_code import RETCODE

logger = logging.getLogger('django')


# 注册视图
class RegisterView(View):

    def get(self, request):
        return render(request, 'register.html')

    def post(self, request):
        # 1、获取参数
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        sms_code = request.POST.get('sms_code')
        # 2、验证参数是否齐全
        if not all([mobile, password, password2, sms_code]):
            return HttpResponseBadRequest('缺少必要的参数')
        # 3、验证手机号是否符合要求
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return HttpResponseBadRequest('手机号不符合规则')
        # 4、验证密码是否正确
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return HttpResponseBadRequest('请输入8-20位密码，密码可以使用数字和字母')
        if password != password2:
            return HttpResponseBadRequest('密码不一致')
        # 5、验证密码是否正确
        redis_conn = get_redis_connection('default')
        redis_sms_code = redis_conn.get('sms:{}'.format(mobile))
        # 6、短信验证
        if redis_sms_code is None:
            return HttpResponseBadRequest('短信验证码已过期')
        if redis_sms_code.decode() != sms_code:
            return HttpResponseBadRequest('短信验证码不一致')
        # 7、保存注册信息
        try:
            user = User.objects.create_user(username=mobile, mobile=mobile, password=password)
        except Exception as e:
            logger.error(e)
            return HttpResponseBadRequest('注册失败')
        # 登录用户
        login(request, user)
        response = redirect(reverse('home:index'))
        # 设置cookie
        response.set_cookie('is_login', True)
        response.set_cookie('username', user.username, max_age=7 * 24 * 3600)
        return response


class ImageCodeView(View):
    def get(self, request):
        '''
        1、后端接受前端传来的uuid
        2、判断uuid是否获取到
        3、生成图片验证，生成图片二进制和图片内容值
        4、将图片内容验证码的值保存到redis，uuid作为key，同时设置一个时效
        5、将图片二进制返回给前端
        :return:
        '''
        uuid = request.GET.get('uuid')
        if uuid is None:
            return HttpResponseBadRequest('没有传递过来uuid')
        # 生成验证码信息
        text, image = captcha.generate_captcha()
        # 把验证码值保存到redis
        redis_conn = get_redis_connection('default')
        redis_conn.setex('img:{}'.format(uuid), 300, text)
        # 返回二进制图片
        return HttpResponse(image, content_type='image/jpeg')


class SmsCodeView(View):

    def get(self, request):
        # 1、获取参数
        mobile = request.GET.get('mobile')
        image_code = request.GET.get('image_code')
        uuid = request.GET.get('uuid')
        # 2、验证参数是否齐全
        if not all([mobile, image_code, uuid]):
            return JsonResponse({'code': RETCODE.NECESSARYPARAMERR, 'errmsg': '缺少必要的参数'})
        # 3、验证验证码是否正确
        redis_conn = get_redis_connection('default')
        redis_image_code = redis_conn.get('img:{}'.format(uuid))
        if redis_image_code is None:
            return JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': '图片验证码已过期'})
        # 4、删除redis中的验证码
        try:
            redis_conn.delete('img:{}'.format(uuid))
        except Exception as e:
            logger.error(e)
        # 5、验证码比对
        if redis_image_code.decode().lower() != image_code.lower():
            return JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': '图片验证码错误'})
        # 6、生成短信验证码
        sms_code = '%06d' % randint(0, 999999)
        logger.info(sms_code)
        redis_conn.setex('sms:{}'.format(mobile), 300, sms_code)
        # 7、发送短信验证码
        CCP().send_template_sms(mobile, [sms_code, 5], 1)
        # 8、返回结果
        return JsonResponse({'code': RETCODE.OK, 'errmsg': '短信验证码发送成功'})


class LoginView(View):
    def get(self, request):
        return render(request, 'login.html')

    def post(self, request):
        # 1、获取参数
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        remember = request.POST.get('remember')
        # 2、验证参数是否齐全
        if not all([mobile, password]):
            return HttpResponseBadRequest('缺少必要的参数')
        # 3、验证手机号是否符合要求
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return HttpResponseBadRequest('手机号不符合规则')
        # 4、验证密码是否正确
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return HttpResponseBadRequest('密码不符合规则')
        # 5、判断登录用户是否存在
        user = authenticate(mobile=mobile, password=password)
        if user is None:
            return HttpResponseBadRequest('用户名或者密码不正确')
        # 6、登录操作
        login(request, user)

        next_page = request.GET.get('next')
        if next_page:
            response = redirect(next_page)
        else:
            response = redirect(reverse('home:index'))
        # 7、判断是否记住用户登录
        if remember != 'on':
            request.session.set_expiry(0)
            response.set_cookie('is_login', True)
        else:
            request.session.set_expiry(None)
            response.set_cookie('is_login', True, 14 * 24 * 3600)
        response.set_cookie('username', user.username, max_age=14 * 24 * 3600)
        return response


class LogoutView(View):
    def get(self, request):
        # 1、session清除
        logout(request)
        # 2、删除部分cookie数据
        response = redirect(reverse('users:login'))
        response.delete_cookie('is_login')
        # 3、跳转登录页面
        return response


class ForgetPwdView(View):

    def get(self, request):
        return render(request, 'forget_password.html')

    def post(self, request):
        # 1、获取参数
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        sms_code = request.POST.get('sms_code')
        # 2、验证参数是否齐全
        if not all([mobile, password, password2, sms_code]):
            return HttpResponseBadRequest('缺少必要的参数')
        # 3、验证手机号是否符合要求
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return HttpResponseBadRequest('手机号不符合规则')
        # 4、验证密码是否正确
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return HttpResponseBadRequest('请输入8-20位密码，密码可以使用数字和字母')
        if password != password2:
            return HttpResponseBadRequest('密码不一致')
        # 5、短信验证
        redis_conn = get_redis_connection('default')
        redis_sms_code = redis_conn.get('sms:{}'.format(mobile))
        if redis_sms_code is None:
            return HttpResponseBadRequest('短信验证码已过期')
        if redis_sms_code.decode() != sms_code:
            return HttpResponseBadRequest('短信验证码不一致')
        # 6、修改用户密码
        try:
            user = User.objects.get(username=mobile)
        except User.DoesNotExist:
            # 如果用户不存在则注册用户
            User.objects.create_user(username=mobile, mobile=mobile, password=password)
        except Exception as e:
            logger.error(e)
            return HttpResponseBadRequest('用户密码修改失败，请稍后重试')
        else:
            # 修改用户密码
            user.set_password(password)
            user.save()
        return redirect(reverse('users:login'))


class UserCenterView(LoginRequiredMixin, View):
    def get(self, request):
        # 获取用户信息
        user = request.user
        # 设置用户信息
        context = {
            'username': user.username,
            'mobile': user.mobile,
            'avatar': user.avatar.url if user.avatar else None,
            'user_desc': user.user_desc
        }
        return render(request, 'center.html', context=context)

    def post(self, request):
        # 获取用户信息
        user = request.user
        # 接收参数
        username = request.POST.get('username', user.username)
        user_desc = request.POST.get('desc', user.user_desc)
        avatar = request.FILES.get('avatar')
        try:
            user.username = username
            user.user_desc = user_desc
            if avatar:
                user.avatar = avatar
            user.save()
        except Exception as e:
            logger.error(e)
            return HttpResponseBadRequest('修改用户信息失败，请稍后重试')
        # 更新cookie中的用户信息
        response = redirect(reverse('users:center'))
        response.set_cookie('username', user.username, max_age=14 * 24 * 3600)
        return response


class WriteBlogView(LoginRequiredMixin, View):
    def get(self, request):
        # 获取所有分类信息
        categories = ArticleCategory.objects.all()
        context = {
            'categories': categories
        }
        return render(request, 'write_blog.html', context=context)

    def post(self, request):
        # 1、获取参数
        avatar = request.FILES.get('avatar')
        title = request.POST.get('title')
        tags = request.POST.get('tags')
        sumary = request.POST.get('sumary')
        content = request.POST.get('content')
        category_id = request.POST.get('category')
        user = request.user
        # 2、验证参数是否齐全
        if not all([avatar, title, tags, sumary, content, category_id]):
            return HttpResponseBadRequest('缺少必要的参数')
        # 3、判断分类是否存在
        try:
            category = ArticleCategory.objects.get(id=category_id)
        except ArticleCategory.DoesNotExist:
            return HttpResponseBadRequest('没有次分类')
        # 4、保存数据
        try:
            article = Article.objects.create(author=user, avatar=avatar, title=title, tags=tags, sumary=sumary,
                                             content=content,
                                             category=category)
        except Exception as e:
            logger.error(e)
            return HttpResponseBadRequest('博客发布失败，请稍后重试')
        return redirect(reverse('home:index'))
