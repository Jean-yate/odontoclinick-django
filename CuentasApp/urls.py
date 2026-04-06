from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from CitaApp import views as cita_views
from Webapp import views as web_views
from .models import Usuario

# Imports necesarios para el envío manual
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.contrib.sites.shortcuts import get_current_site

# --- FORMULARIO BLINDADO ---
class CustomPasswordResetForm(PasswordResetForm):
    def get_users(self, email):
        # Buscamos en tu campo 'correo'
        return Usuario.objects.filter(correo__iexact=email, id_estado__nombre_estado='Activo')

    def save(self, **kwargs):
        """
        Control total del envío para evitar el error de '.email' 
        y los conflictos de argumentos en Django 6.x.
        """
        email_ingresado = self.cleaned_data["email"]
        request = kwargs.get('request')
        
        # Datos del sitio para el link
        current_site = get_current_site(request)
        domain = current_site.domain
        site_name = current_site.name
        use_https = request.is_secure()
        
        for user in self.get_users(email_ingresado):
            # 1. Generamos el contexto para el correo
            context = {
                'email': user.correo,
                'domain': domain,
                'site_name': site_name,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'user': user,
                'token': default_token_generator.make_token(user),
                'protocol': 'https' if use_https else 'http',
            }
            
            # 2. Renderizamos el cuerpo del correo
            # Nota: Asegúrate de tener este archivo en templates/registration/
            body = render_to_string('registration/password_reset_email.html', context)
            
            # 3. Enviamos usando el campo 'correo' de tu modelo
            send_mail(
                subject=f"Restablecer contraseña - {site_name}",
                message=body,
                from_email=None, # Usa el DEFAULT_FROM_EMAIL de settings.py
                recipient_list=[user.correo],
                fail_silently=False,
            )

# --- TUS URLS (Sin cambios en la estructura) ---
urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('registro-base/', views.registro_view, name='registro_base'),
    path('registro-paciente/', web_views.registro_integral_paciente, name='registro'),
    path('agenda-citas/', cita_views.lista_citas, name='lista_citas'),

    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='CuentasApp/password_reset.html',
        form_class=CustomPasswordResetForm
    ), name='password_reset'),
    
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='CuentasApp/password_reset_done.html'
    ), name='password_reset_done'),
    
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='CuentasApp/password_reset_confirm.html'
    ), name='password_reset_confirm'),
    
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='CuentasApp/password_reset_complete.html'
    ), name='password_reset_complete'),

    path('perfil-secretaria/', views.perfil_secretaria, name='perfil_secretaria'),
]