import vtkImageMapper from 'vtk.js/Sources/Rendering/Core/ImageMapper';
import vtkImageSlice from 'vtk.js/Sources/Rendering/Core/ImageSlice';
import vtkImageCropFilter from 'vtk.js/Sources/Filters/General/ImageCropFilter';
import vtkCutter from 'vtk.js/Sources/Filters/Core/Cutter';
import vtkMapper from 'vtk.js/Sources/Rendering/Core/Mapper';
import vtkPlane from 'vtk.js/Sources/Common/DataModel/Plane';
import vtkActor from 'vtk.js/Sources/Rendering/Core/Actor';
import vtkProperty from 'vtk.js/Sources/Rendering/Core/Property';
import vtkCalculator from 'vtk.js/Sources/Filters/General/Calculator';
import vtkGlyph3DMapper from 'vtk.js/Sources/Rendering/Core/Glyph3DMapper';
import vtkSphereSource from 'vtk.js/Sources/Filters/Sources/SphereSource';
import { FieldDataTypes } from 'vtk.js/Sources/Common/DataModel/DataSet/Constants';
import { AttributeTypes } from 'vtk.js/Sources/Common/DataModel/DataSetAttributes/Constants';


import { ref, watch } from 'vue'
import {
    imageViewMode,
    imageViewIntersectMode,
    imageViewIntersectCropMode,
    imageViewAxis,
    imageViewSlices,
    imageViewSliceRanges,
    imageViewCroppedSliceRanges,
    imageViewWindow,
    imageViewWindowRange,
    imageViewLevel,
    imageViewLevelRange,
} from '@/store'

const slices = ref([])

