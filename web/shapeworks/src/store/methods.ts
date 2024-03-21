import { AnalysisParams, CacheComparison, LandmarkInfo, Project, Task } from "@/types";
import {
     loadingState,
     selectedDataset,
     selectedProject,
     allProjectsForDataset,
     layersShown,
     particlesForOriginalDataObjects,
     allDataObjectsInDataset,
     analysis,
     cachedMarchingCubes,
     currentTasks,
     groomedShapesForOriginalDataObjects,
     jobProgressPoll,
     reconstructionsForOriginalDataObjects,
     cachedParticleComparisonColors,
     cachedParticleComparisonVectors,
     allDatasets,
     goodBadAngles,
     landmarkColorList,
     landmarkInfo,
     analysisExpandedTab,
     selectedDataObjects,
     particleSize,
     analysisFilesShown,
     meanAnalysisParticlesFiles,
     currentAnalysisParticlesFiles,
     goodBadMaxAngle,
     showDifferenceFromMeanMode,
     showGoodBadParticlesMode,
     analysisAnimate,
} from ".";
import imageReader from "@/reader/image";
import pointsReader from "@/reader/points";
import generateMapper from "@/reader/mapper";
import {
    abortTask,
    analyzeProject,
    deleteTaskProgress,
    getDataset,
    getDatasets,
    getGroomedShapeForDataObject, getOptimizedParticlesForDataObject,
    getProjectsForDataset,
    getReconstructedSamplesForProject,
    getTaskProgress,
    groomProject, optimizeProject, refreshProject,
    deepssmRunProject,
} from '@/api/rest';
import { layers, COLORS } from "./constants";
import { getDistance, hexToRgb } from "@/helper";
import router from "@/router";

export const resetState = () => {
    selectedDataObjects.value = [];
    layersShown.value = ['Original'];
    landmarkInfo.value = undefined;
    landmarkColorList.value = [];
    currentTasks.value = {};
    jobProgressPoll.value = undefined;
    particleSize.value = 2;
    analysis.value = undefined;
    analysisExpandedTab.value = 0;
    analysisFilesShown.value = undefined;
    currentAnalysisParticlesFiles.value = undefined;
    meanAnalysisParticlesFiles.value = undefined;
    goodBadAngles.value = undefined;
    goodBadMaxAngle.value = 45;
    showGoodBadParticlesMode.value = false;
    showDifferenceFromMeanMode.value = false;
    cachedMarchingCubes.value = {};
    cachedParticleComparisonVectors.value = {};
    cachedParticleComparisonColors.value = {};
    landmarkInfo.value = undefined;
    landmarkColorList.value = [];
    analysisExpandedTab.value = 0;
    analysisAnimate.value = false;
}

export const loadDataset = async (datasetId: number) => {
    // Only reload if something has changed
    if (selectedDataset.value?.id != datasetId) {
        loadingState.value = true;
        selectedDataset.value = await getDataset(datasetId);
        loadingState.value = false;
    }
}

export async function getAllDatasets() {
    const searchText = router.currentRoute.params.searchText;
    loadingState.value = true;
    allDatasets.value = (await getDatasets(searchText)).sort((a, b) => {
        if(a.created < b.created) return 1;
        if(a.created > b.created) return -1;
        return 0;
    });
    loadingState.value = false;
}

export const loadProjectForDataset = async (projectId: number) => {
    refreshProject(projectId).then((proj) => {
        selectedProject.value = proj
        getLandmarks()
    });
}

export const loadProjectsForDataset = async (datasetId: number) => {
    const searchText = router.currentRoute.params.searchText;
    loadingState.value = true;
    allProjectsForDataset.value = (await getProjectsForDataset(searchText, datasetId)).sort((a, b) => {
        if(a.created < b.created) return 1;
        if(a.created > b.created) return -1;
        return 0;
    });
    loadingState.value = false;
}

export const selectProject = (projectId: number | undefined) => {
    if (projectId) {
        resetState();
        selectedProject.value = allProjectsForDataset.value.find(
            (project: Project) => project.id == projectId,
        )
        getLandmarks();
    }
}

export const loadParticlesForObject = async (type: string, id: number) => {
    let particles = await getOptimizedParticlesForDataObject(
        type, id, selectedProject.value?.id
    )
    if (particles.length > 0) particles = particles[0]
    if (!particlesForOriginalDataObjects.value[type]) {
        particlesForOriginalDataObjects.value[type] = {}
    }
    particlesForOriginalDataObjects.value[type][id] = particles
}

export const loadGroomedShapeForObject = async (type: string, id: number) => {
    let groomed = await getGroomedShapeForDataObject(
        type, id, selectedProject.value?.id
    )
    if (groomed.length > 0) groomed = groomed[0]
    if (!groomedShapesForOriginalDataObjects.value[type]) {
        groomedShapesForOriginalDataObjects.value[type] = {}
    }
    groomedShapesForOriginalDataObjects.value[type][id] = groomed
}

export const loadReconstructedSamplesForProject = async (type: string, id: number) => {
    if (selectedProject.value) {
        reconstructionsForOriginalDataObjects.value = await getReconstructedSamplesForProject(
            type, id, selectedProject.value?.id
        )
    }
}

