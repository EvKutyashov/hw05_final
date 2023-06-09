from http import HTTPStatus
from django.test import Client, TestCase
from django.urls import reverse
from ..models import Post, Group, User


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username="NoName")
        cls.second = User.objects.create(username='SecondUser')
        cls.group = Group.objects.create(
            title="Тестовая группа",
            slug="test-slug",
            description="Тестовое описание",
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text="Тестовый пост",
        )
        cls.templates = [
            "/",
            f"/group/{cls.group.slug}/",
            f"/profile/{cls.user}/",
            f"/posts/{cls.post.pk}/",
        ]
        cls.templates_url_names = {
            "/": "posts/index.html",
            f"/group/{cls.group.slug}/": "posts/group_list.html",
            f"/profile/{cls.user.username}/": "posts/profile.html",
            f"/posts/{cls.post.pk}/": "posts/post_detail.html",
            f"/posts/{cls.post.pk}/edit/": "posts/create_post.html",
            "/create/": "posts/create_post.html",
        }

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostURLTests.user)
        self.second_client = Client()
        self.second_client.force_login(PostURLTests.second)

    def test_urls_exists_at_desired_location(self):
        for adress in self.templates:
            with self.subTest(adress):
                response = self.guest_client.get(adress)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_posts_post_id_edit_url_exists_at_author(self):
        """Страница /posts/post_id/edit/ доступна только автору."""
        self.user = User.objects.get(username=self.user)
        self.authorized_client = Client()
        self.authorized_client.force_login(PostURLTests.user)
        response = self.authorized_client.get(
            reverse('posts:post_edit', args=[self.post.pk]), follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_create_url_redirect_anonymous_on_auth_login(self):
        """Страница /create/ перенаправит анонимного пользователя
        на страницу логина."""
        response = self.guest_client.get("/create/", follow=True)
        self.assertRedirects(response, "/auth/login/?next=/create/")

    def test_unexisting_page_at_desired_location(self):
        """Страница /unexisting_page/ должна выдать ошибку."""
        response = self.guest_client.get("/unexisting_page/")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_edit_url_redirect_anonymous_on_auth_login(self):
        """Страница /edit/ перенаправит анонимного пользователя
        на страницу логина.
        """
        response = self.guest_client.get(f'/posts/{self.post.pk}/edit/',
                                         follow=True)
        self.assertRedirects(
            response, f'/auth/login/?next=/posts/{self.post.pk}/edit/')

    def test_edit_url_redirect_authorized_on_post_id(self):
        """Страница /edit/ перенаправит авторизованного пользователя
        на страницу поста.
        """
        response = self.second_client.get(
            reverse('posts:post_edit', args=[self.post.pk]),
            follow=True)
        self.assertRedirects(
            response, reverse('posts:post_detail', args=[self.post.pk])
        )

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        for url, template in self.templates_url_names.items():
            with self.subTest(template=template):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)
