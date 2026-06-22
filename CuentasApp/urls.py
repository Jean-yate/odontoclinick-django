from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from CitaApp import views as cita_views
from Webapp import views as web_views
from .models import Usuario

from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.template.loader import render_to_string
from django.conf import settings
from Webapp.views import _enviar_correo_resend


class CustomPasswordResetForm(PasswordResetForm):
    def get_users(self, email):
        return Usuario.objects.filter(correo__iexact=email, id_estado__nombre_estado='Activo')

    def save(self, **kwargs):
        email_ingresado = self.cleaned_data["email"]
        request = kwargs.get('request')

        # Usamos SITE_URL de settings (variable de entorno) en lugar de
        # get_current_site() que lee la BD y devuelve example.com por defecto.
        # SITE_URL ya está configurado en Railway con el dominio real.
        site_url = settings.SITE_URL  # ej: https://tu-app.up.railway.app
        protocol = 'https' if site_url.startswith('https') else 'http'
        domain = site_url.replace('https://', '').replace('http://', '').rstrip('/')

        for user in self.get_users(email_ingresado):
            context = {
                'email': user.correo,
                'domain': domain,
                'site_name': 'OdontoClinick',
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'user': user,
                'token': default_token_generator.make_token(user),
                'protocol': protocol,
            }

            body = render_to_string('registration/password_reset_email.html', context)

            ok, err = _enviar_correo_resend(
                asunto="Restablecer contraseña - OdontoClinick",
                cuerpo=body,
                destinatario=user.correo,
            )
            if not ok:
                print(f"[ERROR PASSWORD RESET]: no se pudo enviar a {user.correo}: {err}")


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