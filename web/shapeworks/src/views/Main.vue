<script lang="ts">
import {
    onMounted, ref,
    watch, computed, nextTick,
    onBeforeUnmount,
} from 'vue';
import _ from 'lodash';
import imageReader from '../reader/image';
import pointsReader from '../reader/points';
import { groupBy, shortFileName } from '../helper';
import { AugmentationPair, DataObject, DeepSSMImage, ShapeData, TestingData, TrainingPair } from '@/types';
import ShapeViewer from '../components/ShapeViewer/viewer.vue';
import DataList from '../components/DataList.vue'
import RenderControls from '../components/RenderControls.vue'
import vtkImageData from 'vtk.js/Sources/Common/DataModel/ImageData';
import vtkPolyData from 'vtk.js/Sources/Common/DataModel/PolyData';
import {
    renderLoading,
    selectedDataset,
    allSubjectsForDataset,
    selectedDataObjects,
    loadDataset,
    particleSize,
    particlesForOriginalDataObjects,
    layersShown,
    groomedShapesForOriginalDataObjects,
    selectedProject,
    loadProjectForDataset,
    reconstructionsForOriginalDataObjects,
    analysisFilesShown,
    meanAnalysisParticlesFiles,
    currentAnalysisParticlesFiles,
    switchTab,
    jobAlreadyDone,
    analysisExpandedTab,
    allProjectsForDataset,
    loadProjectsForDataset,
    getLandmarks,
    allSetLandmarks,
    getConstraints,
    allSetConstraints,
    landmarksLoading,
    constraintsLoading,
    imageViewMode,
    deepSSMDataTab,
    deepSSMResult,
    deepSSMAugDataShown,
    allDataObjectsInDataset,
    uniformScale,
    deepSSMSamplePage,
    DEEPSSM_SAMPLES_PER_PAGE,
} from '@/store';
import router from '@/router';
import TabForm from '@/components/TabForm.vue';
import AnalysisTab from '@/components/Analysis/AnalysisTab.vue';
import InfoTab from '@/components/InfoTab.vue';
import DeepSSMTab from '@/components/DeepSSMTab.vue';
import { loadingState } from '../store/index';


