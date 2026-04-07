# 🦷 OdontoClinick — Sistema de Gestión Odontológica

**OdontoClinick** es una solución integral de software clínico desarrollada con **Django**. Está diseñada para transformar la administración manual en un ecosistema digital eficiente, facilitando el control de citas, la gestión de pacientes y la optimización de inventarios médicos.

---

## ✨ Características Principales

### 👨‍⚕️ Panel del Especialista (Dashboard)
* **Gestión de Agenda:** Visualización dinámica de pacientes diarios con estados de cita en tiempo real.
* **Centro de Gestión Clínica:** Acceso rápido a historiales, horarios y configuración de servicios (Tratamientos).
* **Interfaz Moderna:** Diseño basado en *Neumorfismo* y *Glassmorfismo* para una experiencia de usuario fluida y profesional.

### 📋 Gestión de Tratamientos e Insumos
* **Catálogo de Servicios:** Registro detallado de procedimientos, códigos clínicos y costos base.
* **Control de Insumos:** Vinculación directa de materiales a tratamientos específicos para un control preciso del stock.
* **Estados Activos/Inactivos:** Capacidad de pausar servicios sin perder el historial de datos.

### 👥 Administración de Pacientes
* **Historias Clínicas:** Registro centralizado de evolución del paciente, documentos y datos de contacto.
* **Seguridad de Datos:** Sistema de autenticación robusto basado en roles (Médico, Admin, Recepción).

---

## 🛠️ Stack Tecnológico

| Componente | Tecnología |
| :--- | :--- |
| **Backend** | Python 3.10+ / Django 5.x |
| **Frontend** | HTML5, CSS3 (Custom Claymorphism), Bootstrap 5 |
| **Iconografía** | Bootstrap Icons |
| **Base de Datos** | PostgreSQL / SQL Server |

---

## 🚀 Instalación y Configuración Rápida

1. **Clonar el Repositorio**
   ```bash
   git clone [https://github.com/tu-usuario/odontoclinick-django.git](https://github.com/tu-usuario/odontoclinick-django.git)
   cd odontoclinick-django
   
2. **Configurar el Entorno Virtual**
python -m venv venv
# Activar en Windows:
.\venv\Scripts\activate

3. **Instalar Dependencias**
   pip install -r requirements.txt

4. **Migraciones y Servidor**
   python manage.py migrate
   python manage.py runserver


Nota del Desarrollador: Este proyecto ha sido creado por Grupo Scrum 3 como parte del programa de Análisis y Desarrollo de Software (ADSO), enfocándose en la escalabilidad y la experiencia de usuario en entornos clínicos.
