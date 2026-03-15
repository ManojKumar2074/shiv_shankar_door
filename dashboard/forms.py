from django import forms
from doors.models import Door


class DoorProductForm(forms.ModelForm):

    # ── Updated choices to match client requirements ──────────────────────
    HEIGHT_CHOICES = [
        ('72', '72"'),
        ('75', '75"'),
        ('78', '78"'),
        ('81', '81"'),
        ('84', '84"'),
        ('custom', 'As per customer request'),
    ]
    WIDTH_CHOICES = [
        ('26', '26"'),
        ('28', '28"'),
        ('30', '30"'),
        ('32', '32"'),
        ('34', '34"'),
        ('36', '36"'),
        ('custom', 'As per customer request'),
    ]
    THICKNESS_CHOICES = [
        ('30', '30 mm'),
        ('32', '32 mm'),
    ]

    # ── Multi-select pill fields ──────────────────────────────────────────
    category = forms.MultipleChoiceField(
        choices=Door.CATEGORY_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'dash-checkbox-group'}),
    )
    height = forms.MultipleChoiceField(
        choices=HEIGHT_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'dash-checkbox-group'}),
    )
    width = forms.MultipleChoiceField(
        choices=WIDTH_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'dash-checkbox-group'}),
    )
    thickness = forms.MultipleChoiceField(
        choices=THICKNESS_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'dash-checkbox-group'}),
    )
    finish_type = forms.MultipleChoiceField(
        choices=Door.FINISH_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'dash-checkbox-group'}),
    )

    # ── Pooja price ───────────────────────────────────────────────────────
    pooja_price = forms.IntegerField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'dash-input',
            'placeholder': 'e.g. 15000',
            'id': 'id_pooja_price',
        }),
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
                'class': 'dash-input',
                'id': 'id_name',
                'placeholder': 'e.g. Royal Teak Double Door',
            }),
            'material': forms.Select(attrs={
                'class': 'dash-select',
                'id': 'id_material',
            }),
            'sft_rate': forms.Select(attrs={
                'class': 'dash-select',
                'id': 'id_sft_rate',
            }),
            'description': forms.Textarea(attrs={
                'class': 'dash-textarea',
                'rows': 4,
                'id': 'id_description',
                'placeholder': 'Describe the door design, style, and key characteristics…',
            }),
            'features': forms.Textarea(attrs={
                'class': 'dash-textarea',
                'rows': 5,
                'id': 'id_features',
                'placeholder': 'Anti-termite treated\nWater resistant\nISI certified hinges',
            }),
            'is_featured': forms.CheckboxInput(attrs={
                'class': 'dash-checkbox',
                'id': 'id_is_featured',
            }),
            'image_main': forms.FileInput(attrs={
                'class': 'dash-file-input',
                'accept': 'image/*',
                'id': 'id_image_main',
                'style': 'position:absolute;inset:0;width:100%;height:100%;opacity:0;cursor:pointer;z-index:3;',
            }),
            'image_2': forms.FileInput(attrs={
                'class': 'dash-file-input',
                'accept': 'image/*',
                'id': 'id_image_2',
                'style': 'position:absolute;inset:0;width:100%;height:100%;opacity:0;cursor:pointer;z-index:3;',
            }),
            'image_3': forms.FileInput(attrs={
                'class': 'dash-file-input',
                'accept': 'image/*',
                'id': 'id_image_3',
                'style': 'position:absolute;inset:0;width:100%;height:100%;opacity:0;cursor:pointer;z-index:3;',
            }),
            'image_4': forms.FileInput(attrs={
                'class': 'dash-file-input',
                'accept': 'image/*',
                'id': 'id_image_4',
                'style': 'position:absolute;inset:0;width:100%;height:100%;opacity:0;cursor:pointer;z-index:3;',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Pre-populate multi-select fields when editing
        if self.instance and self.instance.pk:
            self.initial['category']    = self.instance.get_category_list()
            self.initial['finish_type'] = self.instance.get_finish_list()
            self.initial['height']      = self.instance.get_height_list()
            self.initial['width']       = self.instance.get_width_list()
            self.initial['thickness']   = self.instance.get_thickness_list()
            if self.instance.is_pooja():
                self.fields['pooja_price'].initial = self.instance.price_min
            self.fields['image_main'].required = False

        for f in ['image_2', 'image_3', 'image_4', 'sft_rate', 'pooja_price']:
            self.fields[f].required = False

    def clean_category(self):
        v = self.cleaned_data.get('category', [])
        if not v:
            raise forms.ValidationError('Select at least one category.')
        return ','.join(v)

    def clean_height(self):
        v = self.cleaned_data.get('height', [])
        if not v:
            raise forms.ValidationError('Select at least one height.')
        return ','.join(v)

    def clean_width(self):
        v = self.cleaned_data.get('width', [])
        if not v:
            raise forms.ValidationError('Select at least one width.')
        return ','.join(v)

    def clean_thickness(self):
        v = self.cleaned_data.get('thickness', [])
        if not v:
            raise forms.ValidationError('Select at least one thickness.')
        return ','.join(v)

    def clean_finish_type(self):
        v = self.cleaned_data.get('finish_type', [])
        if not v:
            raise forms.ValidationError('Select at least one finish.')
        return ','.join(v)

    def clean(self):
        cleaned = super().clean()
        category = cleaned.get('category', '')
        is_pooja = 'pooja' in [c.strip() for c in category.split(',') if c.strip()]
        if is_pooja:
            cleaned['sft_rate'] = None
        else:
            cleaned['pooja_price'] = None
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        is_pooja = 'pooja' in [c.strip() for c in instance.category.split(',') if c.strip()]

        if is_pooja:
            instance.price_min = self.cleaned_data.get('pooja_price')
            instance.price_max = None
            instance.sft_rate  = None
        else:
            instance.price_min = None
            instance.price_max = None

        if commit:
            if instance.pk is None:
                # Two-step save: need pk before images can go to door_<pk>/
                _image_fields = ['image_main', 'image_2', 'image_3', 'image_4']
                _image_data = {f: getattr(instance, f) for f in _image_fields}
                for f in _image_fields:
                    setattr(instance, f, None)
                instance.save()
                for f in _image_fields:
                    if _image_data[f]:
                        setattr(instance, f, _image_data[f])
                instance.save()
            else:
                instance.save()

        return instance