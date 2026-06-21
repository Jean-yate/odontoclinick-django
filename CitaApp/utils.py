import qrcode
import requests
from io import BytesIO
from django.core.files import File
from django.conf import settings

def generar_qr_cita(cita):
    """
    Genera un código QR único para el check-in de la cita
    y lo almacena en el modelo.
    """
    # FIX: antes tenía 'http://127.0.0.1:8000' hardcodeado — cualquier QR
    # generado en producción apuntaba a localhost, inútil al escanearlo
    # desde un celular real. Ahora usa settings.SITE_URL (configurable por
    # variable de entorno: distinto en local vs Railway).
    url = f"{settings.SITE_URL}/citas/checkin/{cita.id_cita}/"
    qr = qrcode.make(url)

    buffer = BytesIO()
    qr.save(buffer, format="PNG")

    # FIX REAL del error "Empty file": después de escribir en el buffer con
    # qr.save(), el cursor queda posicionado al FINAL del stream. Si no se
    # rebobina con seek(0) antes de pasarlo a File(), cualquier storage que
    # lea desde la posición actual (como cloudinary_storage) encuentra el
    # cursor ya al final y lee 0 bytes — de ahí "Empty file". Con
    # FileSystemStorage local esto no fallaba porque Django maneja ese caso
    # de otra forma internamente, pero con Cloudinary sí es necesario.
    buffer.seek(0)

    nombre_archivo = f"cita_{cita.id_cita}.png"

    cita.qr_code.save(
        nombre_archivo,
        File(buffer),
        save=True
    )

def enviar_sms_twilio(cita):
    """
    Envía un SMS usando la API de Twilio directamente mediante HTTP Requests,
    sin necesidad de instalar paquetes externos adicionales (como twilio o django-twilio).
    """
    url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json"
    
    # Construcción del cuerpo del mensaje
    mensaje = (
        f"Hola {cita.id_paciente.id_usuario.nombre}, te recordamos tu cita en "
        f"OdontoClinick el {cita.fecha_hora.strftime('%d/%m/%Y a las %H:%M')}."
    )
    
    payload = {
        'From': settings.TWILIO_NUMBER,
        'To': str(cita.id_paciente.id_usuario.telefono),  # Asegúrate que incluya el prefijo (ej: +57)
        'Body': mensaje
    }
    
    # Autenticación Básica con las credenciales de tu settings.py
    auth = (settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    
    try:
        response = requests.post(url, data=payload, auth=auth)
        # Twilio responde con 201 Created si el mensaje se encoló correctamente
        return response.status_code == 201
    except requests.exceptions.RequestException:
        return False