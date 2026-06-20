from django import forms
from .models import MovimientoInventario, Producto, Empresa, ProductoEmpresa
from django.core.exceptions import ValidationError
import re


class EntradaStockForm(forms.Form):
    cantidad = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control input-clay', 'placeholder': 'Ej: 10'})
    )
    motivo = forms.CharField(
        required=False, max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control input-clay', 'placeholder': 'Ej: Compra mensual'})
    )
    empresa = forms.ModelChoiceField(
        # Bug fix: mostrar TODAS las empresas, no solo es_proveedor=True,
        # porque en la BD todas tienen es_comprador=False pero se usan para compras.
        queryset=Empresa.objects.all().order_by('nombre_empresa'),
        required=False,
        empty_label="— Sin empresa / Ajuste interno —",
        widget=forms.Select(attrs={'class': 'form-select input-clay'})
    )
    precio_transaccion = forms.IntegerField(
        required=False, min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control input-clay', 'placeholder': 'Precio por unidad'})
    )

    def clean(self):
        cleaned = super().clean()
        empresa = cleaned.get('empresa')
        precio  = cleaned.get('precio_transaccion')
        if empresa and precio is None:
            self.add_error('precio_transaccion', "Indica el precio de compra por unidad para esta empresa.")
        return cleaned


class SalidaStockForm(forms.Form):
    cantidad = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control input-clay', 'placeholder': 'Ej: 5'})
    )
    motivo = forms.CharField(
        required=False, max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control input-clay', 'placeholder': 'Ej: Uso clínico'})
    )
    DESTINO_CHOICES = [
        ('', '— Solo consumo / sin destinatario —'),
        ('empresa', 'Empresa compradora'),
        ('cliente', 'Cliente / usuario interno'),
    ]
    tipo_destino = forms.ChoiceField(
        choices=DESTINO_CHOICES, required=False,
        widget=forms.Select(attrs={'class': 'form-select input-clay'})
    )
    # Bug fix: TODAS las empresas (en BD es_comprador=0 para todas)
    empresa = forms.ModelChoiceField(
        queryset=Empresa.objects.all().order_by('nombre_empresa'),
        required=False,
        empty_label="— Selecciona empresa —",
        widget=forms.Select(attrs={'class': 'form-select input-clay'})
    )
    # cliente_id: se resuelve en la view con Usuario.objects.get(pk=...)
    # Se envía como hidden field populado por el buscador AJAX
    cliente_id = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput()
    )
    precio_transaccion = forms.IntegerField(
        required=False, min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control input-clay', 'placeholder': 'Precio cobrado (opcional)'})
    )

    def clean(self):
        cleaned = super().clean()
        tipo      = cleaned.get('tipo_destino')
        empresa   = cleaned.get('empresa')
        cliente_id = cleaned.get('cliente_id')
        if tipo == 'empresa' and not empresa:
            self.add_error('empresa', "Selecciona la empresa compradora.")
        if tipo == 'cliente' and not cliente_id:
            self.add_error('cliente_id', "Selecciona un cliente.")
        return cleaned


class EmpresaForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = ['nombre_empresa', 'nit', 'es_proveedor', 'es_comprador']
        widgets = {
            'nombre_empresa': forms.TextInput(attrs={
                'class': 'form-control input-clay',
                'placeholder': 'Ej: Depósito Dental Central'
            }),
            'nit': forms.TextInput(attrs={
                'class': 'form-control input-clay',
                'placeholder': 'Ej: 900123456-1'
            }),
            'es_proveedor': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'es_comprador': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_nombre_empresa(self):
        nombre = self.cleaned_data.get('nombre_empresa', '').strip()
        if len(nombre) < 3:
            raise ValidationError("El nombre debe tener al menos 3 caracteres.")
        return nombre

    def clean_nit(self):
        nit = self.cleaned_data.get('nit', '').strip()
        if not nit:
            raise ValidationError("El NIT es obligatorio.")
        return nit


class ProductoForm(forms.ModelForm):
    descripcion = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control rounded-4', 'rows': 2,
                                     'placeholder': 'Escribe una nota sobre el producto...'}),
        required=True, label="Notas adicionales"
    )

    class Meta:
        model = Producto
        fields = ['codigo_producto', 'nombre_producto', 'descripcion',
                  'id_categoria', 'stock_actual', 'stock_minimo', 'precio_venta']
        widgets = {
            'codigo_producto': forms.TextInput(attrs={'class': 'form-control rounded-pill', 'placeholder': 'Ej: PROD-001'}),
            'nombre_producto': forms.TextInput(attrs={'class': 'form-control rounded-pill'}),
            'id_categoria': forms.Select(attrs={'class': 'form-select rounded-pill'}),
            'stock_actual': forms.NumberInput(attrs={'class': 'form-control rounded-pill'}),
            'stock_minimo': forms.NumberInput(attrs={'class': 'form-control rounded-pill'}),
            'precio_venta': forms.NumberInput(attrs={'class': 'form-control rounded-pill', 'placeholder': 'Ej: 45000'}),
        }

    def clean_nombre_producto(self):
        nombre = self.cleaned_data.get('nombre_producto', '').strip()
        if len(nombre) < 3:
            raise ValidationError("El nombre es demasiado corto (mínimo 3 caracteres).")
        if len(nombre) > 100:
            raise ValidationError("El nombre no puede superar 100 caracteres.")
        if not re.match(r'^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑüÜ\s\-\.]+$', nombre):
            raise ValidationError("Solo se permiten letras, números, espacios, guiones y puntos.")
        return nombre

    def clean_codigo_producto(self):
        codigo = self.cleaned_data.get('codigo_producto', '').strip()
        if not codigo:
            raise ValidationError("El código es obligatorio.")
        if not re.match(r'^[a-zA-Z0-9]+-[0-9]+$', codigo):
            raise ValidationError("Formato inválido. Debe ser letras/números + guión + número (Ej: PROD-001).")
        return codigo

    def clean_stock_actual(self):
        stock = self.cleaned_data.get('stock_actual')
        if stock is not None and stock < 0:
            raise ValidationError("El stock no puede ser negativo.")
        return int(stock)

    def clean_stock_minimo(self):
        minimo = self.cleaned_data.get('stock_minimo')
        if minimo is not None and minimo < 0:
            raise ValidationError("El stock mínimo no puede ser negativo.")
        return int(minimo)

    def clean_precio_venta(self):
        precio = self.cleaned_data.get('precio_venta')
        if precio is not None and precio < 0:
            raise ValidationError("El precio no puede ser negativo.")
        return int(precio)