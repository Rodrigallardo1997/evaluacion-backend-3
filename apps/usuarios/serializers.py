"""
Serializers para el módulo de usuarios y autenticación.
"""
from rest_framework import serializers
from apps.usuarios.models import Usuario


class UsuarioSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "nombre_completo",
            "email",
            "rol",
            "telefono",
            "is_staff",
            "creado_en",
        ]
        read_only_fields = ["id", "creado_en", "is_staff"]

    def get_nombre_completo(self, obj) -> str:
        return obj.get_full_name() or obj.username


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)
