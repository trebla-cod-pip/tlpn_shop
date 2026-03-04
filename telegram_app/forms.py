from django import forms
from telegram_app.models import Message


class MessageAdminForm(forms.ModelForm):
    """Форма для отправки сообщений в админке"""

    class Meta:
        model = Message
        fields = ['telegram_user', 'text', 'direction']
        widgets = {
            'telegram_user': forms.Select(attrs={'class': 'v-select-field'}),
            'text': forms.Textarea(attrs={'rows': 5, 'class': 'v-large-text-field'}),
            'direction': forms.Select(attrs={'class': 'v-select-field'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Для исходящих сообщений скрываем выбор направления
        if self.instance.pk and self.instance.direction == 'outgoing':
            self.fields['direction'].widget.attrs['disabled'] = True


class BulkMessageForm(forms.Form):
    """Форма для массовой отправки сообщений выбранным пользователям"""

    text = forms.CharField(
        label='Текст сообщения',
        widget=forms.Textarea(attrs={'rows': 5, 'placeholder': 'Введите текст сообщения...'}),
        help_text='Сообщение будет отправлено всем выбранным пользователям'
    )
