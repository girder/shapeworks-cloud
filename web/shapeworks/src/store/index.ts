import vtkAnnotatedCubeActor from 'vtk.js/Sources/Rendering/Core/AnnotatedCubeActor';
import {
    DataObject, Dataset, Subject,
    Particles, GroomedShape, Project,
    ReconstructedSample, VTKInstance,
    Analysis, Task, LandmarkInfo, Constraints
} from '@/types'
import { ref } from 'vue'

export * from './methods'

export * from './constants'

export const loadingState = ref<boolean>(false)

export const renderLoading = ref<boolean>(false)

export const currentError = ref<string>()

export const vtkInstance = ref<VTKInstance>()

export const allDatasets = ref<Dataset[]>([])

export const selectedDataset = ref<Dataset>()

export const allProjectsForDataset = ref<Project[]>([])

export const selectedProject = ref<Project>()

export const editingProject = ref<undefined | Project>();

export const allSubjectsForDataset = ref<Subject[]>([])

export const allDataObjectsInDataset = ref<DataObject[]>([])

export const anatomies = ref<string[]>([]);

export const selectedDataObjects = ref<DataObject[]>([])

export const orientationIndicator = ref<vtkAnnotatedCubeActor>(vtkAnnotatedCubeActor.newInstance())

export const particleSize = ref<number>(2)

export const reconstructionsForOriginalDataObjects = ref<ReconstructedSample[]>([])

export const particlesForOriginalDataObjects = ref<Record<string, Record<number, Particles>>>({})

export const groomedShapesForOriginalDataObjects = ref<Record<string, Record<number, GroomedShape>>>({})

export const analysis = ref<Analysis>();

export const analysisFilesShown = ref<string[]>();

export const currentAnalysisParticlesFiles = ref<string[]>();

export const meanAnalysisParticlesFiles = ref<string[]>();

export const layersShown = ref<string[]>(["Original"])

export const goodBadAngles = ref<number[][]>();

export const goodBadMaxAngle = ref<number>(45);

export const showGoodBadParticlesMode = ref<boolean>(false);

export const showDifferenceFromMeanMode = ref<boolean>(false);

export const cachedMarchingCubes = ref({})

export const cachedParticleComparisonVectors = ref<{[key: string]: number[][]}>({})

export const cachedParticleComparisonColors = ref<{[key: string]: number[]}>({})

export const landmarkInfo = ref<LandmarkInfo[]>([]);

export const landmarksLoading = ref(true);

export const landmarkSize = ref(2);

export const allSetLandmarks = ref<Record<string, object>>();

export const currentLandmarkPlacement = ref();

export const constraintInfo = ref<Constraints[]>([]);

export const constraintsLoading = ref(true);

export const constraintsShown = ref([]);

export const allSetConstraints = ref<Record<string, object>>();

export const currentConstraintPlacement = ref();

export const constraintPaintRadius = ref(3);

export const constraintPaintExclusion = ref(true);

export const currentTasks = ref<Record<number, Record<string, Task| undefined>>>({})

export const jobProgressPoll = ref();

export const analysisExpandedTab = ref(0);

export const analysisAnimate = ref<boolean>(false);

export const imageViewMode = ref<boolean>(false);

export const imageViewIntersectMode = ref<boolean>(false);

export const imageViewIntersectCropMode = ref<boolean>(false);

export const imageViewAxis = ref<string>('Z');

export const imageViewSlices = ref({x: 0, y: 0, z: 0});

export const imageViewSliceRanges = ref({x: [0, 1], y: [0, 1], z: [0, 1]});

export const imageViewCroppedSliceRanges = ref({x: [0, 1], y: [0, 1], z: [0, 1]});

export const imageViewWindow = ref<number>(0);

export const imageViewWindowRange = ref<number[]>([0, 1]);

export const imageViewLevel = ref<number>(0);

export const imageViewLevelRange = ref<number[]>([0, 1]);
