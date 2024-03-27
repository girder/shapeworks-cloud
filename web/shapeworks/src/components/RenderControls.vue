<script lang="ts">
import { setDatasetThumbnail, setProjectThumbnail } from '@/api/rest';
import { computed, ref, watch } from 'vue';
import {
    particleSize,
    layers,
    layersShown,
    orientationIndicator,
    selectedDataObjects,
    selectedDataset,
    selectedProject,
    vtkInstance,
    allDatasets,
    allProjectsForDataset,
    showDifferenceFromMeanMode,
    analysisFilesShown,
    showGoodBadParticlesMode,
    goodBadMaxAngle,
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
} from '@/store';


export default {
    props: {
        currentTab: {
            type: String,
            required: true,
        }
    },
    setup(props, context) {
        orientationIndicator.value.setDefaultStyle({
            fontStyle: 'bold',
            fontFamily: 'Arial',
            fontColor: 'black',
            faceColor: '#ffffff',
            faceRotation: 0,
            edgeThickness: 0.1,
            edgeColor: 'black',
            resolution: 400,
        })

        const axisSystemOptions = [
            {
                text: 'XYZ',
                value: 'xyz',
                xPlus: '+X',
                xMinus: '-X',
                yPlus: '+Y',
                yMinus: '-Y',
                zPlus: '+Z',
                zMinus: '-Z',
                axes: ['X', 'Y', 'Z'],
            },
            {
                text: 'Medical',
                value: 'slp',
                xPlus: 'L',
                xMinus: 'R',
                yPlus: 'P',
                yMinus: 'A',
                zPlus: 'S',
                zMinus: 'I',
                axes: ['L', 'P', 'S'],
            }
        ]
        const axisSystem = ref()

        function changeAxisSystem(newSystemValue: string){
            const newSystem = axisSystemOptions.find(
                (system) => system.value == newSystemValue
            )
            axisSystem.value = newSystem
            if(newSystem){
                orientationIndicator.value.setXPlusFaceProperty({
                    text: newSystem.xPlus
                })
                orientationIndicator.value.setXMinusFaceProperty({
                    text: newSystem.xMinus
                })
                orientationIndicator.value.setYPlusFaceProperty({
                    text: newSystem.yPlus
                })
                orientationIndicator.value.setYMinusFaceProperty({
                    text: newSystem.yMinus
                })
                orientationIndicator.value.setZPlusFaceProperty({
                    text: newSystem.zPlus
                })
                orientationIndicator.value.setZMinusFaceProperty({
                    text: newSystem.zMinus
                })
                context.emit("change")
            }
        }
        changeAxisSystem('xyz')

        function resetView() {
            context.emit("change")
        }
        watch(showDifferenceFromMeanMode, resetView)
        watch(showGoodBadParticlesMode, resetView)
        watch(goodBadMaxAngle, resetView)

        const thumbnailTarget = computed(() => {
            if(layersShown.value.length === 1 && layersShown.value[0] === "Original") {
                // showing only original data object, valid for dataset thumbnail
                return {
                    type: 'Dataset',
                    id: selectedDataset.value?.id
                }
            } else {
                // valid for project thumbnail
                return {
                    type: 'Project',
                    id: selectedProject.value?.id
                }
            }
        })

        async function captureThumbnail() {
            if(vtkInstance.value) {
                vtkInstance.value.orientationCube.setEnabled(false)
                const encoded = (await Promise.all(
                    // method signature for captureImages is defined as returning void,
                    // but it returns a list of promises.
                    // @ts-ignore
                    vtkInstance.value.renderWindow.captureImages(
                        "image/png",
                        {
                            size: [100, 100]
                        }
                    )
                ))[0] as String
                const thumbnail = encoded.split(',')[1]
                if (thumbnailTarget.value.type === 'Dataset') {
                    if (thumbnailTarget.value.id) {
                        let dataset = await setDatasetThumbnail(thumbnailTarget.value.id, thumbnail)
                        if(dataset) {
                            allDatasets.value = allDatasets.value.map((d) => {
                                if (d.id === dataset.id) return dataset
                                return d
                            })
                            selectedDataset.value = dataset;
                        }
                    }
                } else {
                    if (thumbnailTarget.value.id) {
                        let project = await setProjectThumbnail(thumbnailTarget.value.id, thumbnail)
                        if(project) {
                            allProjectsForDataset.value = allProjectsForDataset.value.map((p) => {
                                if (p.id === project.id) return project
                                return p
                            })
                            selectedProject.value = project;
                        }
                    }
                }
                vtkInstance.value.orientationCube.setEnabled(true)
            }
        }

        const showAnalysisOptions = computed(() => {
            return props.currentTab === 'analyze' && analysisFilesShown.value?.length;
        })

        const imageIntersectAllowed = computed(() => {
            // TODO: Add other applicable layers here
            return layersShown.value.includes('Groomed')
        })

        const imageViewSlice = computed(() => {
            if (!imageViewAxis.value) {
                return undefined
            } else if (['X', 'L'].includes(imageViewAxis.value)) {
                return imageViewSlices.value.x
            } else if (['Y', 'P'].includes(imageViewAxis.value)) {
                return imageViewSlices.value.y
            } else if (['Z', 'S'].includes(imageViewAxis.value)) {
                return imageViewSlices.value.z
            }
        })

        const imageViewSliceRange = computed(() => {
            if (!imageViewAxis.value) {
                return undefined
            } else if (['X', 'L'].includes(imageViewAxis.value)) {
                return imageViewIntersectCropMode.value ? imageViewCroppedSliceRanges.value.x : imageViewSliceRanges.value.x
            } else if (['Y', 'P'].includes(imageViewAxis.value)) {
                return imageViewIntersectCropMode.value ? imageViewCroppedSliceRanges.value.y : imageViewSliceRanges.value.y
            } else if (['Z', 'S'].includes(imageViewAxis.value)) {
                return imageViewIntersectCropMode.value ? imageViewCroppedSliceRanges.value.z : imageViewSliceRanges.value.z
            }
        })

        function changeImageViewSlice(value) {
            if (!imageViewAxis.value) {
                return undefined
            } else if (['X', 'L'].includes(imageViewAxis.value)) {
                imageViewSlices.value.x = value
            } else if (['Y', 'P'].includes(imageViewAxis.value)) {
                imageViewSlices.value.y = value
            } else if (['Z', 'S'].includes(imageViewAxis.value)) {
                imageViewSlices.value.z = value
            }
        }

        watch(imageIntersectAllowed, (value) => {
            if (!value) {
                imageViewIntersectMode.value = false
                imageViewIntersectCropMode.value = false
            }
        })

        return {
            particleSize,
            layersShown,
            layers,
            axisSystem,
            axisSystemOptions,
            imageViewMode,
            imageViewIntersectMode,
            imageViewIntersectCropMode,
            imageIntersectAllowed,
            imageViewAxis,
            imageViewSlice,
            imageViewSliceRange,
            imageViewLevel,
            imageViewLevelRange,
            imageViewWindow,
            imageViewWindowRange,
            changeImageViewSlice,
            changeAxisSystem,
            resetView,
            selectedDataObjects,
            captureThumbnail,
            thumbnailTarget,
            showDifferenceFromMeanMode,
            showAnalysisOptions,
        }
    }
}
</script>