export const loadDeepSSMDataForProject = async (id: number) => {
    // TODO: implement
    if (selectedProject.value) {
        return;
    }
}

export function jobAlreadyDone(action: string): Boolean {
    let layer;
    switch (action) {
        case 'groom':
            layer = layers.value?.find((layer) => layer.name === 'Groomed')
            return layer ? layer.available() : false
        case 'optimize':
            layer = layers.value?.find((layer) => layer.name === 'Particles')
            return layer ? layer.available() : false
        case 'analyze':
            return false;
        default:
            return false;
    }
}

export async function spawnJob(action: string, payload: Record<string, any>): Promise<any> {
    if (Object.keys(payload).every((key) => key.includes("section") || key.includes("analysis"))) {
        payload = Object.assign({}, ...Object.values(payload))
    }
    const projectId = selectedProject.value?.id;
    if (!projectId) return undefined
    switch (action) {
        case 'groom':
            layersShown.value = layersShown.value.filter(
                (l) => l !== 'Groomed'
            )
            return (await groomProject(projectId, payload))?.data
        case 'optimize':
            layersShown.value = layersShown.value.filter(
                (l) => l !== 'Particles'
            )
            return (await optimizeProject(projectId, payload))?.data
        case 'analyze':
            layersShown.value = layersShown.value.filter(
                (l) => l !== 'Reconstructed'
            )
            return (await analyzeProject(projectId, payload as AnalysisParams))?.data
        case 'deepssm':
            return (await deepssmRunProject(projectId, payload))?.data
        default:
            break;
    }
    return undefined;
}

export async function spawnJobProgressPoll() {
    jobProgressPoll.value = setInterval(pollJobProgress, 1000)
}

export async function pollJobProgress() {
    if (selectedProject.value && currentTasks.value[selectedProject.value.id]) {
        const refreshedTasks = await Promise.all(
            Object.entries(currentTasks.value[selectedProject.value.id])
                .map(async ([taskName, task]) => {
                    if (task?.id) {
                        task = await getTaskProgress(task.id)
                        if (task?.id && task?.percent_complete === 100) {
                            await deleteTaskProgress(task?.id)
                            task.id = undefined
                            setTimeout(() => {
                                if (selectedProject.value) {
                                    currentTasks.value[selectedProject.value.id][taskName] = undefined
                                }
                            }, 1000)
                            fetchJobResults(taskName.replace('_task', ''))
                        }
                    }
                    return [taskName, task]
                }))
        currentTasks.value[selectedProject.value.id] = Object.fromEntries(refreshedTasks)
        currentTasks.value = { ...currentTasks.value }  // reassign for watch response
        if (
            Object.values(currentTasks.value[selectedProject.value.id])
                .every(task => task?.id === undefined)
        ) {
            clearInterval(jobProgressPoll.value)
            jobProgressPoll.value = undefined
        }
    }
}

export async function fetchJobResults(taskName: string) {
    if (!selectedProject.value) {
        return;
    }
    const refreshedProject = await refreshProject(selectedProject.value.id)
    let layerName: string = ''
    let loadFunction: Function | undefined = undefined
    switch (taskName) {
        case 'groom':
            layerName = 'Groomed'
            loadFunction = loadGroomedShapeForObject
            break;
        case 'optimize':
            layerName = 'Particles'
            loadFunction = loadParticlesForObject
            break;
        case 'analyze':
            layerName = 'Reconstructed'
            loadFunction = loadReconstructedSamplesForProject
            analysis.value = refreshedProject?.last_cached_analysis
            if (analysis.value) {
                if (analysis.value.good_bad_angles) {
                    goodBadAngles.value = analysis.value.good_bad_angles
                }
            }
            break;
        case 'deepssm':
            layerName = 'Groomed'
            loadFunction = loadDeepSSMDataForProject
            break;
    }
    if (layerName && loadFunction) {
        await Promise.all(allDataObjectsInDataset.value.map(
            (dataObject) => loadFunction ? loadFunction(dataObject.type, dataObject.id) : undefined
        ))
        cachedMarchingCubes.value = Object.fromEntries(
            Object.entries(cachedMarchingCubes.value).filter(
                ([cachedLabel]) => !cachedLabel.includes(layerName)
            )
        )
        const layer = layers.value.find((l) => l.name === layerName)
        if (layer?.available() && !layersShown.value.includes(layerName)) {
            layersShown.value = [...layersShown.value, layerName]
        }
    }
}

export async function abort(task: Task) {
    if (task.id) abortTask(task.id)
    if (selectedProject.value) {
        currentTasks.value[selectedProject.value.id] = {}
    }
    clearInterval(jobProgressPoll.value)
    jobProgressPoll.value = undefined
}

