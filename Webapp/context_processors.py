def roles_usuario(request):
    if request.user.is_authenticated:
        return {
            'es_medico': request.user.groups.filter(name='Medico').exists(),
            'es_auxiliar': request.user.groups.filter(name='Auxiliar').exists(),
        }
    return {}