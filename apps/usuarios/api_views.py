"""
Vistas API para autenticación y perfil de usuario.
"""
from django.contrib.auth import authenticate, login, logout
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.usuarios.serializers import UsuarioSerializer, LoginSerializer


class LoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]

        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response(
                {"detail": "Credenciales inválidas. Verifique usuario y contraseña."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            return Response(
                {"detail": "Esta cuenta se encuentra desactivada."},
                status=status.HTTP_403_FORBIDDEN,
            )

        login(request, user)
        token, _ = Token.objects.get_or_create(user=user)
        refresh = RefreshToken.for_user(user)
        refresh["username"] = user.username
        refresh["rol"] = user.rol

        return Response(
            {
                "detail": "Inicio de sesión exitoso.",
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "token": token.key,
                "usuario": UsuarioSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Eliminar token DRF si el cliente se autenticó vía Token (Frontend desacoplado)
        if hasattr(request.user, "auth_token"):
            request.user.auth_token.delete()
        logout(request)
        return Response({"detail": "Sesión cerrada exitosamente."}, status=status.HTTP_200_OK)


class MeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UsuarioSerializer(request.user).data)
