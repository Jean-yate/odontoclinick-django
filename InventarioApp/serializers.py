# InventarioApp/serializers.py
from rest_framework import serializers
from .models import Producto, CategoriaProducto

class ProductoSerializer(serializers.ModelSerializer):
    
    # Esto le dice a data_wizard cómo resolver el id_categoria del CSV
    id_categoria = serializers.PrimaryKeyRelatedField(
        queryset=CategoriaProducto.objects.all()
    )

    fecha_vencimiento = serializers.DateField(
        format='%Y-%m-%d',
        input_formats=['%Y-%m-%d']
    )

    class Meta:
        model = Producto
        fields = [
            'codigo_producto',
            'nombre_producto',
            'descripcion',
            'precio_compra',
            'precio_venta',
            'stock_actual',
            'stock_minimo',
            'fecha_vencimiento',
            'activo',
            'id_categoria',
            'unidad_medida',
        ]

def create(self, validated_data):
    codigo = validated_data.get('codigo_producto')
    if codigo:
        producto, creado = Producto.objects.update_or_create(
            codigo_producto=codigo,
            defaults=validated_data
        )
        return producto
    return Producto.objects.create(**validated_data)