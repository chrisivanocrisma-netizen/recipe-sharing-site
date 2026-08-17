from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import UserProfile

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Remove all password validators
        self.fields['password1'].validators = []
        self.fields['password2'].validators = []
        
        # Remove help text
        self.fields['password1'].help_text = ''
        self.fields['password2'].help_text = ''
        
        # Update widget attrs
        for field in self.fields:
            placeholder = f'Enter {field}'
            if field == 'password1':
                placeholder = 'Enter any password'
            elif field == 'password2':
                placeholder = 'Confirm password'
            
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
                'placeholder': placeholder
            })
    
    def clean_password1(self):
        # Accept any password, no validation
        password1 = self.cleaned_data.get("password1")
        # Kahit 1 character lang, o kahit same sa username - OKAY LAHAT
        if not password1:
            raise ValidationError("This field is required.")
        return password1
    
    def clean_password2(self):
        # Only check if passwords match
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        
        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords don't match")
        return password2
    
    def _post_clean(self):
        """Override to COMPLETELY REMOVE Django's password validations"""
        # Skip UserCreationForm's _post_clean entirely
        # Call ModelForm's _post_clean instead
        super(forms.ModelForm, self)._post_clean()
        
        # Validate username uniqueness
        try:
            self.instance.validate_unique()
        except ValidationError as e:
            self._update_errors(e)

# ... keep the rest of your forms unchanged
class UserLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter username or email'
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter password'
        })

class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField()
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class': 'form-control'
            })

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['bio', 'profile_picture', 'location', 'website']
        widgets = {
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Tell us about yourself...'
            }),
            'profile_picture': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your location'
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your website URL'
            }),
        }