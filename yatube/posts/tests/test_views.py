from django import forms
from django.test import Client, TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from ..models import Post, Group, User, Comment, Follow


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username="EvgeniyKutyashov")
        cls.group = Group.objects.create(
            title="Тестовая группа",
            slug="test-slug",
            description="Тестовое описание",
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text="Тестовый пост",
            group=cls.group,
        )
        cls.templates_pages_names = {
            reverse("posts:index"): "posts/index.html",
            reverse(
                "posts:group_list", kwargs={"slug": cls.group.slug}
            ): "posts/group_list.html",
            reverse(
                "posts:profile", kwargs={"username": cls.post.author}
            ): "posts/profile.html",
            reverse(
                "posts:post_detail", kwargs={"post_id": cls.post.id}
            ): "posts/post_detail.html",
            reverse(
                "posts:post_edit", kwargs={"post_id": cls.post.id}
            ): "posts/create_post.html",
            reverse("posts:post_create"): "posts/create_post.html",
        }
        cls.url_names = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': f'{cls.group.slug}'}),
            reverse('posts:profile', kwargs={'username': f'{cls.user}'})
        ]

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostPagesTests.user)

    def test_pages_uses_correct_template(self):
        for template, reverse_name in self.templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(template)
                self.assertTemplateUsed(response, reverse_name)

    def test_check_group_in_pages(self):
        form_fields = {
            reverse("posts:index"): Post.objects.get(group=self.post.group),
            reverse(
                "posts:group_list", kwargs={"slug": self.group.slug}
            ): Post.objects.get(group=self.post.group),
            reverse(
                "posts:profile", kwargs={"username": self.post.author}
            ): Post.objects.get(group=self.post.group),
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                response = self.authorized_client.get(value)
                form_field = response.context["page_obj"]
                self.assertIn(expected, form_field)

    def test_check_group_not_in_mistake_group_list_page(self):
        form_fields = {
            reverse(
                "posts:group_list", kwargs={"slug": self.group.slug}
            ): Post.objects.exclude(group=self.post.group),
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                response = self.authorized_client.get(value)
                form_field = response.context["page_obj"]
                self.assertNotIn(expected, form_field)

    def test_index_show_correct_context(self):
        response = self.guest_client.get(reverse("posts:index"))
        expected = list(Post.objects.all()[:10])
        self.assertEqual(list(response.context["page_obj"]), expected)

    def test_group_list_show_correct_context(self):
        response = self.guest_client.get(
            reverse("posts:group_list", kwargs={"slug": self.group.slug})
        )
        expected = list(Post.objects.filter(group_id=self.group.pk))
        self.assertEqual(list(response.context["page_obj"]), expected)

    def test_profile_show_correct_context(self):
        response = self.guest_client.get(
            reverse("posts:profile", args=(self.post.author,))
        )
        expected = list(Post.objects.filter(author_id=self.user.pk))
        self.assertEqual(list(response.context["page_obj"]), expected)

    def test_post_detail_show_correct_context(self):
        response = self.guest_client.get(
            reverse("posts:post_detail", kwargs={"post_id": self.post.pk})
        )
        self.assertEqual(response.context.get("post").text, self.post.text)
        self.assertEqual(response.context.get("post").author, self.post.author)
        self.assertEqual(response.context.get("post").group, self.post.group)

    def test_create_edit_show_correct_context(self):
        response = self.authorized_client.get(
            reverse("posts:post_edit", kwargs={"post_id": self.post.id})
        )
        form_fields = {
            "text": forms.fields.CharField,
            "group": forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context["form"].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_create_show_correct_context(self):
        response = self.authorized_client.get(reverse("posts:post_create"))
        form_fields = {
            "text": forms.fields.CharField,
            "group": forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context["form"].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_new_post_with_pictures_in_right_place(self):
        """Новый пост с img есть на страницах index, group, profile, detail"""
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        post_wth_pic = Post.objects.create(
            text='Новый текст с картинкой',
            author=self.user,
            group=self.group,
            image=uploaded,
        )
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': post_wth_pic.id})
        )
        self.assertEqual(response.context.get('post'), post_wth_pic)
        for name in self.url_names:
            with self.subTest(name=name):
                response = self.authorized_client.get(name)
                self.assertEqual(post_wth_pic, response.context['page_obj'][0])
                self.assertEqual(response.context['page_obj'][0].image,
                                 post_wth_pic.image.name)

    def test_comment_correct_context(self):
        """Валидная форма Комментария создает запись в Post."""
        comments_count = Comment.objects.count()
        form_data = {"text": "Тестовый коммент"}
        response = self.authorized_client.post(
            reverse("posts:add_comment", kwargs={"post_id": self.post.id}),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response, reverse("posts:post_detail",
                              kwargs={"post_id": self.post.id})
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertTrue(Comment.objects.filter(text="Тестовый коммент")
                        .exists())

    def test_check_cache(self):
        """Проверка кеша."""
        response = self.guest_client.get(reverse("posts:index"))
        r_1 = response.content
        Post.objects.get(id=1).delete()
        response2 = self.guest_client.get(reverse("posts:index"))
        r_2 = response2.content
        self.assertEqual(r_1, r_2)
        cache.clear()
        self.assertNotEqual(r_2, self.guest_client.get(
            reverse('posts:index')
        ).content)

    def test_follow_page(self):
        # Проверяем, что страница подписок пуста
        response = self.authorized_client.get(reverse("posts:follow_index"))
        self.assertEqual(len(response.context["page_obj"]), 0)
        # Проверка подписки на автора поста
        Follow.objects.get_or_create(user=self.user, author=self.post.author)
        r_2 = self.authorized_client.get(reverse("posts:follow_index"))
        self.assertEqual(len(r_2.context["page_obj"]), 1)
        # проверка подписки у юзера-фоловера
        self.assertIn(self.post, r_2.context["page_obj"])

        # Проверка что пост не появился в избранных у юзера-обычного
        outsider = User.objects.create(username="NoName")
        self.authorized_client.force_login(outsider)
        r_2 = self.authorized_client.get(reverse("posts:follow_index"))
        self.assertNotIn(self.post, r_2.context["page_obj"])

        # Проверка отписки от автора поста
        Follow.objects.all().delete()
        r_3 = self.authorized_client.get(reverse("posts:follow_index"))
        self.assertEqual(len(r_3.context["page_obj"]), 0)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='EvgeniyKutyashov')
        for i in range(13):
            Post.objects.bulk_create([
                Post(author=cls.user,
                     text='Тестовый пост',
                     )
            ])

    def setUp(self):
        self.logined_client = Client()
        self.logined_client.force_login(self.user)

    def test_paginator_correct_post_count(self):
        pages_count_posts = {
            reverse('posts:index'): 10,
            reverse('posts:index') + '?page=2': 3,
        }
        for page, expected in pages_count_posts.items():
            with self.subTest(page=page):
                response = self.logined_client.get(page)
                count = len(response.context["page_obj"])
                self.assertEqual(count, expected)
