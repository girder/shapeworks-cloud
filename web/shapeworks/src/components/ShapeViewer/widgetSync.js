import _ from 'lodash';

import vtkPickerManipulator from 'vtk.js/Sources/Widgets/Manipulators/PickerManipulator';
import vtkWidgetManager from 'vtk.js/Sources/Widgets/Core/WidgetManager';
import vtkSeedWidget from 'vtk.js/Sources/Widgets/Widgets3D/SeedWidget';
import vtkPaintWidget from 'vtk.js/Sources/Widgets/Widgets3D/PaintWidget';
import vtkImplicitPlaneWidget from 'vtk.js/Sources/Widgets/Widgets3D/ImplicitPlaneWidget'
import vtkColorTransferFunction from 'vtk.js/Sources/Rendering/Core/ColorTransferFunction';
import vtkDataArray from 'vtk.js/Sources/Common/Core/DataArray';

import { kdTree } from 'kd-tree-javascript';
import { distance } from '@/helper'
import { ref, watch } from 'vue'

import {
    layersShown,
    landmarkInfo, landmarkSize, currentLandmarkPlacement,
    getLandmarkLocation, setLandmarkLocation,
    allSetLandmarks, reassignLandmarkNumSetValues,
    constraintInfo, constraintsShown, allSetConstraints, currentConstraintPlacement,
    getConstraintLocation, setConstraintLocation,
    constraintPaintRadius, constraintPaintExclusion,
} from '@/store';

const manipulators = ref({});  // organized by label, domain
const dataKDTrees = ref({});   // organized by label, domain
const shapeKDTrees = ref({});   // organized by label, domain
const seedWidgets = ref({});  // organized by label, domain, id
const planeWidgets = ref({});  // organized by label, domain, id
const paintWidgets = ref({});  // organized by label, domain, id

