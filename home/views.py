from django.core.paginator import Paginator, EmptyPage
from django.http import HttpResponseBadRequest
from django.shortcuts import render, redirect
# Create your views here.
from django.urls import reverse
from django.views import View

from home.models import ArticleCategory, Article, Comment


class HomeView(View):
    def get(self, request):
        # 1、获取所有分类
        categories = ArticleCategory.objects.all()
        # 2、接收传过来的分类id
        cat_id = request.GET.get('cat_id', 1)
        # 3、根据分类id获取分类信息
        try:
            category = ArticleCategory.objects.get(id=cat_id)
        except ArticleCategory.DoesNotExist:
            return HttpResponseBadRequest('没有次分类')
        # 4、查询分类下的分页文章信息列表
        page_num = request.GET.get('page_num', 1)
        page_size = request.GET.get('page_size', 10)
        articles = Article.objects.filter(category=category)
        paginator = Paginator(articles, per_page=page_size)
        try:
            page_articles = paginator.page(page_num)
        except EmptyPage:
            return HttpResponseBadRequest('页码为空')

        total_page = paginator.num_pages
        # 5、传递数据
        context = {
            'categories': categories,
            'category': category,
            'articles': page_articles,
            'page_num': page_num,
            'page_size': page_size,
            'total_page': total_page
        }
        return render(request, 'index.html', context=context)


class DetailView(View):
    def get(self, request):
        # 1、接收参数
        id = request.GET.get('id')
        try:
            article = Article.objects.get(id=id)
        except Article.DoesNotExist:
            return render(request, '404.html')
        else:
            # 浏览量加1
            article.total_views += 1
            article.save()
        # 2、查询分类信息
        categories = ArticleCategory.objects.all()
        # 3、查询浏览量前十的文章
        hot_articles = Article.objects.order_by('-total_views')[:9]
        # 4、获取评论数据
        page_num = request.GET.get('page_num', 1)
        page_size = request.GET.get('page_size', 10)
        comments = Comment.objects.filter(article=article).order_by('-created')
        paginator = Paginator(comments, per_page=page_size)
        try:
            page_comments = paginator.page(page_num)
        except EmptyPage:
            return HttpResponseBadRequest('页码为空')

        total_page = paginator.num_pages
        # 5、组装数据
        context = {
            'article': article,
            'category': article.category,
            'categories': categories,
            'hot_articles': hot_articles,
            'comments': page_comments,
            'page_num': page_num,
            'page_size': page_size,
            'total_page': total_page
        }
        return render(request, 'detail.html', context=context)

    def post(self, request):
        # 1、接收用户信息
        user = request.user
        # 2、判断用户是否登陆
        if user and user.is_authenticated:
            # 3、接收并保存数据
            id = request.POST.get('id')
            content = request.POST.get('content')
            try:
                article = Article.objects.get(id=id)
            except Article.DoesNotExist:
                return HttpResponseBadRequest('没有该文章')
            else:
                # 保存评论信息
                Comment.objects.create(content=content, article=article, user=user)
                # 更新文章评论数
                article.comment_counts += 1
                article.save()
                return redirect(reverse('home:detail') + '?id={}'.format(article.id))
        else:
            # 4、未登录跳转到登录页面
            return redirect(reverse('users:login'))