export default {
    createSlice(renderer) {
        const sliceActor = vtkImageSlice.newInstance();
        const imageMapper = vtkImageMapper.newInstance();
        const cutPlane = vtkPlane.newInstance();
        const cutter = vtkCutter.newInstance();
        const cutMapper = vtkMapper.newInstance();
        const cutActor = vtkActor.newInstance();
        const cropFilter = vtkImageCropFilter.newInstance();
        const particleFilter = vtkCalculator.newInstance();
        const filteredParticleSphere = vtkSphereSource.newInstance();
        const filteredParticleActor = vtkActor.newInstance();
        const filteredParticleMapper = vtkGlyph3DMapper.newInstance();

        sliceActor.setMapper(imageMapper);
        renderer.addActor(sliceActor);

        cutter.setCutFunction(cutPlane);
        cutMapper.setInputConnection(cutter.getOutputPort());
        cutActor.setMapper(cutMapper);

        const cutProperty = cutActor.getProperty();
        cutProperty.setRepresentation(vtkProperty.Representation.WIREFRAME);
        cutProperty.setLighting(false);
        cutProperty.setColor(0, 1, 0);
        cutProperty.setLineWidth(5);
        cutActor.setVisibility(false);

        particleFilter.setFormula({
            getArrays: () => ({
                input: [{
                    location: FieldDataTypes.COORDINATE,
                }],
                output: [{
                    location: FieldDataTypes.POINT,
                    name: 'visible',
                    dataType: Float32Array,
                    attribute: AttributeTypes.SCALARS,
                    numberOfComponents: 1,
                }]
            }),
            evaluate: (arraysIn, arraysOut) => {
                const [coords] = arraysIn.map((d) => d.getData());
                const [visible] = arraysOut.map((d) => d.getData());

                const imageBounds = cropFilter.getInputData().getBounds()
                let currentAxis;
                let axisBounds;
                switch (imageMapper.getSlicingMode()) {
                    case 0:
                        currentAxis = 'x';
                        axisBounds = imageBounds.slice(0, 2);
                        break;
                    case 1:
                        currentAxis = 'y'
                        axisBounds = imageBounds.slice(2, 4)
                        break;
                    default:
                        currentAxis = 'z'
                        axisBounds = imageBounds.slice(4, 6)
                        break;
                }
                const sliceRange = imageViewSliceRanges.value[currentAxis]
                const currentSlice = imageViewSlices.value[currentAxis]
                const numSlices = sliceRange[1] - sliceRange[0]
                const sliceThickness = (axisBounds[1] - axisBounds[0]) / numSlices
                const slicePosition = (
                    (currentSlice - sliceRange[0]) / (sliceRange[1] - sliceRange[0])
                    * (axisBounds[1] - axisBounds[0]) + axisBounds[0]
                )

                for (var i = 0; i < visible.length; i++) {
                    const location = coords.slice(i * 3, i * 3 + 3)
                    const axisCoord = location[imageMapper.getSlicingMode()]
                    if (
                        axisCoord >= slicePosition &&
                        axisCoord < (slicePosition + sliceThickness)
                    ) {
                        visible[i] = 1
                    }
                }

                arraysOut.forEach(x => x.modified())
            }
        })
        filteredParticleMapper.setScaleModeToScaleByMagnitude();
        filteredParticleMapper.setScaleFactor(this.glyphSize);
        filteredParticleMapper.setScaleArray('visible')
        filteredParticleMapper.setInputConnection(particleFilter.getOutputPort(), 0)
        filteredParticleMapper.setInputConnection(filteredParticleSphere.getOutputPort(), 1)
        filteredParticleActor.setMapper(filteredParticleMapper);

        const slice = {
            renderer,
            sliceActor,
            imageMapper,
            cutPlane,
            cutter,
            cutMapper,
            cutActor,
            cropFilter,
            particleFilter,
            filteredParticleMapper,
            filteredParticleActor,
        }
        slices.value.push(slice)
        return slice
    },
    updateSlice(slice) {
        const { sliceActor, imageMapper, renderer } = slice;

        let cameraPosition, cameraDirection, cameraViewUp;
        const camera = renderer.getActiveCamera();
        const center = sliceActor.getCenter();
        const distance = camera.getDistance();

        if (['X', 'L'].includes(imageViewAxis.value)) {
            imageMapper.setSlicingMode('I');
            imageMapper.setISlice(imageViewSlices.value.x);
            cameraPosition = [
                center[0] + distance,
                center[1],
                center[2],
            ]
            cameraDirection = [-1, 0, 0]
            cameraViewUp = [0, 1, 0]
        } else if (['Y', 'P'].includes(imageViewAxis.value)) {
            imageMapper.setSlicingMode('J');
            imageMapper.setJSlice(imageViewSlices.value.y);
            cameraPosition = [
                center[0],
                center[1] + distance,
                center[2],
            ]
            cameraDirection = [0, -1, 0]
            cameraViewUp = [0, 0, -1]
        } else if (['Z', 'S'].includes(imageViewAxis.value)) {
            imageMapper.setSlicingMode('K');
            imageMapper.setKSlice(imageViewSlices.value.z);
            cameraPosition = [
                center[0],
                center[1],
                center[2] + distance,
            ]
            cameraDirection = [0, 0, -1]
            cameraViewUp = [0, 1, 0]
        }

        if (cameraPosition && cameraDirection && cameraViewUp) {
            camera.setPosition(...cameraPosition)
            camera.setDirectionOfProjection(...cameraDirection)
            camera.setViewUp(...cameraViewUp)
        }

        if (imageViewIntersectMode.value) {
            this.updateCuttingPlane(slice)
        }
        renderer.resetCamera()
    },
    updateIntersection(slice) {
        // TODO: account for multidomain cases
        const {
            renderer, cutter, cutActor,
            filteredParticleActor, particleFilter, cropFilter,
        } = slice

        const intersectionShape = renderer.getActors().find((actor) => actor.getClassName() != "vtkImageSlice")
        if (intersectionShape) {
            if (imageViewIntersectCropMode.value) {
                // Compare bounds to find crop proportions, apply proportion to image slices
                const fullBounds = cropFilter.getInputData().getBounds()
                const fullSlices = [
                    ...imageViewSliceRanges.value.x,
                    ...imageViewSliceRanges.value.y,
                    ...imageViewSliceRanges.value.z,
                ]
                const padding = 0.01 // pad crop by 1%
                const cropToBounds = intersectionShape.getBounds()
                const cropToProportions = cropToBounds.map((v, i) => {
                    const minIndex = Math.floor((i) / 2) * 2
                    const maxIndex = minIndex + 1
                    const padValue = i % 2 === 0 ? 0 - padding : padding
                    return (v - fullBounds[minIndex]) / (fullBounds[maxIndex] - fullBounds[minIndex]) + padValue
                })
                const cropToSlices = cropToProportions.map((v, i) => {
                    const minIndex = Math.floor((i) / 2) * 2
                    const maxIndex = minIndex + 1
                    return v * (fullSlices[maxIndex] - fullSlices[minIndex]) + fullSlices[minIndex]
                })
                imageViewCroppedSliceRanges.value = {
                    x: cropToSlices.slice(0, 2),
                    y: cropToSlices.slice(2, 4),
                    z: cropToSlices.slice(4, 6),
                }
                // clamp current slices to cropped ranges
                imageViewSlices.value = Object.fromEntries(
                    Object.entries(imageViewSlices.value).map(([axis, slice]) => {
                        const [min, max] = imageViewCroppedSliceRanges.value[axis]
                        if (slice < min) return [axis, min]
                        if (slice > max) return [axis, max]
                        return [axis, slice]
                    })
                )
                cropFilter.setCroppingPlanes(cropToSlices)
            } else {
                cropFilter.reset()
            }
            cutter.setInputData(intersectionShape.getMapper().getInputData())
            cutActor.setVisibility(imageViewIntersectMode.value)
            cutActor.setPosition(1, 1, 1) // ensure cutActor is always in front of sliceActor
            intersectionShape.setVisibility(!imageViewIntersectMode.value)
            renderer.addActor(cutActor);
            renderer.resetCamera()
        }

        // If particles shown, filter by slice bounds
        const particles = renderer.getActors().map(
            (a) => ({
                mapper: a.getMapper(),
                actor: a
            })
        ).find(
            ({ mapper }) => mapper.getClassName() === 'vtkGlyph3DMapper'
        )
        if (particles) {
            particles.actor.setVisibility(!imageViewIntersectMode.value);
            particleFilter.setInputData(particles.mapper.getInputData())
            filteredParticleActor.setVisibility(imageViewIntersectMode.value)
            renderer.addActor(filteredParticleActor)
        } else {
            filteredParticleActor.setVisibility(false)
        }
        this.render()
    },
    updateCuttingPlane(slice) {
        const { imageMapper, cutPlane, particleFilter } = slice;

        const sliceBounds = imageMapper.getBoundsForSlice()
        let origin = [sliceBounds[0], sliceBounds[2], sliceBounds[4]]
        let normal = [0, 0, 0]
        normal[imageMapper.getSlicingMode()] = 1
        cutPlane.setOrigin(origin)
        cutPlane.setNormal(normal)

        // If filtering particles, call modified to trigger filter evaluation
        particleFilter.getInputData()?.modified()
    },
    updateGlyphSize(glyphSize) {
        slices.value.forEach(({ filteredParticleMapper }) => {
            filteredParticleMapper.setScaleFactor(glyphSize)
        })
        this.render()
    },
    addImage(imageData, renderer) {
        let slice = slices.value.find((s) => s.renderer == renderer)
        if (!slice) slice = this.createSlice(renderer)

        imageViewMode.value = true

        slice.cropFilter.setInputData(imageData)
        slice.cropFilter.reset()
        slice.imageMapper.setInputConnection(slice.cropFilter.getOutputPort())
        slice.sliceActor.getProperty().setColorWindow(imageViewWindow.value)
        slice.sliceActor.getProperty().setColorLevel(imageViewLevel.value)

        const dataRange = imageData.getPointData().getScalars().getRange();
        imageViewLevelRange.value = dataRange
        imageViewLevel.value = (dataRange[1] - dataRange[0]) / 2 + dataRange[0]
        imageViewWindowRange.value = [0, (dataRange[1] - dataRange[0])]
        imageViewWindow.value = imageViewWindowRange.value[1]

        const extent = imageData.getExtent();
        imageViewSliceRanges.value = {
            x: [extent[0], extent[1]],
            y: [extent[2], extent[3]],
            z: [extent[4], extent[5]],
        }
        imageViewCroppedSliceRanges.value = imageViewSliceRanges.value

        if (imageViewIntersectMode.value || imageViewIntersectCropMode.value) this.imageViewIntersectModeUpdated()
        this.updateSlice(slice)
    },
    imageViewModeUpdated() {
        // resize render window when visibility of image render options changes
        this.resize();
        this.render();
    },
    imageViewAxisUpdated() {
        slices.value.forEach((slice) => {
            this.updateSlice(slice)
        })
        this.render()
    },
    imageViewSliceUpdated() {
        if (!imageViewAxis.value) {
            return undefined
        }
        slices.value.forEach((slice) => {
            const { imageMapper } = slice;

            if (['X', 'L'].includes(imageViewAxis.value)) {
                imageMapper.setISlice(imageViewSlices.value.x);
            } else if (['Y', 'P'].includes(imageViewAxis.value)) {
                imageMapper.setJSlice(imageViewSlices.value.y);
            } else if (['Z', 'S'].includes(imageViewAxis.value)) {
                imageMapper.setKSlice(imageViewSlices.value.z);
            }
            if (imageViewIntersectMode.value) {
                this.updateCuttingPlane(slice)
            }
        })
        this.render()
    },
    imageViewWindowUpdated() {
        slices.value.forEach(({ sliceActor }) => {
            sliceActor.getProperty().setColorWindow(imageViewWindow.value)
        })
        this.render()
    },
    imageViewLevelUpdated() {
        slices.value.forEach(({ sliceActor }) => {
            sliceActor.getProperty().setColorLevel(imageViewLevel.value)
        })
        this.render()
    },
    imageViewIntersectModeUpdated() {
        slices.value.forEach((slice) => {
            this.updateIntersection(slice);
            this.updateCuttingPlane(slice);
        })
        this.render()
    },
    watchImageStates() {
        watch(imageViewMode, this.imageViewModeUpdated)
        watch(imageViewAxis, this.imageViewAxisUpdated)
        watch(imageViewSlices, this.imageViewSliceUpdated, { deep: true })
        watch(imageViewWindow, this.imageViewWindowUpdated)
        watch(imageViewLevel, this.imageViewLevelUpdated)
        watch(imageViewIntersectMode, this.imageViewIntersectModeUpdated)
        watch(imageViewIntersectCropMode, this.imageViewIntersectModeUpdated)
    },
    resetImageSlices() {
        slices.value = []
    },
    resetIntersections() {
        slices.value.forEach(this.updateIntersection)
    }
}
