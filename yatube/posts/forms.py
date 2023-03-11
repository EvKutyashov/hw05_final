from django import forms
from .models import Post, Comment
from django.forms import ModelForm


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = {'text', 'group', 'image'}
        help_text = {
            'text': 'Текст поста',
            'group': 'Группа',
        }
        labels = {
            'text': 'Текст поста',
            'group': 'Группа поста',
        }

    def clean_subject(self):
        data = self.cleaned_data['text']
        if '' not in data():
            raise forms.ValidationError(
                'Поле надо заполнить'
            )
        return data


class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        labels = {'text': 'Текст комментария'}
