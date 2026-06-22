"""
Script de datos iniciales para OdontoClinick.
Pobla: Especialidades, Categorías de Producto, Productos, Empresas y Tratamientos.
"""

import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.settings')
django.setup()

from MedicoApp.models import Especialidad
from InventarioApp.models import CategoriaProducto, Producto
from EmpresaApp.models import Empresa
from TratamientoApp.models import Tratamiento

print("=" * 60)
print("  Iniciando carga de datos iniciales — OdontoClinick")
print("=" * 60)


# =============================================================================
# 1. ESPECIALIDADES ODONTOLÓGICAS
# =============================================================================
print("\n[1/5] Cargando especialidades...")

especialidades = [
    ("Odontología General",         "Atención primaria dental, diagnóstico y tratamientos básicos."),
    ("Ortodoncia",                   "Corrección de la posición de dientes y mandíbula."),
    ("Endodoncia",                   "Tratamiento del interior del diente (conductos radiculares)."),
    ("Periodoncia",                  "Tratamiento de encías y tejidos de soporte dental."),
    ("Odontopediatría",              "Atención dental especializada en niños y adolescentes."),
    ("Cirugía Oral y Maxilofacial", "Extracciones complejas, implantes y cirugías de mandíbula."),
    ("Prostodoncia",                 "Rehabilitación con prótesis, coronas, puentes e implantes."),
    ("Radiología Oral",              "Diagnóstico por imagen dental (radiografías, tomografías)."),
    ("Estética Dental",              "Blanqueamiento, carillas y mejora del aspecto visual."),
    ("Odontología Forense",          "Identificación dental en contextos legales o periciales."),
]

for nombre, descripcion in especialidades:
    obj, created = Especialidad.objects.get_or_create(
        nombre_especialidad=nombre,
        defaults={'descripcion': descripcion}
    )
    print(f"  {'✅ Creada' if created else '⏭️  Ya existe'}: {nombre}")

print(f"  Total especialidades: {Especialidad.objects.count()}")


# =============================================================================
# 2. CATEGORÍAS DE PRODUCTO
# =============================================================================
print("\n[2/5] Cargando categorías de producto...")

categorias = [
    ("Anestésicos",          "Anestesia local y tópica para procedimientos dentales."),
    ("Materiales de Obturación", "Resinas, amalgamas y cementos para rellenos."),
    ("Instrumental Desechable",  "Guantes, mascarillas, baberos y materiales de un solo uso."),
    ("Instrumental Reutilizable","Espejos, sondas, fórceps y herramientas esterilizables."),
    ("Ortodoncia",           "Brackets, arcos, bandas y accesorios de ortodoncia."),
    ("Implantología",        "Implantes, pilares y componentes protésicos."),
    ("Higiene y Profilaxis", "Pastas profilácticas, cepillos, hilo dental y sellantes."),
    ("Radiología",           "Películas, sensores y accesorios radiográficos."),
    ("Endodoncia",           "Limas, irrigantes y materiales para tratamiento de conductos."),
    ("Blanqueamiento",       "Geles y kits para blanqueamiento dental."),
    ("Medicamentos",         "Antibióticos, analgésicos y antiinflamatorios de uso odontológico."),
    ("Equipos y Repuestos",  "Piezas de mano, turbinas, eyectores y repuestos varios."),
]

cat_objs = {}
for nombre, descripcion in categorias:
    obj, created = CategoriaProducto.objects.get_or_create(
        nombre_categoria=nombre,
        defaults={'descripcion': descripcion}
    )
    cat_objs[nombre] = obj
    print(f"  {'✅ Creada' if created else '⏭️  Ya existe'}: {nombre}")

print(f"  Total categorías: {CategoriaProducto.objects.count()}")


# =============================================================================
# 3. EMPRESAS / PROVEEDORES
# =============================================================================
print("\n[3/5] Cargando empresas proveedoras...")

empresas = [
    ("Dentsply Sirona Colombia",  "900123456-1", True,  False),
    ("3M Oral Care Colombia",     "900234567-2", True,  False),
    ("Kerr Dental Colombia",      "900345678-3", True,  False),
    ("Ultradent Products",        "900456789-4", True,  False),
    ("GC América Colombia",       "900567890-5", True,  False),
    ("Ivoclar Vivadent",          "900678901-6", True,  False),
    ("Nobel Biocare Colombia",    "900789012-7", True,  False),
    ("Straumann Colombia",        "900890123-8", True,  False),
    ("Medifarma Dental",          "901234567-1", True,  False),
    ("DistribuDent SAS",          "901345678-2", True,  False),
    ("Clínica OdontoClinick",     "900000001-0", False, True),
]

