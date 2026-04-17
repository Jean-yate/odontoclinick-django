from django import forms
from .models import MovimientoInventario, Producto
from django.core.exceptions import ValidationError

class EntradaStockForm(forms.ModelForm):
    class Meta:
        model = MovimientoInventario
        fields = ['cantidad', 'motivo']
        widgets = {
            'cantidad': forms.NumberInput(attrs={'class': 'form-control rounded-pill', 'placeholder': 'Ej: 10'}),
            'motivo': forms.TextInput(attrs={'class': 'form-control rounded-pill', 'placeholder': 'Ej: Compra mensual / Donación'}),
        }

    # Validación para Entrada de Stock: Solo enteros positivos
    def clean_cantidad(self):
        cantidad = self.cleaned_data.get('cantidad')
        if cantidad is not None:
            if cantidad <= 0:
                raise ValidationError("La cantidad a ingresar debe ser mayor a cero.")
            if cantidad != int(cantidad):
                raise ValidationError("No se permiten fracciones; ingresa un número entero.")
        return cantidad


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            'codigo_producto', 
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

    # 1. Validación: Código Obligatorio
    def clean_codigo_producto(self):
        codigo = self.cleaned_data.get('codigo_producto')
        if not codigo or codigo.strip() == "":
            raise ValidationError("El código es obligatorio para identificar el suministro.")
        return codigo

    # 2. Validación: Stock sin decimales y no negativo
    def clean_stock_actual(self):
        stock = self.cleaned_data.get('stock_actual')
        if stock is not None:
            if stock < 0:
                raise ValidationError("El stock no puede ser negativo.")
            if stock != int(stock):
                raise ValidationError("El stock debe ser un número entero.")
        return stock

    # 3. Validación: Stock mínimo no negativo
    def clean_stock_minimo(self):
        minimo = self.cleaned_data.get('stock_minimo')
        if minimo is not None and minimo < 0:
            raise ValidationError("El stock mínimo no puede ser negativo.")
        return minimo

    # 4. Validación: Precios no negativos
    def clean_precio_venta(self):
        precio = self.cleaned_data.get('precio_venta')
        if precio is not None and precio < 0:
            raise ValidationError("El precio de venta no puede ser negativo.")
        return precio