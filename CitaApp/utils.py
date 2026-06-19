import qrcode
from io import BytesIO

from django.core.files import File
from django.conf import settings

def generar_qr_cita(cita):

    url = f"http://127.0.0.1:8000/citas/checkin/{cita.id_cita}/"

    qr = qrcode.make(url)

    buffer = BytesIO()

    qr.save(buffer, format="PNG")

    nombre_archivo = f"cita_{cita.id_cita}.png"

    cita.qr_code.save(
        nombre_archivo,
        File(buffer),
        save=True
    )