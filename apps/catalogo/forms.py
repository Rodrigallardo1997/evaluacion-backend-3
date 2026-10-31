"""
Formularios para Insumos, Recetas y Ajustes de Stock.
"""
from decimal import Decimal
from django import forms
from apps.catalogo.models import Insumo, Receta, RecetaInsumo


class InsumoForm(forms.ModelForm):
    class Meta:
        model = Insumo
        fields = [
            "nombre",
            "categoria",
            "unidad",
            "stock_actual",
            "stock_minimo",
            "costo_unitario",
            "perecedero",
            "fecha_vencimiento",
            "activo",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "categoria": forms.Select(attrs={"class": "form-select"}),
            "unidad": forms.Select(attrs={"class": "form-select"}),
            "stock_actual": forms.NumberInput(attrs={"class": "form-control", "step": "0.001"}),
            "stock_minimo": forms.NumberInput(attrs={"class": "form-control", "step": "0.001"}),
            "costo_unitario": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "perecedero": forms.CheckboxInput(attrs={"class": "form-check-input", "id": "checkPerecedero"}),
            "fecha_vencimiento": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class AjusteStockForm(forms.Form):
    tipo = forms.ChoiceField(
        choices=[("ENTRADA", "Entrada (Compra/Recepción)"), ("SALIDA", "Salida (Uso/Retiro)"), ("MERMA", "Merma (Desperdicio)"), ("AJUSTE", "Ajuste de Inventario (Fijar stock exacto)")],
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    cantidad = forms.DecimalField(
        max_digits=10,
        decimal_places=3,
        min_value=Decimal("0.001"),
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.001"}),
    )
    motivo = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: Compra proveedor Molino San Juan"}),
    )


class RecetaForm(forms.ModelForm):
    class Meta:
        model = Receta
        fields = [
            "nombre",
            "categoria",
            "descripcion",
            "rendimiento",
            "precio_base",
            "margen_deseado",
            "tiempo_preparacion_min",
            "imagen",
            "activo",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "categoria": forms.Select(attrs={"class": "form-select"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "rendimiento": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
            "precio_base": forms.NumberInput(attrs={"class": "form-control", "step": "100"}),
            "margen_deseado": forms.NumberInput(attrs={"class": "form-control", "step": "1"}),
            "tiempo_preparacion_min": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
            "imagen": forms.FileInput(attrs={"class": "form-control"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
