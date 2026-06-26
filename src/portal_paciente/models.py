from django.db import models
from django.utils import timezone
from admision.models import Paciente

class AIChatUsage(models.Model):
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='ai_usage')
    # default (not auto_now_add) so get_or_create can match/insert a row keyed by date.
    fecha = models.DateField(default=timezone.localdate)
    count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('paciente', 'fecha')

    def __str__(self):
        return f"{self.paciente} - {self.fecha}: {self.count} queries"