export default {
    // ---------------------
    // Initialization
    // ---------------------
    initializeWidgets() {
        // called when shapes or layers shown have changed
        this.vtk.widgetManagers = {}
        Object.entries(this.vtk.renderers).forEach(([label, renderer]) => {
            manipulators.value[label] = {}
            const wm = vtkWidgetManager.newInstance()
            wm.setRenderer(renderer)
            wm.disablePicking();
            this.vtk.widgetManagers[label] = wm
            renderer.getActors().forEach((actor) => {
                const domain = actor.getMapper()?.getInputData()?.getFieldData()?.getArrayByName('domain')?.getData()[0]
                if (!manipulators.value[label][domain]) {
                    const m = vtkPickerManipulator.newInstance()
                    m.getPicker().addPickList(actor)
                    manipulators.value[label][domain] = m
                }
                if (layersShown.value.includes('Landmarks')) {
                    const existingWidgets = seedWidgets.value[label]
                    if (existingWidgets) {
                        Object.values(existingWidgets).forEach((ws) => {
                            Object.values(ws).forEach((w) => {
                                const widgetHandle = wm.addWidget(w)
                                widgetHandle.setScaleInPixels(false)
                                widgetHandle.onEndInteractionEvent(() => {
                                    this.seedWidgetEndInteraction(w)
                                })
                            })
                        })
                    }
                }
                if (layersShown.value.includes('Constraints')) {
                    this.initializeConstraintColormap(actor)
                    const existingWidgets = planeWidgets.value[label]
                    if (existingWidgets) {
                        Object.values(existingWidgets).forEach((ws) => {
                            Object.values(ws).forEach((w) => {
                                const widgetHandle = wm.addWidget(w)
                                this.stylePlaneWidget(widgetHandle)
                                widgetHandle.onEndInteractionEvent(() => {
                                    this.planeWidgetEndInteraction(w)
                                })
                            })
                        })
                    }
                }
            })
        })
        if (layersShown.value.includes('Landmarks')) {
            this.landmarkInfoUpdated(landmarkInfo.value)
        }
        if (layersShown.value.includes('Constraints')) {
            this.constraintInfoUpdated(constraintInfo.value)
        }
    },
    initializeConstraintColormap(actor) {
        const mapper = actor.getMapper()
        if (!mapper.setLookupTable) return undefined

        const ctfun = vtkColorTransferFunction.newInstance();
        let defaultColor = [255, 255, 255]
        if (actor.getProperty() && actor.getProperty().getColor) {
            defaultColor = actor.getProperty().getColor()
        }
        ctfun.addRGBPoint(1, ...defaultColor); // 0: default color has not been excluded
        ctfun.addRGBPoint(0, 0.5, 0.5, 0.5); // 1: gray has been excluded
        ctfun.setMappingRange(0, 1)
        ctfun.updateRange()

        mapper.setLookupTable(ctfun)
        mapper.setColorByArrayName('color')

        const inputData = mapper.getInputData()
        const allPoints = inputData.getPoints()
        const colorArray = vtkDataArray.newInstance({
            name: 'color',
            values: Array.from(
                { length: allPoints.getNumberOfPoints() }, () => 1
            )
        })
        inputData.getPointData().addArray(colorArray)
    },

    // ---------------------
    // Getters
    // ---------------------
    getWidgetManager(label) {
        return this.vtk.widgetManagers[label]
    },
    getManipulator(label, domain) {
        if (!manipulators.value[label]) manipulators.value[label] = {}
        return manipulators.value[label][domain]
    },
    getDataKDTree(label, domain, cData) {
        if (!dataKDTrees.value[label]) dataKDTrees.value[label] = {}
        if (!dataKDTrees.value[label][domain]) {
            const { points } = cData.data.field
            const scalarPoints = points.map((p, i) => ({ x: p[0], y: p[1], z: p[2], i }))
            dataKDTrees.value[label][domain] = new kdTree(scalarPoints, distance, ['x', 'y', 'z', 'i']);
        }
        return dataKDTrees.value[label][domain]
    },
    getShapeKDTree(label, domain, shapeData) {
        if (!shapeKDTrees.value[label]) shapeKDTrees.value[label] = {}
        if (!shapeKDTrees.value[label][domain]) {
            const pointData = Array.prototype.slice.call(shapeData.getPoints().getData())
            const allPoints = Array.from({ length: pointData.length / 3 }, () => pointData.splice(0, 3));
            const treePoints = allPoints.map((p) => ({ x: p[0], y: p[1], z: p[2] }))
            shapeKDTrees.value[label][domain] = new kdTree(
                treePoints,
                distance,
                ['x', 'y', 'z']
            )
        }
        return shapeKDTrees.value[label][domain]
    },
    getSeedWidget(label, domain, lInfo) {
        if (!seedWidgets.value[label]) seedWidgets.value[label] = {}
        if (!seedWidgets.value[label][domain]) seedWidgets.value[label][domain] = {}
        if (!seedWidgets.value[label][domain][lInfo.id]) {
            this.createSeedWidget(label, domain, lInfo)
        }
        return seedWidgets.value[label][domain][lInfo.id]
    },
    getPlaneWidget(label, domain, cInfo) {
        if (!planeWidgets.value[label]) planeWidgets.value[label] = {}
        if (!planeWidgets.value[label][domain]) planeWidgets.value[label][domain] = {}
        if (!planeWidgets.value[label][domain][cInfo.id]) {
            this.createPlaneWidget(label, domain, cInfo)
        }
        return planeWidgets.value[label][domain][cInfo.id]
    },
    getPaintWidget(label, domain, cInfo, inputData) {
        if (!paintWidgets.value[label]) paintWidgets.value[label] = {}
        if (!paintWidgets.value[label][domain]) paintWidgets.value[label][domain] = {}
        // always create new paint widget
        this.createPaintWidget(label, domain, cInfo, inputData)
        return paintWidgets.value[label][domain][cInfo.id]
    },

    // ---------------------
    // Widget creation
    // ---------------------
    createSeedWidget(label, domain, lInfo) {
        const renderer = this.vtk.renderers[label]
        const manipulator = this.getManipulator(label, domain)
        const widgetManager = this.getWidgetManager(label)
        if (renderer && manipulator) {
            const widget = vtkSeedWidget.newInstance()
            const widgetHandle = widgetManager.addWidget(widget)
            widget.setManipulator(manipulator)
            widgetHandle.setScaleInPixels(false)
            widgetHandle.onEndInteractionEvent(() => {
                this.seedWidgetEndInteraction(widget)
            })
            seedWidgets.value[label][domain][lInfo.id] = widget
        }
    },
    createPlaneWidget(label, domain, cInfo) {
        const renderer = this.vtk.renderers[label]
        const manipulator = this.getManipulator(label, domain)
        const widgetManager = this.getWidgetManager(label)
        if (renderer && manipulator) {
            const pickList = manipulator.getPicker().getPickList()
            if (pickList.length > 0) {
                const actor = pickList[0]
                const bounds = actor.getBounds()
                const widget = vtkImplicitPlaneWidget.newInstance()
                widget.placeWidget(bounds)
                widget.setPlaceFactor(2)
                const widgetHandle = widgetManager.addWidget(widget)
                widgetHandle.getRepresentations()[0].setLabels({
                    'subject': label,
                    'domain': domain
                })
                this.stylePlaneWidget(widgetHandle)
                widgetHandle.onEndInteractionEvent(() => {
                    this.planeWidgetEndInteraction(widget)
                })
                planeWidgets.value[label][domain][cInfo.id] = widget
            }
        }
    },
    createPaintWidget(label, domain, cInfo, inputData) {
        const widgetManager = this.getWidgetManager(label)
        const manipulator = this.getManipulator(label, domain)
        if (manipulator) {
            const widget = vtkPaintWidget.newInstance({ manipulator });
            const widgetHandle = widgetManager.addWidget(widget)
            paintWidgets.value[label][domain][cInfo.id] = widget
            widgetHandle.onEndInteractionEvent(() => {
                this.paintWidgetEndInteraction(widget, inputData)
            })
        }
    },
    stylePlaneWidget(widgetHandle) {
        widgetHandle.setHandleSizeRatio(0.08)
        widgetHandle.setAxisScale(0.25)
        widgetHandle.setRepresentationStyle({
            static: {
                outline: {
                    opacity: 0
                }
            }
        })
    },

    // ---------------------
    // Widget interaction events
    // ---------------------

    seedWidgetEndInteraction(widget) {
        Object.entries(seedWidgets.value).forEach(([label, subjectWidgets]) => {
            Object.entries(subjectWidgets).forEach(([domain, shapeWidgets]) => {
                Object.entries(shapeWidgets).forEach(([id, w]) => {
                    if (widget === w) {
                        const lInfo = { domain, id }
                        const wm = this.getWidgetManager(label)
                        // When widget moved, update value in allSetLandmarks
                        const landmarkCoord = widget.getWidgetState().getMoveHandle().getOrigin()
                        if (landmarkCoord) {
                            wm.releaseFocus(widget);
                            const previousLocation = getLandmarkLocation({ name: label }, lInfo, landmarkCoord)
                            if (!previousLocation || previousLocation.some((v, i) => landmarkCoord[i] != v)) {
                                setLandmarkLocation({ name: label }, lInfo, landmarkCoord)
                                // reassign store var for listeners
                                allSetLandmarks.value = Object.assign({}, allSetLandmarks.value)
                                reassignLandmarkNumSetValues()
                                currentLandmarkPlacement.value = undefined;
                            }
                        }

                    }
                })
            })
        })
    },
    planeWidgetEndInteraction(widget) {
        Object.entries(planeWidgets.value).forEach(([label, subjectWidgets]) => {
            Object.entries(subjectWidgets).forEach(([domain, shapeWidgets]) => {
                Object.entries(shapeWidgets).forEach(([id, w]) => {
                    if (widget === w) {
                        const cInfo = { domain, id }
                        // When widget moved, update value in allSetConstraints
                        const widgetState = widget.getWidgetState()
                        setConstraintLocation({ name: label }, cInfo, {
                            type: 'plane',
                            data: {
                                origin: widgetState.getOrigin(),
                                normal: widgetState.getNormal(),
                            }
                        })
                        this.updateConstraintColors()
                    }
                })
            })
        })
    },
    paintWidgetEndInteraction(widget, inputData) {
        Object.entries(paintWidgets.value).forEach(([label, subjectWidgets]) => {
            Object.entries(subjectWidgets).forEach(([domain, shapeWidgets]) => {
                Object.entries(shapeWidgets).forEach(([id, w]) => {
                    if (widget === w) {
                        const cInfo = { domain, id }
                        const allPoints = inputData.getPoints()
                        const tree = this.getShapeKDTree(label, domain, inputData)
                        let cData = getConstraintLocation({ name: label }, cInfo)
                        if (!cData) {
                            const numPoints = allPoints.getNumberOfPoints()
                            const points = Array.from({ length: numPoints }).map((v, i) => allPoints.getPoint(i))
                            cData = {
                                type: 'paint',
                                data: {
                                    field: {
                                        points,
                                        scalars: Array.from({ length: numPoints }).fill(1),
                                    }
                                }
                            }
                        }
                        let paintedPoints = []
                        widget.getWidgetState().getTrailList().forEach((state) => {
                            const currentPoint = state.getOrigin()
                            if (currentPoint) {
                                paintedPoints = [
                                    ...paintedPoints,
                                    ...tree.nearest(
                                        { x: currentPoint[0], y: currentPoint[1], z: currentPoint[2] },
                                        allPoints.getNumberOfPoints(),
                                        constraintPaintRadius.value * 2
                                    )
                                ]
                            }
                        })
                        paintedPoints.forEach(([{ x, y, z },]) => {
                            const pointIndex = cData.data.field.points.findIndex(
                                (p) => p[0] === x && p[1] === y && p[2] === z
                            )
                            if (pointIndex >= 0 && pointIndex < cData.data.field.scalars.length) {
                                cData.data.field.scalars[pointIndex] = constraintPaintExclusion.value ? 0 : 1
                            }
                        })
                        setConstraintLocation({ name: label }, cInfo, cData)
                        this.updateConstraintColors()
                    }
                })
            })
        })
    },

    // ---------------------
    // Update widget states
    // ---------------------
    landmarkInfoUpdated(newInfo) {
        const validWidgets = []
        Object.entries(manipulators.value).forEach(([label, records]) => {
            Object.entries(records).forEach(([domain,]) => {
                newInfo.filter((lInfo) => lInfo.domain === domain).forEach((lInfo) => {
                    const widget = this.getSeedWidget(label, domain, lInfo)
                    const handle = widget.getWidgetState().getMoveHandle();
                    validWidgets.push(widget)

                    const location = getLandmarkLocation({ name: label }, lInfo)
                    if (location && (
                        !handle.getOrigin() ||
                        handle.getOrigin().some((v, i) => v !== location[i])
                    )) {
                        handle.setOrigin(location)
                    }
                    if (handle.getColor3().some((v, i) => v !== lInfo.color[i])) {
                        handle.setColor3(...lInfo.color);
                    }
                    if (handle.getScale1() != landmarkSize.value) {
                        handle.setScale1(landmarkSize.value);
                    }
                })
            })
        })
        seedWidgets.value = Object.fromEntries(
            Object.entries(seedWidgets.value).map(([label, labelRecords]) => {
                return [label, Object.fromEntries(
                    Object.entries(labelRecords).map(([domain, shapeRecords]) => {
                        return [domain, Object.fromEntries(
                            Object.entries(shapeRecords).map(([id, seedWidget]) => {
                                if (!validWidgets.includes(seedWidget)) {
                                    this.getWidgetManager(label).removeWidget(seedWidget)
                                    return [id, undefined]
                                }
                                return [id, seedWidget]
                            })
                        )]
                    })
                )]
            })
        )
        this.render()
    },
    landmarkSizeUpdated() {
        Object.values(seedWidgets.value).forEach((subjectWidgets) => {
            Object.values(subjectWidgets).forEach((shapeWidgets) => {
                Object.values(shapeWidgets).forEach((widget) => {
                    const handle = widget.getWidgetState().getMoveHandle();
                    if (handle.getScale1() != landmarkSize.value) {
                        handle.setScale1(landmarkSize.value);
                    }
                })
            })
        })
        this.render()
    },
    currentLandmarkPlacementUpdated(newPlacement) {
        if (newPlacement) {
            const label = newPlacement.subjectName
            const domain = newPlacement.domain
            const id = newPlacement.widgetID
            const widgetManager = this.getWidgetManager(label)
            const manipulator = this.getManipulator(label, domain)
            if (manipulator) {
                const widget = this.getSeedWidget(label, domain, { id, domain })
                const pickList = manipulator.getPicker().getPickList()
                if (pickList.length > 0) {
                    const actor = pickList[0]
                    widget.placeWidget(actor.getBounds());
                    widgetManager.grabFocus(widget)
                }
            }
        }
    },
    constraintInfoUpdated(newInfo) {
        const validWidgets = []
        Object.entries(manipulators.value).forEach(([label, records]) => {
            Object.entries(records).forEach(([domain,]) => {
                newInfo.filter((cInfo) => cInfo.domain === domain).forEach((cInfo) => {
                    if (cInfo.type === 'plane') {
                        const widget = this.getPlaneWidget(label, domain, cInfo)
                        const widgetState = widget.getWidgetState()
                        const cData = getConstraintLocation({ name: label }, cInfo)
                        validWidgets.push(widget)

                        let origin = cData?.data?.origin
                        if (origin && widgetState.getOrigin().some((v, i) => v != origin[i])) {
                            widgetState.setOrigin(origin)
                        }
                        let normal = cData?.data?.normal
                        if (normal && widgetState.getNormal().some((v, i) => v != normal[i])) {
                            widgetState.setNormal(normal)
                        }

                        widget.setVisibility(origin && normal && constraintsShown.value.includes(cInfo.id))
                    }
                })
            })
        })
        planeWidgets.value = Object.fromEntries(
            Object.entries(planeWidgets.value).map(([label, labelRecords]) => {
                return [label, Object.fromEntries(
                    Object.entries(labelRecords).map(([domain, shapeRecords]) => {
                        return [domain, Object.fromEntries(
                            Object.entries(shapeRecords).map(([id, planeWidget]) => {
                                if (!validWidgets.includes(planeWidget)) {
                                    this.getWidgetManager(label).removeWidget(planeWidget)
                                    return [id, undefined]
                                }
                                return [id, planeWidget]
                            })
                        )]
                    })
                )]
            })
        )
        this.updateConstraintColors()
        this.render()
    },
    constraintsShownUpdated() {
        this.constraintInfoUpdated(constraintInfo.value)
    },
    currentConstraintPlacementUpdated(newPlacement) {
        if (newPlacement) {
            const label = newPlacement.subjectName
            const domain = newPlacement.domain
            const id = newPlacement.widgetID
            const widgetManager = this.getWidgetManager(label)
            const manipulator = this.getManipulator(label, domain)
            const cInfo = constraintInfo.value.find((c) =>
                c.id == id && c.domain == domain
            )
            if (manipulator) {
                const pickList = manipulator.getPicker().getPickList()
                if (pickList.length > 0) {
                    const actor = pickList[0]
                    if (cInfo?.type === 'plane') {
                        const bounds = actor.getBounds()
                        const origin = [
                            (bounds[0] + bounds[1]) / 2,
                            (bounds[2] + bounds[3]) / 2,
                            (bounds[4] + bounds[5]) / 2,
                        ]
                        const normal = [0, 0, 1]
                        setConstraintLocation(
                            { name: label },
                            { id, domain },
                            { type: 'plane', data: { origin, normal } },
                        )
                        currentConstraintPlacement.value = undefined
                        this.constraintInfoUpdated(constraintInfo.value)
                    } else if (manipulator && cInfo?.type === 'paint') {
                        const mapper = actor.getMapper()
                        const inputData = mapper.getInputData()
                        const widget = this.getPaintWidget(label, domain, cInfo, inputData)
                        widget.setRadius(constraintPaintRadius.value)
                        widget.getWidgetState().getHandle().setVisible(true)
                        widgetManager.grabFocus(widget);
                        widget.getWidgetState().setActive(true)
                    }
                }
            }
        } else {
            Object.entries(paintWidgets.value).forEach(([label, subjectRecords]) => {
                const widgetManager = this.getWidgetManager(label)
                if (widgetManager) {
                    Object.values(subjectRecords).forEach((shapeRecords) => {
                        Object.values(shapeRecords).forEach((widget) => {
                            widget.getWidgetState().getHandle().setVisible(false)
                            widget.getWidgetState().setActive(false)
                            widgetManager.releaseFocus(widget)
                        })
                    })
                }
            })
        }
    },
    updateConstraintColors() {
        Object.entries(manipulators.value).forEach(([label, shapeManipulators]) => {
            if (!allSetConstraints.value[label]) return
            Object.entries(shapeManipulators).forEach(([domain, manipulator]) => {
                const pickList = manipulator.getPicker().getPickList()
                if (!pickList.length || !allSetConstraints.value[label][domain]) return
                const actor = pickList[0]
                const mapper = actor.getMapper()
                const inputData = mapper.getInputData()
                const allPoints = inputData.getPoints()
                const allPointColors = inputData.getPointData().getArrayByName('color')
                allPointColors.setData(
                    new Uint8Array(allPoints.getNumberOfPoints()).fill(1)
                )
                Object.entries(allSetConstraints.value[label][domain]).forEach(
                    ([id, cData]) => {
                        if (constraintsShown.value.includes(parseInt(id))) {
                            if (cData?.type === 'plane') {
                                const { normal, origin } = cData.data
                                let dot = (a, b) => a.map((x, i) => a[i] * b[i]).reduce((m, n) => m + n);
                                for (let i = 0; i < allPoints.getNumberOfPoints(); i++) {
                                    const point = allPoints.getPoint(i)
                                    const pointColor = allPointColors.getValue(i)
                                    if (pointColor == 1) {
                                        // has not been excluded yet, check for exclusion
                                        const dotProduct = dot(normal, [
                                            origin[0] - point[0],
                                            origin[1] - point[1],
                                            origin[2] - point[2],
                                        ])
                                        if (dotProduct <= 0) {
                                            // negative dotProduct means point is below plane
                                            allPointColors.setValue(i, 0)
                                        }
                                    }
                                }
                            } else if (cData?.type === 'paint') {
                                const { scalars } = cData.data.field
                                const tree = this.getDataKDTree(label, domain, cData)
                                if (scalars.length === allPoints.getNumberOfPoints()) {
                                    for (let i = 0; i < scalars.length; i++) {
                                        const pointColor = allPointColors.getValue(i)
                                        if (pointColor == 1) {
                                            // has not been excluded yet, check for exclusion
                                            const currentPoint = allPoints.getPoint(i)
                                            const currentPointObj = {
                                                x: currentPoint[0],
                                                y: currentPoint[1],
                                                z: currentPoint[2],
                                            }
                                            const nearests = tree.nearest(currentPointObj, 1)
                                            if (nearests.length) {
                                                const [nearest,] = nearests[0]
                                                if (nearest.i && nearest.i >= 0 && nearest.i < cData.data.field.scalars.length) {
                                                    allPointColors.setValue(i, cData.data.field.scalars[nearest.i])
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                )
                allPointColors.modified()
                inputData.modified()
            })
        })
        this.render()
    },

    // ---------------------
    // Listeners
    // ---------------------
    watchWidgetStates() {
        watch(landmarkInfo, _.debounce(this.landmarkInfoUpdated, 1000))
        watch(landmarkSize, _.debounce(this.landmarkSizeUpdated, 1000))
        watch(currentLandmarkPlacement, _.debounce(this.currentLandmarkPlacementUpdated, 1000))
        watch(constraintInfo, _.debounce(this.constraintInfoUpdated, 1000))
        watch(constraintsShown, _.debounce(this.constraintsShownUpdated, 1000))
        watch(currentConstraintPlacement, _.debounce(this.currentConstraintPlacementUpdated, 1000))
        watch(allSetConstraints, _.debounce(this.updateConstraintColors, 1000))
    },
}
