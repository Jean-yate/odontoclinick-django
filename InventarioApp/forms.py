from django import forms
from .models import MovimientoInventario, Producto

class EntradaStockForm(forms.ModelForm):
    class Meta:
        model = MovimientoInventario
        fields = ['cantidad', 'motivo']
        widgets = {
            'cantidad': forms.NumberInput(attrs={'class': 'form-control rounded-pill', 'placeholder': 'Ej: 10'}),
            'motivo': forms.TextInput(attrs={'class': 'form-control rounded-pill', 'placeholder': 'Ej: Compra mensual / Donación'}),
        }


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            'codigo_producto', # <-- AGREGADO AQUÍ
            'nombre_producto', 
            'descripcion', 
            'id_categoria', 
            'stock_actual', 
            'stock_minimo', 
            'precio_compra', 
            'precio_venta'
        ]
        widgets = {
            'codigo_producto': forms.TextInput(attrs={'class': 'form-control rounded-pill', 'placeholder': 'Ej: PROD-001'}),
            'nombre_producto': forms.TextInput(attrs={'class': 'form-control rounded-pill'}),
            'id_categoria': forms.Select(attrs={'class': 'form-select rounded-pill'}),
            'stock_actual': forms.NumberInput(attrs={'class': 'form-control rounded-pill'}),
            'stock_minimo': forms.NumberInput(attrs={'class': 'form-control rounded-pill'}),
            'precio_compra': forms.NumberInput(attrs={'class': 'form-control rounded-pill'}),
            'precio_venta': forms.NumberInput(attrs={'class': 'form-control rounded-pill'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control rounded-4', 'rows': 2}),
        }