emp_objs = {}
for nombre, nit, es_prov, es_comp in empresas:
    obj, created = Empresa.objects.get_or_create(
        nit=nit,
        defaults={
            'nombre_empresa': nombre,
            'es_proveedor':   es_prov,
            'es_comprador':   es_comp,
        }
    )
    emp_objs[nombre] = obj
    print(f"  {'✅ Creada' if created else '⏭️  Ya existe'}: {nombre}")

print(f"  Total empresas: {Empresa.objects.count()}")


# =============================================================================
# 4. PRODUCTOS DE INVENTARIO
# =============================================================================
print("\n[4/5] Cargando productos...")

productos = [
    # (codigo, nombre, descripcion, categoria, precio_venta, stock_actual, stock_minimo, unidad)
    # --- Anestésicos ---
    ("ANES-001", "Lidocaína 2% con Epinefrina",  "Cartucho 1.8ml, caja x50",         "Anestésicos",           85000,  20, 5,  "CJ"),
    ("ANES-002", "Mepivacaína 3% sin vasoconstrictor", "Cartucho 1.8ml, caja x50",   "Anestésicos",           90000,  10, 5,  "CJ"),
    ("ANES-003", "Gel anestésico tópico benzocaína", "Sabor fresa, tarro 30g",        "Anestésicos",           35000,  15, 3,  "UN"),

    # --- Materiales de Obturación ---
    ("OBT-001",  "Resina compuesta A2 (jeringa 4g)", "Fotopolimerizable, alta estética","Materiales de Obturación", 95000, 10, 3, "UN"),
    ("OBT-002",  "Resina compuesta A3 (jeringa 4g)", "Fotopolimerizable",              "Materiales de Obturación", 95000,  8, 3,  "UN"),
    ("OBT-003",  "Cemento de ionómero de vidrio",    "Polvo/líquido, 15g/10ml",        "Materiales de Obturación", 75000, 12, 3,  "UN"),
    ("OBT-004",  "Amalgama encapsulada",             "Cápsula de 600mg, caja x50",     "Materiales de Obturación", 120000, 5, 2,  "CJ"),
    ("OBT-005",  "Hidróxido de calcio pasta",        "Base/catalizador 12g c/u",       "Materiales de Obturación", 55000,  8, 3,  "UN"),

    # --- Instrumental Desechable ---
    ("DES-001",  "Guantes de nitrilo talla M",      "Caja x100 unidades sin polvo",   "Instrumental Desechable", 28000, 30, 10, "CJ"),
    ("DES-002",  "Guantes de nitrilo talla S",      "Caja x100 unidades sin polvo",   "Instrumental Desechable", 28000, 20, 10, "CJ"),
    ("DES-003",  "Guantes de nitrilo talla L",      "Caja x100 unidades sin polvo",   "Instrumental Desechable", 28000, 20, 10, "CJ"),
    ("DES-004",  "Mascarillas desechables 3 capas", "Caja x50 unidades",              "Instrumental Desechable", 18000, 40, 10, "CJ"),
    ("DES-005",  "Baberos desechables",              "Paquete x100 unidades",          "Instrumental Desechable", 22000, 25,  8, "CJ"),
    ("DES-006",  "Eyectores de saliva",              "Bolsa x100 unidades",            "Instrumental Desechable", 12000, 30,  8, "CJ"),
    ("DES-007",  "Rollos de algodón #2",             "Bolsa x1000 unidades",           "Instrumental Desechable", 15000, 20,  5, "CJ"),

    # --- Instrumental Reutilizable ---
    ("RUT-001",  "Espejo bucal plano #5",            "Mango metálico antideslizante",  "Instrumental Reutilizable", 18000, 15,  5, "UN"),
    ("RUT-002",  "Sonda periodontal OMS",            "Marcas en 3.5-8.5-11.5mm",       "Instrumental Reutilizable", 45000,  8,  3, "UN"),
    ("RUT-003",  "Explorador #5",                    "Punta fina para caries",         "Instrumental Reutilizable", 22000, 10,  3, "UN"),
    ("RUT-004",  "Pinza para algodón",               "Acero inoxidable",               "Instrumental Reutilizable", 28000, 10,  3, "UN"),
    ("RUT-005",  "Fórceps #150 superiores",          "Extracción premolares/molares",  "Instrumental Reutilizable", 85000,  5,  2, "UN"),
    ("RUT-006",  "Fórceps #151 inferiores",          "Extracción universal inferior",  "Instrumental Reutilizable", 85000,  5,  2, "UN"),

    # --- Ortodoncia ---
    ("ORT-001",  "Brackets metálicos slot 0.022",   "Kit x20 dientes",                "Ortodoncia",            180000,  8,  2, "UN"),
    ("ORT-002",  "Arco niti redondo 0.014",          "Paquete x10 arcos",              "Ortodoncia",             45000, 12,  3, "UN"),
    ("ORT-003",  "Ligaduras elásticas colores",      "Bolsa x1000 unidades",           "Ortodoncia",             18000, 15,  5, "CJ"),
    ("ORT-004",  "Cera para ortodoncia",             "Caja x10 tiras",                 "Ortodoncia",             12000, 20,  5, "CJ"),
    ("ORT-005",  "Adhesivo para brackets",           "Kit base/catalizador 7ml",       "Ortodoncia",             65000,  6,  2, "UN"),

    # --- Higiene y Profilaxis ---
    ("HIG-001",  "Pasta profiláctica sabor menta",  "Tarro 200g grano fino",          "Higiene y Profilaxis",   28000, 15,  5, "UN"),
    ("HIG-002",  "Copa de goma para profilaxis",     "Bolsa x144 unidades latillas",   "Higiene y Profilaxis",   22000, 10,  3, "CJ"),
    ("HIG-003",  "Sellante de fosas y fisuras",      "Jeringa 1ml fotopolimerizable",  "Higiene y Profilaxis",   55000, 10,  3, "UN"),
    ("HIG-004",  "Hilo dental profesional 200m",     "Rollo cera menta",               "Higiene y Profilaxis",   18000, 20,  5, "UN"),
    ("HIG-005",  "Flúor gel 1.23% acidulado",       "Frasco 480g sabor uva",          "Higiene y Profilaxis",   45000,  8,  3, "UN"),

    # --- Endodoncia ---
    ("END-001",  "Limas K-file #15 25mm",           "Caja x6 unidades acero inox",    "Endodoncia",             38000, 10,  3, "CJ"),
    ("END-002",  "Limas K-file #20 25mm",           "Caja x6 unidades acero inox",    "Endodoncia",             38000, 10,  3, "CJ"),
    ("END-003",  "Limas rotatorias ProTaper Gold",  "Kit 6 limas Ni-Ti",              "Endodoncia",            280000,  5,  2, "UN"),
    ("END-004",  "Hipoclorito de sodio 5.25%",      "Frasco 1000ml irrigante",        "Endodoncia",             18000, 12,  4, "UN"),
    ("END-005",  "EDTA gel 24%",                    "Jeringa 5ml lubricante",         "Endodoncia",             35000,  8,  3, "UN"),
    ("END-006",  "Gutapercha conos #25",             "Caja x120 conos",                "Endodoncia",             22000, 10,  3, "CJ"),
    ("END-007",  "Cemento sellador AH Plus",         "Cartucho doble jeringa 4g",      "Endodoncia",             95000,  4,  2, "UN"),

    # --- Blanqueamiento ---
    ("BLA-001",  "Gel blanqueador peróxido H 35%",  "Jeringa 3ml uso clínico",        "Blanqueamiento",         85000,  8,  2, "UN"),
    ("BLA-002",  "Gel blanqueador peróxido H 16%",  "Kit cubetas x4 jeringas",        "Blanqueamiento",         65000,  6,  2, "UN"),
    ("BLA-003",  "Protector gingival fotocurable",  "Jeringa 2ml",                    "Blanqueamiento",         45000,  8,  2, "UN"),

    # --- Medicamentos ---
    ("MED-001",  "Amoxicilina 500mg",               "Caja x30 cápsulas",              "Medicamentos",           22000, 20,  5, "CJ"),
    ("MED-002",  "Ibuprofeno 400mg",                "Caja x30 tabletas",              "Medicamentos",           15000, 25,  5, "CJ"),
    ("MED-003",  "Clindamicina 300mg",              "Caja x16 cápsulas",              "Medicamentos",           38000, 12,  4, "CJ"),
    ("MED-004",  "Metronidazol 500mg",              "Caja x30 tabletas",              "Medicamentos",           18000, 15,  4, "CJ"),
    ("MED-005",  "Dexametasona 4mg/2ml inyectable", "Caja x3 ampollas",               "Medicamentos",           28000, 10,  3, "CJ"),
]

