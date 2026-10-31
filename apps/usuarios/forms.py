"""
Formularios para gestión de usuarios y asignación de roles.
"""
from django import forms
from apps.usuarios.models import Usuario


class UsuarioCrearForm(forms.ModelForm):
    """Formulario para que el administrador registre usuarios y asigne roles."""
    password = forms.CharField(
        label="Contraseña inicial",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Ej: Secreta123!"}),
        help_text="Mínimo 8 caracteres recomendado.",
    )
    password_confirm = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Repite la contraseña"}),
    )

    class Meta:
        model = Usuario
        fields = ["username", "first_name", "last_name", "email", "telefono", "rol"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control", "placeholder": "ej: mlopez"}),
            "first_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre"}),
            "last_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Apellido"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "correo@dulcearte.cl"}),
            "telefono": forms.TextInput(attrs={"class": "form-control", "placeholder": "+56 9 1234 5678"}),
            "rol": forms.Select(attrs={"class": "form-select fw-semibold"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("password")
        p2 = cleaned_data.get("password_confirm")
        if p1 and p2 and p1 != p2:
            self.add_error("password_confirm", "Las contraseñas no coinciden.")
        return cleaned_data

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.set_password(self.cleaned_data["password"])
        # Si es Admin, darle acceso al Django Admin
        if usuario.rol == Usuario.Rol.ADMIN:
            usuario.is_staff = True
        if commit:
            usuario.save()
        return usuario


class UsuarioEditarForm(forms.ModelForm):
    """Formulario para editar datos y cambiar de rol a un usuario."""
    nueva_password = forms.CharField(
        label="Nueva contraseña (opcional)",
        required=False,
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Dejar vacío si no se desea cambiar"}),
    )

    class Meta:
        model = Usuario
        fields = ["first_name", "last_name", "email", "telefono", "rol", "is_active"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "telefono": forms.TextInput(attrs={"class": "form-control"}),
            "rol": forms.Select(attrs={"class": "form-select fw-bold"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def save(self, commit=True):
        usuario = super().save(commit=False)
        nueva_pass = self.cleaned_data.get("nueva_password")
        if nueva_pass:
            usuario.set_password(nueva_pass)
        if usuario.rol == Usuario.Rol.ADMIN:
            usuario.is_staff = True
        if commit:
            usuario.save()
        return usuario
