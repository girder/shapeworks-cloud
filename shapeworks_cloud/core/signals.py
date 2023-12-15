from django.db.models.signals import pre_delete
from django.dispatch import receiver

from .models import (
    CachedAnalysis,
    CachedAnalysisGroup,
    CachedAnalysisMeanShape,
    CachedAnalysisMode,
    CachedAnalysisModePCA,
    CachedDeepSSM,
    CachedExample,
    CachedModel,
    CachedModelExamples,
    CachedPrediction,
    CachedTensors,
    Project,
)


@receiver(pre_delete, sender=Project)
def delete_cached_analysis(sender, instance, using, **kwargs):
    CachedAnalysisModePCA.objects.filter(
        cachedanalysismode__cachedanalysis__project=instance
    ).delete()
    CachedAnalysisMode.objects.filter(cachedanalysis__project=instance).delete()
    CachedAnalysis.objects.filter(project=instance).delete()
    CachedAnalysisGroup.objects.filter(cachedanalysis__project=instance).delete()
    CachedAnalysisMeanShape.objects.filter(cachedanalysis__project=instance).delete()


@receiver(pre_delete, sender=Project)
def delete_cached_deepssm(sender, instance, using, **kwargs):
    CachedPrediction.objects.filter(project=instance).delete()
    CachedExample.objects.filter(project=instance).delete()
    CachedModelExamples.objects.filter(project=instance).delete()
    CachedModel.objects.filter(project=instance).delete()
    CachedTensors.objects.filter(project=instance).delete()
    CachedDeepSSM.objects.filter(project=instance).delete()
