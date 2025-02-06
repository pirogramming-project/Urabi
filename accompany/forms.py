from django import forms
from .models import TravelGroup

class TravelGroupForm(forms.ModelForm):
    class Meta:
        model = TravelGroup
        fields = ['title', 'city', 'explanation', 'start_date', 'end_date', 'max_member', 'tags', 'photo','gender','min_age','max_age']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': '제목', 'id':'title'}),
            'city': forms.TextInput(attrs={'placeholder': '도시', 'id':'city'}),
            'explanation': forms.Textarea(attrs={'placeholder': '설명을 입력하세요!','id':'description'}),
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'max_member': forms.NumberInput(attrs={'placeholder': '최대 인원', 'id':'max_member'}),
            'tags': forms.TextInput(attrs={'placeholder': '장소 태그', 'id':'tags'}),
            'photo': forms.ClearableFileInput(attrs={'class': 'file-upload-input', 'id':'image-upload'}),
            'gender':forms.Select(attrs={'id':'gender'}),
            'min_age':forms.NumberInput(attrs={'placeholder':'최소 나이','id':'min_age'}),
            'max_age':forms.NumberInput(attrs={'placeholder':'최대 나이','id':'max_age'})
        }
        tags = forms.CharField(
            required=False, 
            widget=forms.HiddenInput()
        )