for codigo, nombre, desc, cat_nombre, precio, stock, stock_min, unidad in productos:
    categoria = cat_objs.get(cat_nombre)
    if not categoria:
        print(f"  ⚠️  Categoría no encontrada para: {nombre}")
        continue
    obj, created = Producto.objects.get_or_create(
        codigo_producto=codigo,
        defaults={
            'nombre_producto': nombre,
            'descripcion':     desc,
            'id_categoria':    categoria,
            'precio_venta':    precio,
            'stock_actual':    stock,
            'stock_minimo':    stock_min,
            'unidad_medida':   unidad,
            'activo':          1,
        }
    )
    print(f"  {'✅ Creado' if created else '⏭️  Ya existe'}: {nombre}")

print(f"  Total productos: {Producto.objects.count()}")


# =============================================================================
# 5. TRATAMIENTOS / PROCEDIMIENTOS
# =============================================================================
print("\n[5/5] Cargando tratamientos y procedimientos...")

tratamientos = [
    # (codigo, nombre, descripcion, costo_base, duracion_min)
    # --- Preventivos ---
    ("PREV-001", "Consulta de valoración inicial",   "Examen clínico completo, diagnóstico y plan de tratamiento.",           50000,   30),
    ("PREV-002", "Profilaxis dental (limpieza)",      "Remoción de placa y cálculo supragingival con ultrasonido.",            80000,   45),
    ("PREV-003", "Aplicación de flúor tópico",        "Gel o barniz de flúor para remineralización.",                          40000,   20),
    ("PREV-004", "Sellantes de fosas y fisuras",      "Sellante fotopolimerizable por diente.",                                 45000,   30),
    ("PREV-005", "Radiografía periapical",            "Radiografía digital de uno o dos dientes.",                             25000,   15),
    ("PREV-006", "Radiografía panorámica",            "Imagen panorámica completa de ambas arcadas.",                           85000,   20),

    # --- Restauraciones ---
    ("REST-001", "Restauración en resina clase I",    "Obturación oclusal en diente posterior.",                                90000,   45),
    ("REST-002", "Restauración en resina clase II",   "Obturación interproximal en diente posterior.",                         120000,   60),
    ("REST-003", "Restauración en resina clase III",  "Obturación en diente anterior cara proximal.",                          100000,   45),
    ("REST-004", "Restauración en resina clase IV",   "Obturación en ángulo incisal de diente anterior.",                      130000,   60),
    ("REST-005", "Restauración en resina clase V",    "Obturación cervical o en cara vestibular.",                              90000,   40),
    ("REST-006", "Restauración en amalgama",          "Obturación con amalgama en diente posterior.",                           80000,   45),

    # --- Endodoncia ---
    ("ENDO-001", "Endodoncia diente unirradicular",   "Tratamiento de conducto en incisivos o caninos.",                       450000,  120),
    ("ENDO-002", "Endodoncia diente birradicular",    "Tratamiento de conducto en premolares.",                                550000,  150),
    ("ENDO-003", "Endodoncia diente multirradicular", "Tratamiento de conducto en molares.",                                   700000,  180),
    ("ENDO-004", "Retratamiento endodóntico",         "Retratamiento de conducto previamente tratado.",                        600000,  150),

    # --- Periodoncia ---
    ("PERIO-001","Raspaje y alisado radicular",       "Cuadrante por sesión, con ultrasonido y curetas.",                      150000,   60),
    ("PERIO-002","Cirugía periodontal colgajo",       "Procedimiento quirúrgico por cuadrante.",                               800000,  120),
    ("PERIO-003","Aplicación de antibiótico local",   "Colocación de fibras de tetraciclina o chip de clorhexidina.",          120000,   30),

    # --- Cirugía Oral ---
    ("CIR-001",  "Extracción simple",                 "Extracción de diente erupcionado sin complicaciones.",                  120000,   30),
    ("CIR-002",  "Extracción quirúrgica",             "Extracción de diente retenido o con complicaciones.",                   250000,   60),
    ("CIR-003",  "Extracción de cordal (muela juicio)","Extracción de tercer molar, dificultad moderada.",                    350000,   90),
    ("CIR-004",  "Frenectomía",                       "Eliminación quirúrgica del frenillo labial o lingual.",                 280000,   45),
    ("CIR-005",  "Biopsia de tejidos blandos",        "Toma de muestra para análisis histopatológico.",                        220000,   30),

    # --- Ortodoncia ---
    ("ORT-001",  "Estudio ortodóntico completo",      "Registros, modelos, fotos, radiografías y diagnóstico.",               350000,   60),
    ("ORT-002",  "Ortodoncia fija metálica (arco completo)","Tratamiento completo con brackets metálicos (mensualidad).",      180000,   60),
    ("ORT-003",  "Ortodoncia fija estética (zafiro)", "Tratamiento con brackets de zafiro (mensualidad).",                    250000,   60),
    ("ORT-004",  "Retenedor removible",               "Placa de retención termoformada o acrílica.",                           180000,   30),
    ("ORT-005",  "Control de ortodoncia mensual",     "Ajuste de arco y cambio de ligaduras.",                                 80000,   30),

    # --- Prótesis ---
    ("PROT-001", "Corona metal-porcelana",            "Corona unitaria sobre muñón o implante.",                               900000,   60),
    ("PROT-002", "Corona en zirconia",                "Corona totalmente cerámica de alta resistencia.",                      1400000,   60),
    ("PROT-003", "Puente fijo de 3 unidades",         "Prótesis fija de tres piezas sobre dientes pilares.",                 2200000,   90),
    ("PROT-004", "Prótesis parcial removible",        "Placa parcial metálica o acrílica.",                                   850000,   60),
    ("PROT-005", "Prótesis total (dentadura completa)","Prótesis completa superior o inferior.",                              1100000,   60),
    ("PROT-006", "Carilla de porcelana",              "Lámina cerámica adhesiva por diente.",                                 950000,   90),

    # --- Implantología ---
    ("IMP-001",  "Implante dental (solo fixture)",    "Colocación quirúrgica del implante de titanio.",                       2500000,  120),
    ("IMP-002",  "Corona sobre implante",             "Restauración protésica sobre implante oseointegrado.",                 1500000,   60),
    ("IMP-003",  "Injerto óseo",                      "Regeneración ósea guiada con biomaterial.",                           1800000,  120),

    # --- Estética ---
    ("EST-001",  "Blanqueamiento dental en consultorio","Sesión con peróxido activado por luz.",                               350000,   90),
    ("EST-002",  "Blanqueamiento dental en casa",      "Kit con cubetas y gel para uso domiciliario.",                         220000,   30),
    ("EST-003",  "Contorneado dental (odontoplastia)", "Remodelado estético del esmalte.",                                    150000,   45),

    # --- Odontopediatría ---
    ("PED-001",  "Consulta odontopediátrica",          "Valoración y diagnóstico en paciente pediátrico.",                     60000,   30),
    ("PED-002",  "Pulpotomía en diente deciduo",       "Tratamiento pulpar parcial en molar de leche.",                       180000,   60),
    ("PED-003",  "Corona de acero inoxidable",         "Corona pediátrica prefabricada en diente deciduo.",                   150000,   45),
    ("PED-004",  "Mantenedor de espacio fijo",         "Aparato para preservar espacio de diente perdido.",                   280000,   30),
]

for codigo, nombre, desc, costo, duracion in tratamientos:
    obj, created = Tratamiento.objects.get_or_create(
        codigo=codigo,
        defaults={
            'nombre_tratamiento':         nombre,
            'descripcion':                desc,
            'costo_base':                 costo,
            'duracion_estimada_minutos':  duracion,
            'activo':                     1,
        }
    )
    print(f"  {'✅ Creado' if created else '⏭️  Ya existe'}: {nombre}")

print(f"  Total tratamientos: {Tratamiento.objects.count()}")


# =============================================================================
# RESUMEN FINAL
# =============================================================================
print("\n" + "=" * 60)
print("  ✅ Carga de datos completada")
print(f"  Especialidades : {Especialidad.objects.count()}")
print(f"  Categorías     : {CategoriaProducto.objects.count()}")
print(f"  Productos      : {Producto.objects.count()}")
print(f"  Empresas       : {Empresa.objects.count()}")
print(f"  Tratamientos   : {Tratamiento.objects.count()}")
print("=" * 60)
