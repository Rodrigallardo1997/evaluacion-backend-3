"""
Vistas web para gestión de usuarios y roles por parte del Administrador.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from apps.usuarios.forms import UsuarioCrearForm, UsuarioEditarForm
from apps.usuarios.models import Usuario
from apps.usuarios.permissions import role_required


@login_required
@role_required("ADMIN")
def usuarios_lista(request):
    """Listado y gestión rápida de roles de usuarios (exclusivo Administrador)."""
    q = request.GET.get("q", "").strip()
    rol_filtro = request.GET.get("rol", "").strip()

    queryset = Usuario.objects.all().order_by("-creado_en")

    if q:
        queryset = queryset.filter(
            Q(username__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(email__icontains=q)
        )
    if rol_filtro and rol_filtro in Usuario.Rol.values:
        queryset = queryset.filter(rol=rol_filtro)

    paginator = Paginator(queryset, 15)
    page_number = request.GET.get("page")
    usuarios = paginator.get_page(page_number)

    # Conteo de usuarios por rol para las tarjetas resumen
    conteos = {
        "total": Usuario.objects.count(),
        "admin": Usuario.objects.filter(rol=Usuario.Rol.ADMIN).count(),
        "vendedor": Usuario.objects.filter(rol=Usuario.Rol.VENDEDOR).count(),
        "cocina": Usuario.objects.filter(rol=Usuario.Rol.COCINA).count(),
        "repartidor": Usuario.objects.filter(rol=Usuario.Rol.REPARTIDOR).count(),
        "cliente": Usuario.objects.filter(rol=Usuario.Rol.CLIENTE).count(),
    }

    return render(
        request,
        "usuarios/lista.html",
        {
            "usuarios": usuarios,
            "q": q,
            "rol_filtro": rol_filtro,
            "roles": Usuario.Rol.choices,
            "conteos": conteos,
        },
    )


@login_required
@role_required("ADMIN")
def usuario_crear(request):
    """Crea un nuevo usuario asignándole poderes/rol de forma inmediata."""
    if request.method == "POST":
        form = UsuarioCrearForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            messages.success(
                request,
                f"Usuario '{usuario.username}' registrado exitosamente con rol de {usuario.get_rol_display()}.",
            )
            return redirect("usuarios:lista")
    else:
        form = UsuarioCrearForm()

    return render(
        request,
        "usuarios/form.html",
        {"form": form, "titulo": "Registrar Nuevo Usuario con Rol", "accion": "Crear Usuario"},
    )


@login_required
@role_required("ADMIN")
def usuario_editar(request, pk):
    """Edita un usuario existente y permite reasignar sus poderes/rol."""
    usuario = get_object_or_404(Usuario, pk=pk)
    if request.method == "POST":
        form = UsuarioEditarForm(request.POST, instance=usuario)
        if form.is_valid():
            usuario = form.save()
            messages.success(
                request,
                f"Usuario '{usuario.username}' actualizado. Rol asignado: {usuario.get_rol_display()}.",
            )
            return redirect("usuarios:lista")
    else:
        form = UsuarioEditarForm(instance=usuario)

    return render(
        request,
        "usuarios/form.html",
        {
            "form": form,
            "usuario_editado": usuario,
            "titulo": f"Editar Usuario: {usuario.username}",
            "accion": "Guardar Cambios",
        },
    )


@login_required
@role_required("ADMIN")
def usuario_cambiar_rol(request, pk):
    """Acción rápida vía POST para cambiar el rol de un usuario con un clic."""
    if request.method == "POST":
        usuario = get_object_or_404(Usuario, pk=pk)
        nuevo_rol = request.POST.get("nuevo_rol", "").strip()

        if nuevo_rol in Usuario.Rol.values:
            # Si el admin intenta quitarse el rol a sí mismo
            if usuario == request.user and nuevo_rol != Usuario.Rol.ADMIN:
                messages.error(request, "No puedes quitarte el rol de Administrador a ti mismo.")
            else:
                rol_anterior = usuario.get_rol_display()
                usuario.rol = nuevo_rol
                if nuevo_rol == Usuario.Rol.ADMIN:
                    usuario.is_staff = True
                usuario.save()
                messages.success(
                    request,
                    f"Poderes actualizados: '{usuario.username}' cambió de {rol_anterior} a {usuario.get_rol_display()}.",
                )
        else:
            messages.error(request, "El rol especificado no es válido.")

    return redirect("usuarios:lista")
