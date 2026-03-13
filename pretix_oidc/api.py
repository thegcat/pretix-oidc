from rest_framework import serializers, viewsets
from rest_framework.exceptions import ValidationError

from pretix.base.models import Team

from .models import OIDCTeamAssignmentRule


class OIDCTeamAssignmentRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = OIDCTeamAssignmentRule
        fields = ("id", "team", "attribute", "value")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Restrict team choices to teams belonging to the current organizer
        if "organizer" in self.context:
            self.fields["team"].queryset = Team.objects.filter(
                organizer=self.context["organizer"]
            )

    def validate_team(self, value):
        organizer = self.context.get("organizer")
        if organizer and value.organizer_id != organizer.pk:
            raise ValidationError(
                "The selected team does not belong to this organizer."
            )
        return value


class OIDCTeamAssignmentRuleViewSet(viewsets.ModelViewSet):
    serializer_class = OIDCTeamAssignmentRuleSerializer
    queryset = OIDCTeamAssignmentRule.objects.none()
    permission = "can_change_organizer_settings"
    write_permission = "can_change_organizer_settings"

    def get_queryset(self):
        return OIDCTeamAssignmentRule.objects.filter(
            team__organizer=self.request.organizer
        ).order_by("pk")

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["organizer"] = self.request.organizer
        return ctx

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()

