from django import forms
from .models import Inquiry, Door


class InquiryForm(forms.ModelForm):
    class Meta:
        model = Inquiry
        fields = ['name', 'phone', 'email', 'location', 'message']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your Full Name'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+91 98765 43210'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'your@email.com'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City, State'
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Tell us about your requirements — dimensions, quantity, finish preference...',
                'rows': 5
            }),
        }


class ContactForm(forms.Form):
    name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Your Full Name'
    }))
    phone = forms.CharField(max_length=15, widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': '+91 98765 43210'
    }))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={
        'class': 'form-control', 'placeholder': 'your@email.com'
    }))
    message = forms.CharField(widget=forms.Textarea(attrs={
        'class': 'form-control', 'placeholder': 'How can we help you?', 'rows': 5
    }))

class DoorProductForm(forms.ModelForm):
    # Single plain price field for Pooja Room doors (replaces price_min / price_max)
    pooja_price = forms.IntegerField(
        required=False,
        min_value=0,
        label='Price (₹)',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. 15000',
        }),
        help_text='Enter the price for this Pooja Room door in ₹',
    )

    class Meta:
        model = Door
        fields = [
            'name', 'category', 'material', 'description',
            'height', 'width', 'thickness', 'finish_type',
            'sft_rate',
            'image_main', 'image_2', 'image_3', 'image_4',
            'features', 'is_featured',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Door product name'
            }),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'material': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 4,
                'placeholder': 'Describe the door design, style, and key features…'
            }),
            'height': forms.Select(attrs={'class': 'form-control'}),
            'width': forms.Select(attrs={'class': 'form-control'}),
            'thickness': forms.Select(attrs={'class': 'form-control'}),
            'finish_type': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. matte  or  matte,gloss'
            }),
            'sft_rate': forms.Select(attrs={'class': 'form-control'}),
            'features': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 4,
                'placeholder': 'One feature per line'
            }),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Pre-populate pooja_price from instance when editing
        if self.instance and self.instance.pk and self.instance.is_pooja():
            self.fields['pooja_price'].initial = self.instance.price_min

        # sft_rate is only relevant for non-pooja doors — not required at field level;
        # custom validation below handles the logic per category.
        self.fields['sft_rate'].required = False

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')

        if category == 'pooja':
            # Pooja Room: plain price field, no min/max enforced — just save to price_min
            # sft_rate not needed
            cleaned_data['sft_rate'] = None
        else:
            # Non-pooja: price fields not needed at all
            cleaned_data['pooja_price'] = None

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        if instance.category == 'pooja':
            # Store single price into price_min; clear price_max and sft_rate
            price = self.cleaned_data.get('pooja_price')
            instance.price_min = price
            instance.price_max = None
            instance.sft_rate = None
        else:
            # Non-pooja: clear pooja price fields
            instance.price_min = None
            instance.price_max = None

        if commit:
            instance.save()
        return instance


class PreviewRequestForm(forms.Form):
    """Validates everything the AI-preview endpoint receives from the browser."""

    MAX_UPLOAD_BYTES = 10 * 1024 * 1024
    MAX_PIXELS = 40_000_000
    ALLOWED_FORMATS = {'JPEG', 'PNG', 'WEBP'}

    door_id = forms.ModelChoiceField(
        queryset=Door.objects.all(),
        error_messages={
            'required': 'Please select a door.',
            'invalid_choice': 'That door does not exist.',
        },
    )

    house_image = forms.ImageField(
        error_messages={
            'required': 'Please upload a photo of your entrance.',
            'invalid_image': 'Please upload a valid JPG, PNG or WebP photo.',
        },
    )

    rect_x = forms.FloatField(min_value=0, max_value=100)
    rect_y = forms.FloatField(min_value=0, max_value=100)
    rect_w = forms.FloatField(min_value=1, max_value=100)
    rect_h = forms.FloatField(min_value=1, max_value=100)

    def clean_house_image(self):
        f = self.cleaned_data['house_image']

        if f.size > self.MAX_UPLOAD_BYTES:
            raise forms.ValidationError(
                'Photo is too large. Maximum size is 10 MB.'
            )

        img = f.image

        if img.format not in self.ALLOWED_FORMATS:
            raise forms.ValidationError(
                'Only JPG, PNG or WebP photos are supported.'
            )

        if img.width * img.height > self.MAX_PIXELS:
            raise forms.ValidationError(
                'Photo resolution is too high. Please upload a smaller photo.'
            )

        f.seek(0)
        return f

    def clean(self):
        data = super().clean()

        try:
            if (
                data['rect_x'] + data['rect_w'] > 100
                or data['rect_y'] + data['rect_h'] > 100
            ):
                raise forms.ValidationError(
                    'The marked area must stay inside the photo.'
                )
        except KeyError:
            pass

        return data