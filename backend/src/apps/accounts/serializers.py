from rest_framework import serializers

from apps.companies.serializers import LocationSerializer

from .models import User


class UserSerializer(serializers.ModelSerializer):
    locations = LocationSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "locations",
        ]
        read_only_fields = ["id", "username"]


class UserMeSerializer(serializers.ModelSerializer):
    """Serializer for current user profile."""

    locations = LocationSerializer(many=True, read_only=True)
    location_ids = serializers.PrimaryKeyRelatedField(
        source="locations",
        queryset=LocationSerializer.Meta.model.objects.all(),
        many=True,
        write_only=True,
        required=False,
    )

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "locations",
            "location_ids",
            "external_user_id",
        ]
        read_only_fields = ["id", "username", "email"]


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change."""

    current_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=8)

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect")
        return value