export default {
    components: {
        ShapeViewer,
        DataList,
        InfoTab,
        RenderControls,
        TabForm,
        AnalysisTab,
        DeepSSMTab,
    },
    props: {
        dataset: {
            type: Number,
            required: true,
        },
        project: {
            type: Number,
            required: true,
        }
    },
    setup(props) {
        const drawerWidth = ref<number>(600);
        const drawer = ref();
        const renderAreaStyle = computed(() => {
            let width = `calc(100% - ${drawerWidth.value}px)`
            return {
                width,
                position: 'absolute',
                left: `${drawerWidth.value}px`,
                top: imageViewMode.value ? '140px' : '70px',
                height: imageViewMode.value ? 'calc(100% - 140px)' : 'calc(100% - 70px)'
            }
        })

        const tab = ref();
        const rows = ref<number>(1);
        const cols = ref<number>(1);
        const renderData = ref<Record<string, ShapeData[]>>({});
        const renderMetaData = ref<Record<string, ShapeData[]>>({});

        onMounted(async () => {
            try {
                await loadDataset(props.dataset);
                await loadProjectForDataset(props.project);
            } catch(e) {
                console.log(e);
                toSelectPage();
            }
            nextTick(() => {
                window.addEventListener('resize', onResize);
            })
        })

        onBeforeUnmount(() => {
            window.removeEventListener('resize', onResize);
        })

        function onResize() {
            refreshRender()
        }

        async function toSelectPage() {
            selectedProject.value = undefined;
            analysisFilesShown.value = undefined;
            if (allProjectsForDataset.value.length === 0 && selectedDataset.value) {
                loadProjectsForDataset(selectedDataset.value.id);
            }
            router.push('/dataset/'+selectedDataset.value?.id);
        }

        function prepareDrawer() {
            if (drawer.value && drawer.value.$el) {
                let i = drawer.value.$el.querySelector(
                    ".v-navigation-drawer__border"
                );
                i.style.width = "10px";
                i.style.cursor = "ew-resize";
                i.addEventListener(
                    "mousedown",
                    function(e: MouseEvent) {
                        e.preventDefault()
                        if (e.offsetX < 300) {
                            drawer.value.$el.style.transition ='initial';
                            document.addEventListener("mousemove", setDrawerWidth, false);
                        }
                    },
                    false
                );
                document.addEventListener(
                    "mouseup",
                    function() {
                        if (drawer.value) {
                            drawer.value.$el.style.transition = '';
                        }
                        document.body.style.cursor = "";
                        document.removeEventListener("mousemove", setDrawerWidth, false);
                    },
                    false
                );
            }
        }

        function setDrawerWidth(e: MouseEvent) {
            document.body.style.cursor = "ew-resize";
            drawer.value.$el.style.width =  e.clientX + "px";
            drawerWidth.value = e.clientX
        }

        async function refreshRender() {
            // Get landmarks and constraints the first time each layer is enabled,
            // regardless of whether there are objects to render
            let landmarksPromise;
            if(
                layersShown.value.includes("Landmarks") &&
                !allSetLandmarks.value
            ) {
                landmarksPromise = getLandmarks().then(() => {
                    landmarksLoading.value = false
                })
            }

            let constraintsPromise;
            if(
                layersShown.value.includes("Constraints") &&
                !allSetConstraints.value
            ) {
                constraintsPromise = getConstraints().then(() => {
                    constraintsLoading.value = false
                })
            }

            if (selectedDataObjects.value.length == 0) {
                return Promise.all([
                    landmarksPromise,
                    constraintsPromise,
                ])
            }
            renderLoading.value = true
            imageViewMode.value = false
            let newRenderData = {}
            let newRenderMetaData = {}
            const groupedSelections: Record<string, DataObject[]> = groupBy(selectedDataObjects.value, 'subject')
            if (
                analysisFilesShown.value?.length &&
                currentAnalysisParticlesFiles.value?.length &&
                meanAnalysisParticlesFiles.value?.length
            ) {
                // populate newRenderData and renderMetaData
                await Promise.all(
                    analysisFilesShown.value.map(async (f, i) => {
                        if(meanAnalysisParticlesFiles.value && currentAnalysisParticlesFiles.value){
                            const key = analysisExpandedTab.value === 0 ? "PCA": "GROUP"
                            if (!newRenderData[key]) {
                                newRenderData[key] = []
                            }
                            newRenderData[key].push({
                                shape: [  // only one layer, no overlapping shapes
                                    await imageReader(f, shortFileName(f))
                                ],
                                points: await pointsReader(currentAnalysisParticlesFiles.value[i])
                            })

                            if (!newRenderMetaData[key]) {
                                newRenderMetaData[key] = []
                            }
                            const meanParticles = await pointsReader(
                                meanAnalysisParticlesFiles.value[i]
                            )
                            const currParticles = await pointsReader(
                                currentAnalysisParticlesFiles.value[i]
                            )
                            newRenderMetaData[key].push({
                                "mean": {
                                    shape: await imageReader(undefined),
                                    points: meanParticles,
                                },
                                "current": {
                                    shape: await imageReader(undefined),
                                    points: currParticles,
                                }
                            })
                        }
                    })
                )
            }
            else if (tab.value === "deepssm" && deepSSMResult.value) {
                // defaults to subjects selected
                let labelledGroups: Record<string, any> = groupedSelections;
                const trainingImages: DeepSSMImage[] = deepSSMResult.value.images
                const augImages: AugmentationPair[] = deepSSMResult.value.aug_pairs

                switch(deepSSMDataTab.value) {
                    case 0:  // augmentation
                        // populate labelledGroups from aug_pairs
                        // if generated data is shown. Else pass groupedSelections
                        if (deepSSMAugDataShown.value === 'Generated') {
                            const paginatedAugPairs = augImages.slice(DEEPSSM_SAMPLES_PER_PAGE * (deepSSMSamplePage.value - 1), DEEPSSM_SAMPLES_PER_PAGE * deepSSMSamplePage.value)
                            labelledGroups = groupBy(paginatedAugPairs, 'sample_num')
                        }
                        else {
                            labelledGroups = groupedSelections;
                        }
                        break;
                    case 1:  // training
                        // populate from training_pairs
                        labelledGroups = deepSSMResult.value.training_pairs.reduce((acc, obj) => {
                            const key = `${obj.example_type}_${(obj.validation)}`;
                            if (!acc[key]) {
                                acc[key] = [];
                            }
                            acc[key].push(obj);
                            return acc;
                        }, {});

                        // sort labelledGroups where it should go: best true, median true, worst true, best false, median false, worst false
                        // eslint-disable-next-line
                        const order = ['best', 'median', 'worst'];
                        labelledGroups = Object.fromEntries(
                            Object.entries(labelledGroups).sort(
                                // eslint-disable-next-line
                                ([aKey, aVal], [bKey, bVal]) => {
                                    const a = aKey.split('_');
                                    const b = bKey.split('_');
                                    if (a[1] === 'true' && b[1] === 'true') {
                                        return order.indexOf(a[0]) - order.indexOf(b[0]);
                                    } else if (a[1] === 'true') {
                                        return -1;
                                    } else if (b[1] === 'true') {
                                        return 1;
                                    } else {
                                        return order.indexOf(a[0]) - order.indexOf(b[0]);
                                    }
                                }
                            )
                        )
                        break;
                    case 2:  // testing
                        labelledGroups = groupBy(deepSSMResult.value.test_pairs, 'image_id')
                        // filter labelled groups to use only items which have "image_type" == world
                        labelledGroups = Object.fromEntries(
                            Object.entries(labelledGroups).map(([subjectId, dataObjects]) => {
                                const filteredDataObjects = dataObjects.filter((obj) => obj.image_type === 'world');
                                return [subjectId, filteredDataObjects];
                            })
                        );

                        break;
                    default:
                        break;
                }

                newRenderData = Object.fromEntries(
                    await Promise.all(Object.entries(labelledGroups).map(
                        async ([subjectId, dataObjects]) => {
                            let label = subjectId;
                            // prepend "Generated_Sample_" to label is dataObjects is AugmentationPair
                            if ((dataObjects[0] as TrainingPair).example_type) {
                                label = `${dataObjects[0].example_type} ${dataObjects[0].validation ? 'validation' : 'training'}`;
                            }
                            if((dataObjects[0] as AugmentationPair).sample_num) {
                                label = "Generated_Sample_" + subjectId;
                            }
                            if(allSubjectsForDataset.value){
                                const subject = allSubjectsForDataset.value.find(
                                    (subject) => subject.id.toString() === subjectId
                                )
                                if (subject) label = subject.name
                            }
                            const shapeDatas = (await Promise.all(dataObjects.map(
                                (dataObject: DataObject | DeepSSMImage | AugmentationPair | TrainingPair | TestingData) => {
                                    const shapePromises: Promise<any>[] = [];
                                    let shapeURL;
                                    let imageURL;
                                    let particleURL;
                                    // Augmentation
                                    if ('sample_num' in dataObject) {
                                        const d = dataObject as AugmentationPair
                                        shapeURL = d.mesh
                                        imageURL = d.image
                                        particleURL = d.particles
                                        shapePromises.push(
                                            imageReader(imageURL, `${label}.nrrd`)
                                        )
                                        shapePromises.push(
                                            imageReader(shapeURL, `${label}.vtk`)
                                        )
                                    }
                                    // Training
                                    else if ('example_type' in dataObject) {
                                        const d = dataObject as TrainingPair
                                        shapeURL = d.mesh
                                        particleURL = d.particles

                                        if (d.index.startsWith('Generated_sample_')) {
                                            const sample_num = parseInt(d.index.split('_')[2])
                                            imageURL = augImages.find((i) => i.sample_num === sample_num)?.image
                                        } else {
                                            imageURL = trainingImages.find((i) => i.index === d.index)?.image
                                        }

                                        shapePromises.push(
                                            imageReader(imageURL, `${label}.nrrd`)
                                        )
                                        shapePromises.push(
                                            imageReader(shapeURL, `${label}.vtk`, 'DeepSSM')
                                        )
                                    }
                                    // Testing
                                    else if ('image_id' in dataObject) {
                                        const d = dataObject as TestingData
                                        shapeURL = d.mesh
                                        particleURL = d.particles
                                        const image_id = d.image_id

                                        // get subject name from allSubjectsForDataset
                                        const subjectID = allSubjectsForDataset.value.find(
                                            (subject) => subject.name.toString() === image_id
                                        )?.id

                                        // get dataObject for subjectID
                                        const fetchedDataObject = allDataObjectsInDataset.value.find(
                                            (dataObject) => dataObject.subject === subjectID
                                        )

                                        const imageURL = fetchedDataObject?.file

                                        shapePromises.push(
                                            imageReader(imageURL, `${label}.nrrd`)
                                        )
                                        shapePromises.push(
                                            imageReader(shapeURL, `${label}.vtk`, 'DeepSSM')
                                        )
                                    }
                                    else {
                                        shapeURL = (dataObject as DataObject).file
                                        if ("anatomy_type" in dataObject) {
                                            shapePromises.push(
                                                imageReader(shapeURL, `${label}.vtk`, 'Original')
                                            )
                                        } else {
                                            shapePromises.push(
                                                imageReader(shapeURL, `${label}.nrrd`, 'Original')
                                            )
                                        }
                                    }

                                    return Promise.all([
                                        Promise.all(shapePromises),
                                        pointsReader(particleURL),
                                    ])
                                }
                            )))
                            .map((e: any) => ({
                                shape: e[0],
                                points: e[1],
                            }))
                            return [
                                label, shapeDatas
                            ]
                        }
                    )
                ))
            } else {
                newRenderData = Object.fromEntries(
                    await Promise.all(Object.entries(groupedSelections).map(
                        async ([subjectId, dataObjects]) => {
                            let subjectName = subjectId;
                            if(allSubjectsForDataset.value){
                                const subject = allSubjectsForDataset.value.find(
                                    (subject) => subject.id.toString() === subjectId
                                )
                                if (subject) subjectName = subject.name
                            }
                            const shapeDatas = (await Promise.all(dataObjects.map(
                                (dataObject) => {
                                    const shapePromises: Promise<vtkPolyData | vtkImageData>[] = [];
                                    if(layersShown.value.includes("Original")){
                                        const layerLabel = dataObject.anatomy_type ? 'Original' : 'Original - Image'
                                        shapePromises.push(
                                            imageReader(
                                                dataObject.file,
                                                shortFileName(dataObject.file),
                                                layerLabel,
                                                dataObject.anatomy_type && { domain: dataObject.anatomy_type.replace('anatomy_', '') }
                                            )
                                        )
                                    }
                                    if(layersShown.value.includes("Groomed")){
                                        if (
                                            groomedShapesForOriginalDataObjects.value[dataObject.type] &&
                                            groomedShapesForOriginalDataObjects.value[dataObject.type][dataObject.id]
                                        ) {
                                            const shapeURL = groomedShapesForOriginalDataObjects.value[
                                                dataObject.type
                                            ][dataObject.id]?.file
                                            if(shapeURL) {
                                                shapePromises.push(
                                                    imageReader(
                                                        shapeURL,
                                                        shortFileName(shapeURL),
                                                        "Groomed",
                                                        { domain: dataObject.anatomy_type.replace('anatomy_', '') }
                                                    )
                                                )
                                            }
                                        }
                                    }
                                    if(layersShown.value.includes("Reconstructed")){
                                        const targetReconstruction = reconstructionsForOriginalDataObjects.value.find(
                                            (reconstructed) => {
                                                const particles = reconstructed.particles
                                                let originalId;
                                                if(dataObject.type === 'mesh'){
                                                    originalId = particles.groomed_mesh.mesh
                                                } else if (dataObject.type === 'segmentation'){
                                                    originalId = particles.groomed_segmentation.segmentation
                                                }
                                                return originalId === dataObject.id
                                            }
                                        )
                                        if (targetReconstruction) {
                                            const shapeURL = targetReconstruction.file
                                            shapePromises.push(
                                                imageReader(
                                                    shapeURL,
                                                    shortFileName(shapeURL),
                                                    "Reconstructed",
                                                    { domain: targetReconstruction.anatomy_type.replace('anatomy_', '') }
                                                )
                                            )
                                        }
                                    }

                                    let particleURL;
                                    if(layersShown.value.includes("Particles")){
                                        particleURL = particlesForOriginalDataObjects.value[dataObject.type][dataObject.id]?.local
                                    }

                                    return Promise.all([
                                        Promise.all(shapePromises),
                                        pointsReader(particleURL),
                                        landmarksPromise,
                                        constraintsPromise,
                                    ])
                                }
                            )))
                            .map(([imageData, particleData, landmarkData, constraintData]) => ({
                                shape: imageData,
                                points: particleData,
                                landmarks: landmarkData,
                                constraints: constraintData
                            }))
                            return [
                                subjectName, shapeDatas
                            ]
                        }
                    )
                ))
            }

            const n = Object.keys(newRenderData).length;
            const sqrt = Math.ceil(Math.sqrt(n));
            const numGroups = Math.min(sqrt, 5)
            const renderAreaWidth = window.innerWidth - drawerWidth.value
            const renderAreaHeight = window.innerHeight - 120
            const renderAreaRatio = renderAreaWidth / renderAreaHeight
            if (renderAreaRatio > 1) {
                rows.value = Math.ceil(n / numGroups);
                cols.value = numGroups;
            } else {
                cols.value = Math.ceil(n / numGroups);
                rows.value = numGroups;
            }
            renderData.value = newRenderData
            renderMetaData.value = newRenderMetaData
        }

        const debouncedRefreshRender = _.debounce(refreshRender, 300)

        watch(drawer, prepareDrawer)
        watch(selectedDataObjects, debouncedRefreshRender)
        watch(layersShown, debouncedRefreshRender)
        watch(analysisFilesShown, debouncedRefreshRender, {deep: true})
        watch(meanAnalysisParticlesFiles, debouncedRefreshRender, {deep: true})
        watch(deepSSMDataTab, debouncedRefreshRender)
        watch(deepSSMAugDataShown, debouncedRefreshRender)
        watch(uniformScale, debouncedRefreshRender)
        watch(deepSSMSamplePage, debouncedRefreshRender)
        watch(tab, switchTab)

        return {
            loadingState,
            renderLoading,
            drawer,
            drawerWidth,
            setDrawerWidth,
            renderAreaStyle,
            tab,
            rows,
            cols,
            renderData,
            renderMetaData,
            selectedDataset,
            selectedProject,
            selectedDataObjects,
            toSelectPage,
            refreshRender,
            jobAlreadyDone,
            particleSize,
            analysisFilesShown,
        }
    }
}
</script>


