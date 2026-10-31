"""
Formularios para Rutas de Despacho y Confirmación de Entregas.
"""
from django import forms
from apps.despachos.models import RutaDespacho, Despacho
from apps.usuarios.models import Usuario


class RutaDespachoForm(forms.ModelForm):
    class Meta:
        model = RutaDespacho
        fields = ["fecha", "repartidor", "vehiculo", "observaciones"]
        widgets = {
            "fecha": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "repartidor": forms.Select(attrs={"class": "form-select"}),
            "vehiculo": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: Furgón Peugeot Partner ABCD-12"}),
            "observaciones": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["repartidor"].queryset = Usuario.objects.filter(
            rol=Usuario.Rol.REPARTIDOR, is_active=True
        )


class ConfirmarEntregaForm(forms.Form):
    receptor_nombre = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre completo de quien recibe"}),
    )
    firma_digital = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={"id": "firma_digital_input"}),
    )
    foto_comprobante = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={"class": "form-control", "id": "foto_comprobante_input", "accept": "image/*"}),
    )
    observaciones = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Observaciones de la entrega..."}),
    )
    latitud = forms.DecimalField(
        required=False,
        widget=forms.HiddenInput(attrs={"id": "latitud_input"}),
    )
    longitud = forms.DecimalField(
        required=False,
        widget=forms.HiddenInput(attrs={"id": "longitud_input"}),
    )
