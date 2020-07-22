from django.forms import ModelForm

from .models import OIDCTeamAssignmentRule


class OIDCAssignmentRuleForm(ModelForm):
    def __init__(self, organizer, *args, **kwargs):
        super(OIDCAssignmentRuleForm, self).__init__(*args, **kwargs)
        self.fields['team'].queryset = self.fields['team'].queryset.filter(organizer=organizer)

    class Meta:
        model = OIDCTeamAssignmentRule
        fields = ['team', 'attribute', 'value']