export async function switchTab(tabName: string) {
    if (!selectedProject.value) {
        return;
    }
    const refreshedProject = await refreshProject(selectedProject.value.id)
    switch (tabName) {
        // add any other tab-switching updates here
        case 'analyze':
            if (refreshedProject && !currentTasks.value[selectedProject.value.id]) {
                analysis.value = refreshedProject.last_cached_analysis
                if (analysis.value) {
                    if (analysis.value.good_bad_angles) {
                        goodBadAngles.value = analysis.value.good_bad_angles
                    }
                }
            }
    }
}

export function calculateComparisons(mapper: any, currentPoints: number[], meanPoints: number[]) {
    const vectorValues: number[][] = []
    let colorValues: number[] = []
    for (let i = 0; i < currentPoints.length; i += 3){
        const currentParticle = currentPoints.slice(i, i+3)
        const meanParticle = meanPoints.slice(i, i+3)
        const distance = getDistance(currentParticle as number[], meanParticle as number[], true)
        vectorValues.push([...currentParticle, distance])
    }

    const pointLocations = mapper.getInputData().getPoints().getData()
    const normals = mapper.getInputData().getPointData().getArrayByName('Normals').getData()
    colorValues = Array.from(
        [...Array(pointLocations.length / 3).keys()].map(
        (i) =>  {
            let colorVal = 0;
            const location = pointLocations.slice(i * 3, i * 3 + 3)
            const normal = normals.slice(i * 3, i * 3 + 3)
            const nearbyParticles = vectorValues.map(
            (p, i) => [getDistance(p.slice(0, 3), location), i, ...p]
            ).sort((a, b) => a[0] - b[0]).slice(0, 10)
            const nearestParticleIndex = nearbyParticles[0][1]
            if (vectorValues[nearestParticleIndex].length < 5){
            vectorValues[nearestParticleIndex].push(...normal)
            }
            colorVal = nearbyParticles[0][5]
            nearbyParticles.slice(1).forEach((p) => {
            const weight = 1 / p[0];
            colorVal = (colorVal * (1 - weight)) + (p[5] * weight)
            })
            return colorVal/10 + 0.5
        }
        )
    )

    return { colorValues: colorValues, vectorValues: vectorValues }
}

export function cacheComparison(colorValues: number[], vectorValues: number[][], particleComparisonKey: string) {
    cachedParticleComparisonColors.value[particleComparisonKey] = colorValues
    cachedParticleComparisonVectors.value[particleComparisonKey] = vectorValues
}

export async function cacheAllComparisons(comparisons: CacheComparison[][]) {
    if (comparisons !== undefined) {
        const cachePrep = await Promise.all(comparisons?.map(async (g) => {
            return await Promise.all(
                g.map(async (domain, i) => {
                    if(meanAnalysisParticlesFiles.value && meanAnalysisParticlesFiles.value.length > i){
                        const particleComparisonKey = domain.particles;

                        if (!cachedParticleComparisonColors.value[particleComparisonKey]) { // if the comparison is NOT already cached
                            const compareToPoints = await pointsReader(meanAnalysisParticlesFiles.value[i]);
                            const currentPoints = await pointsReader(domain.particles);

                            const currentMesh = await imageReader(domain.file, "current_mesh.vtk");

                            return {
                                "compareTo": {
                                    points: compareToPoints.getPoints().getData(),
                                    particleUrl: domain,
                                },
                                "current":  {
                                    points: currentPoints.getPoints().getData(),
                                    mapper: generateMapper(currentMesh),
                                    particleUrl: domain.particles,
                                },
                            }
                        }
                    }
                })
            )
        }))

        cachePrep.forEach((g) => {
            if (g !== undefined) {
                g.forEach((c) => {
                    if (c){
                        const { current, compareTo } = c;
                        const comparisons = calculateComparisons(current.mapper, current.points as number[], compareTo.points as number[])
                        cacheComparison(comparisons.colorValues, comparisons.vectorValues, current.particleUrl);
                    }
                })
            }
        })
    }
}

export function updateLandmarkColorList() {
    landmarkColorList.value = landmarkInfo.value.map(
        (info: LandmarkInfo) => info.color
    )
}

export async function getLandmarks() {
    if (selectedProject.value?.landmarks){
        const subjectParticles = await Promise.all(
            selectedProject.value.landmarks.map(
                async (subjectLandmarks) => {
                    const locations = await pointsReader(subjectLandmarks.file)
                    return locations.getPoints().getNumberOfPoints()
                }
            )
        )
        if (subjectParticles.length > 0){
            const numRows = Math.max(...subjectParticles)
            landmarkInfo.value = [...Array(numRows).keys()].map((index) => {
                let currentInfo = {
                    id: index,
                    color: COLORS[index % COLORS.length],
                    name: `L${index}`,
                    num_set: subjectParticles.filter(
                        (numLocations) => numLocations > index
                    ).length,
                    comment: undefined,

                }
                if (selectedProject.value?.landmarks_info && selectedProject.value.landmarks_info.length > index) {
                    currentInfo = Object.assign(
                        currentInfo,
                        selectedProject.value?.landmarks_info[index]
                    )
                }
                if (currentInfo.color.toString().includes("#")) {
                    currentInfo.color = hexToRgb(currentInfo.color.toString())
                }
                return currentInfo
            })
            updateLandmarkColorList()
        }
    }
}
