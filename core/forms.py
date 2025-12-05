from django import forms
from .models import Category, MenuItem

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Category name'}),
        }



class MenuItemForm(forms.ModelForm):
    class Meta:
        model = MenuItem
        fields = ['category', 'name', 'price', 'image']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Food name'}),
            'price': forms.NumberInput(attrs={'placeholder': 'Price in ₹'}),
            'category': forms.Select(),  # placeholder handled via empty_label
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