<template>
    <div>
        <div class="render-control-row">
            <v-select
                v-model="layersShown"
                v-if="!showAnalysisOptions"
                :items="layers"
                :item-disabled="(layer) => !layer.available()"
                item-value="name"
                label="Layers shown"
                style="width: 500px"
                multiple
                small-chips
                item-text="name"
            >
                <template #selection="{ item }">
                    <v-chip
                        close
                        @click:close="layersShown = layersShown.filter((l) => l !== item.name)"
                        :color="item.color"
                        :text-color="item.color === 'white' ? 'black' : 'white'"
                    >
                        {{ item.name }}
                    </v-chip>
                </template>
            </v-select>
            <v-text-field
                v-model.number="particleSize"
                v-if="!showAnalysisOptions && layersShown.includes('Particles')"
                label="Particle Size"
                type="number"
                style="width: 80px"
                step="0.5"
                min="0.5"
                max="10"
                hide-details
            />
            <v-select
                :value="axisSystem"
                :items="axisSystemOptions"
                @change="changeAxisSystem"
                label="Axis System"
                style="width: 150px"
            />
            <v-switch
                v-if="showAnalysisOptions"
                v-model="showDifferenceFromMeanMode"
                label="Show difference from mean"
            />
            <v-btn
                class="my-5"
                v-if="!showAnalysisOptions && selectedDataObjects.length === 1"
                @click="captureThumbnail"
            >
                Set {{ thumbnailTarget.type }} thumbnail
            </v-btn>
            <v-btn
                class="my-5"
                @click="resetView"
            >
                Reset view
            </v-btn>
        </div>
        <div class="render-control-row" v-if="imageViewMode && axisSystem">
            <div  v-if="imageIntersectAllowed">
                <v-checkbox
                    v-model="imageViewIntersectMode"
                    label="Intersect"
                    :dense="true"
                    :hide-details="true"
                    class="mt-0 pt-0"
                />
                <v-checkbox
                    v-model="imageViewIntersectCropMode"
                    label="Crop"
                    :dense="true"
                    :hide-details="true"
                />
            </div>
            <v-select
                v-model="imageViewAxis"
                :items="axisSystem.axes"
                label="Axis"
                style="width: 25%"
                :hide-details="true"
            />
            <v-slider
                v-if="imageViewSliceRange"
                :value="imageViewSlice"
                :min="imageViewSliceRange[0]"
                :max="imageViewSliceRange[1]"
                :thumb-label="true"
                label="Slice"
                style="width: 25%"
                @input="changeImageViewSlice"
                :hide-details="true"
            />
            <v-slider
                v-model="imageViewWindow"
                :min="imageViewWindowRange[0]"
                :max="imageViewWindowRange[1]"
                :thumb-label="true"
                label="Window"
                style="width: 25%"
                :hide-details="true"
            />
            <v-slider
                v-model="imageViewLevel"
                :min="imageViewLevelRange[0]"
                :max="imageViewLevelRange[1]"
                :thumb-label="true"
                label="Level"
                style="width: 25%"
                :hide-details="true"
            />
        </div>
    </div>
</template>

<style scoped>
.render-control-row {
    display: flex;
    width: 100%;
    height: 70px;
    justify-content: space-between;
    align-items: center;
    column-gap: 20px;
}
.render-control-row > * {
    flex-grow: 0;
}
</style>