<template>
    <div class='content-area' style='height: 100%' v-if="selectedDataset">
        <v-navigation-drawer
            ref="drawer"
            :width="drawerWidth"
            permanent
            absolute
        >
                <v-list-item>
                    <v-list-item-title class="text-h6">
                        <v-tooltip bottom>
                        <template v-slot:activator="{ on, attrs }">
                            <v-icon
                            dark
                            v-bind="attrs"
                            v-on="on"
                            @click="toSelectPage"
                            >
                            mdi-arrow-left
                            </v-icon>
                        </template>
                        <span>Return to dataset/project selection</span>
                        </v-tooltip>
                        Dataset: {{ selectedDataset.name }}
                    </v-list-item-title>
                </v-list-item>
                <v-list-item>
                    <v-icon />
                    <v-tabs v-model="tab" fixed-tabs>
                        <v-tab href="#data">Data</v-tab>
                        <v-tab-item value="data">
                            <data-list :dataset="dataset" autoSelectOne/>
                        </v-tab-item>
                        <v-tab href="#info">Info</v-tab>
                        <v-tab-item value="info">
                            <span
                                v-if="selectedProject && selectedProject.readonly"
                                class="red--text pa-3"
                            >
                                This project is read only.
                                No operations may be performed.
                            </span>
                            <info-tab v-else />
                        </v-tab-item>
                        <v-tab href="#groom">Groom</v-tab>
                        <v-tab-item value="groom">
                            <span
                                v-if="selectedProject && selectedProject.readonly"
                                class="red--text pa-3"
                            >
                                This project is read only.
                                No grooming or optimizing may be performed.
                            </span>
                            <tab-form v-else form="groom" @change="refreshRender"/>
                        </v-tab-item>
                        <v-tab href="#optimize">Optimize</v-tab>
                        <v-tab-item value="optimize">
                            <span
                                v-if="selectedProject && selectedProject.readonly"
                                class="red--text pa-3"
                            >
                                This project is read only.
                                No grooming or optimizing may be performed.
                            </span>
                            <tab-form
                                v-else
                                form="optimize"
                                @change="refreshRender"
                                :prerequisite="() => jobAlreadyDone('groom')"
                                prerequisite_unfulfilled="Perform a groom operation before optimizing."
                            />
                        </v-tab-item>
                        <v-tab href="#analyze">Analyze</v-tab>
                        <v-tab-item value="analyze">
                            <analysis-tab @change="refreshRender" :currentTab="tab || ''"/>
                        </v-tab-item>
                        <v-tab href="#deepssm">DeepSSM</v-tab>
                        <v-tab-item value="deepssm">
                            <DeepSSMTab @change="refreshRender" />
                        </v-tab-item>
                    </v-tabs>
                </v-list-item>
                <br>
        </v-navigation-drawer>
        <v-card :style="renderAreaStyle" class="px-3 render-controls">
            <render-controls @change="refreshRender" :currentTab="tab || ''"/>
        </v-card>

        <v-card :style="renderAreaStyle" class="pa-3">
            <template v-if="selectedDataObjects.length > 0 || analysisFilesShown && analysisFilesShown.length">
                <shape-viewer
                    :data="renderData"
                    :metaData="renderMetaData"
                    :rows="rows"
                    :columns="cols"
                    :glyph-size="particleSize"
                    :currentTab="tab || ''"
                    :drawerWidth="drawerWidth"
                />
            </template>
            <span v-else>Select any number of data objects</span>
            <v-overlay absolute :value="!loadingState && renderLoading" :stop-propagation="true">
                <v-progress-circular indeterminate />
            </v-overlay>
        </v-card>
    </div>
</template>

<style>
.content-area {
    position: relative;
    min-height: calc(100vh - 160px);
    background-color: #1e1e1e;
}
.render-controls {
    height: auto!important;
    top: 0!important;
    z-index: 2;
}
</style>
