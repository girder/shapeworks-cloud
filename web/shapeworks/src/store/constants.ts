import { ref } from 'vue'
import {
    selectedProject,
    groomedShapesForOriginalDataObjects,
    reconstructionsForOriginalDataObjects,
    particlesForOriginalDataObjects
} from '.';

export const layers = ref<Record<string, any>[]>([
    {
        name: 'Original',
        color: 'white',
        rgb: [1, 1, 1],
        available: () => true,
    },
    {
        name: 'Groomed',
        color: 'green',
        rgb: [0, 1, 0],
        available: () => {
            return Object.values(groomedShapesForOriginalDataObjects.value)
            .map((obj) => Object.values(obj).flat()).flat().length > 0
        }
    },
    {
        name: 'Reconstructed',
        color: 'red',
        rgb: [1, 0, 0],
        available: () => {
            return reconstructionsForOriginalDataObjects.value?.length > 0
        },
    },
    {
        name: 'Particles',
        color: undefined,
        rgb: undefined,
        available: () => {
            return Object.values(particlesForOriginalDataObjects.value)
            .map((obj) => Object.values(obj).flat()).flat().length > 0
        }
    },
    {
        name: 'Landmarks',
        color: undefined,
        rgb: undefined,
        available: () => {
            return selectedProject.value?.landmarks_info && selectedProject.value.landmarks_info.length > 0
        }
    },
    {
        name: 'Constraints',
        color: undefined,
        rgb: undefined,
        available: () => {
            return selectedProject.value?.constraints && selectedProject.value.constraints.length > 0
        }
    }
])

export const vtkShapesByType = ref<Record<string, any[]>>({
    "Original": [],
    "Original - Image": [],
    "Groomed": [],
    "Reconstructed": [],
    "Particles": [],
    "DeepSSM": [],
})

export const SPHERE_RESOLUTION = 32;

export const COLORS = [
    [166, 206, 227],
    [31, 120, 180],
    [178, 223, 138],
    [51, 160, 44],
    [251, 154, 153],
    [227, 26, 28],
    [253, 191, 111],
    [255, 127, 0],
    [202, 178, 214],
    [106, 61, 154],
    [255, 255, 153],
    [177, 89, 40],
];

export const DEEPSSM_SAMPLES_PER_PAGE = 12;
