from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls.base import reverse

from shapeworks_cloud.core.forms import ParticlesForm
from shapeworks_cloud.core.models import Dataset, Particles, ShapeModel


def particles_detail(request, dataset_pk, shape_model_pk, particles_pk):
    dataset = get_object_or_404(Dataset, pk=dataset_pk)
    shape_model = get_object_or_404(ShapeModel, pk=shape_model_pk)
    particles = get_object_or_404(
        Particles,
        shape_model__dataset__pk=dataset_pk,
        shape_model__pk=shape_model_pk,
        pk=particles_pk,
    )
    context = {
        'dataset': dataset,
        'shape_model': shape_model,
        'particles': particles,
    }
    return render(request, 'particles_detail.html', context)


@login_required
def particles_create(request, dataset_pk, shape_model_pk):
    dataset = get_object_or_404(Dataset, pk=dataset_pk)
    shape_model = get_object_or_404(ShapeModel, dataset__pk=dataset_pk, pk=shape_model_pk)
    if request.method == 'POST':
        # Create a new Particles
        form = ParticlesForm(request.POST)
        if form.is_valid():
            particles = form.instance
            particles.shape_model = shape_model
            particles.save()
            return HttpResponseRedirect(
                reverse('shape_model_detail', args=(dataset_pk, shape_model_pk))
            )
    else:
        form = ParticlesForm()
    context = {
        'form': form,
        'dataset': dataset,
        'shape_model': shape_model,
    }
    return render(request, 'particles_create.html', context)


@login_required
def particles_edit(request, dataset_pk, shape_model_pk, particles_pk):
    dataset = get_object_or_404(Dataset, pk=dataset_pk)
    shape_model = get_object_or_404(ShapeModel, dataset__pk=dataset_pk, pk=shape_model_pk)
    particles = get_object_or_404(
        Particles,
        shape_model__dataset__pk=dataset_pk,
        shape_model__pk=shape_model_pk,
        pk=particles_pk,
    )
    if request.method == 'POST':
        # Edit an existing Particles
        form = ParticlesForm(request.POST, initial={'blob': particles.blob})
        if not form.fields['blob']:
            form.fields.blob = particles.blob
        if form.is_valid():
            particles.dataset = dataset
            particles.name = form.instance.name
            particles.blob = form.instance.blob
            particles.save()
            return HttpResponseRedirect(
                reverse('particles_detail', args=(dataset_pk, shape_model_pk, particles_pk))
            )
    else:
        form = ParticlesForm(instance=particles)
    context = {
        'form': form,
        'dataset': dataset,
        'shape_model': shape_model,
        'particles': particles,
    }
    return render(request, 'particles_edit.html', context)
