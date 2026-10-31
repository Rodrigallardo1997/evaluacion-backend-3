"""
Formularios para Pedidos y Clientes.
"""
from django import forms
from apps.pedidos.models import Cliente, Pedido, DetallePedido, Pago


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            "nombre_completo",
            "rut",
            "telefono",
            "email",
            "direccion",
            "referencia_direccion",
            "notas",
            "activo",
        ]
        widgets = {
            "nombre_completo": forms.TextInput(attrs={"class": "form-control"}),
            "rut": forms.TextInput(attrs={"class": "form-control", "placeholder": "12.345.678-9"}),
            "telefono": forms.TextInput(attrs={"class": "form-control", "placeholder": "+56 9 1234 5678"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "direccion": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "referencia_direccion": forms.TextInput(attrs={"class": "form-control"}),
            "notas": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class PedidoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = [
            "cliente",
            "prioridad",
            "fecha_entrega",
            "direccion_entrega",
            "diseno_descripcion",
            "imagen_referencia",
            "observaciones",
            "descuento",
        ]
        widgets = {
            "cliente": forms.Select(attrs={"class": "form-select"}),
            "prioridad": forms.Select(attrs={"class": "form-select"}),
            "fecha_entrega": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"}
            ),
            "direccion_entrega": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "diseno_descripcion": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "placeholder": "Temática, colores, mensaje o dedicatoria..."}
            ),
            "imagen_referencia": forms.FileInput(attrs={"class": "form-control"}),
            "observaciones": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "descuento": forms.NumberInput(attrs={"class": "form-control", "min": "0", "step": "100"}),
        }

    def __init__(self, *args, **kwargs):
        es_cliente = kwargs.pop("es_cliente", False)
        super().__init__(*args, **kwargs)
        if es_cliente:
            self.fields["cliente"].required = False
            self.fields["cliente"].widget = forms.HiddenInput()
            self.fields["descuento"].required = False
            self.fields["descuento"].initial = 0
            self.fields["descuento"].widget = forms.HiddenInput()


class PagoForm(forms.ModelForm):
    class Meta:
        model = Pago
        fields = ["tipo", "metodo", "monto", "referencia", "comprobante"]
        widgets = {
            "tipo": forms.Select(attrs={"class": "form-select"}),
            "metodo": forms.Select(attrs={"class": "form-select"}),
            "monto": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
            "referencia": forms.TextInput(attrs={"class": "form-control"}),
            "comprobante": forms.FileInput(attrs={"class": "form-control"}),
        }
