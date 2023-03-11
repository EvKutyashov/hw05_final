from django.core.paginator import Paginator
POSTS = 10


def get_page(request, posts):
    paginator = Paginator(posts, POSTS)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj
