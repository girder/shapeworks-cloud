import 'vtk.js/Sources/Rendering/Profiles/All';
import vtkInteractorStyleTrackballCamera from 'vtk.js/Sources/Interaction/Style/InteractorStyleTrackballCamera';
import vtkOpenGLRenderWindow from 'vtk.js/Sources/Rendering/OpenGL/RenderWindow';
import vtkRenderWindow from 'vtk.js/Sources/Rendering/Core/RenderWindow';
import vtkRenderWindowInteractor from 'vtk.js/Sources/Rendering/Core/RenderWindowInteractor';
import vtkColorTransferFunction from 'vtk.js/Sources/Rendering/Core/ColorTransferFunction';
import vtkColorMaps from 'vtk.js/Sources/Rendering/Core/ColorTransferFunction/ColorMaps';

import methods from './methods';
import { vtkInstance, showDifferenceFromMeanMode } from '@/store';


export default {
    props: {
        data: {
            type: Object,
            required: true,
        },
        metaData: {
            type: Object,
            required: false,
        },
        rows: {
            type: Number,
            required: true,
        },
        columns: {
            type: Number,
            required: true,
        },
        glyphSize: {
            type: Number,
            required: true,
        },
        currentTab: {
            type: String,
            required: true,
        },
        drawerWidth: {
            type: Number,
            required: false,
        },
    },
    computed: {
        grid() {
            const grid = [];
            const nx = this.columns;
            const ny = this.rows;
            for (let y = 0; y < ny; y += 1) {
                for (let x = 0; x < nx; x += 1) {
                    const xmin = x / nx;
                    const ymin = y / ny;
                    const xmax = (x + 1) / nx;
                    const ymax = (y + 1) / ny;
                    grid.push([xmin, 1 - ymax, xmax, 1 - ymin]);
                }
            }
            return grid;
        },
        labelCanvas() {
            return this.$refs.labels;
        },
        labelCanvasContext() {
            return this.labelCanvas.getContext("2d");
        },
        showDifferenceFromMeanMode() {
            return showDifferenceFromMeanMode.value
        },
    },
    watch: {
        data() {
            this.renderGrid();
        },
        grid() {
            this.renderGrid();
        },
        glyphSize() {
            this.updateGlyphSize(this.glyphSize)
            this.vtk.pointMappers.forEach((mapper) => {
                mapper.setScaleFactor(this.glyphSize);
            });
            this.render();
        },
        drawerWidth() {
            this.updateSize()
        }
    },
    beforeDestroy() {
        this.vtk.interactor.unbindEvents();
        this.vtk.orientationCube.delete();
        this.vtk.openglRenderWindow.setContainer(null);
    },
    created() {
        const renderWindow = vtkRenderWindow.newInstance();
        const openglRenderWindow = vtkOpenGLRenderWindow.newInstance();
        renderWindow.addView(openglRenderWindow);

        const interactor = vtkRenderWindowInteractor.newInstance();
        interactor.setView(openglRenderWindow);
        interactor.initialize();
        interactor.setInteractorStyle(vtkInteractorStyleTrackballCamera.newInstance());
        interactor.onAnimation(this.syncCameras)
        interactor.disable()

        const orientationCube = this.newOrientationCube(interactor)

        this.lookupTable = vtkColorTransferFunction.newInstance();
        this.lookupTable.applyColorMap(
            vtkColorMaps.getPresetByName('erdc_rainbow_bright')
        );
        this.lookupTable.setMappingRange(0, 1)
        this.lookupTable.updateRange();

        this.vtk = {
            renderWindow,
            interactor,
            openglRenderWindow,
            orientationCube,
            renderers: {},
            pointMappers: [],
            widgetManagers: {},
        };

        vtkInstance.value = this.vtk
    },
    mounted() {
        const el = this.$refs.vtk;
        this.vtk.openglRenderWindow.setContainer(el);
        this.vtk.interactor.bindEvents(el);

        this.updateSize();
        this.renderGrid();
        this.watchWidgetStates();
        this.watchImageStates();
    },
    updated() {
        this.prepareColorScale()
    },
    methods,
};
