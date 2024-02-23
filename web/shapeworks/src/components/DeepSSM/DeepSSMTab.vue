<script lang="ts">
/* eslint-disable no-unused-vars */
import { spawnJob } from '@/store';
import { Ref, ref } from 'vue';


export default {
    components: {
        
    },
    setup() {
        enum Sampler {
            Gaussian = "Gaussian",
            Mixture = "Mixture",
            KDE = "KDE",
        }

        enum LossFunction {
            MSE = "MSE",
            Focal = "Focal",
        }

        const openTab = ref<number>(0);

        const prepData = {
            testingSplit: ref<number>(20),
            validationSplit: ref<number>(20),
            percentVariability: ref<number>(95),
            imageSpacing: ref<{x: number, y: number, z: number}>({x: 1, y: 1, z: 1})
        }
        
        // Augmentation
        const augmentationData = {
            numSamples: ref<number>(300),
            samplerType : ref<Sampler>(Sampler.Gaussian),
        }
        
        // Training
        const trainingData = {
            lossFunction: ref<LossFunction>(LossFunction.MSE),
            epochs: ref<number>(100),
            learningRate: ref<number>(0.001),
            batchSize: ref<number>(8),
            decayLearningRate: ref<boolean>(true),
            fineTuning: ref<boolean>(true),
            ftEpochs: ref<number>(100),
            ftLearningRate: ref<number>(0.001),
        }

        /**
         * Converts an object of reactive properties to a plain object for use in api formData fields.
         * 
         * @param {Object} object - The object containing reactive properties.
         * @returns {Object} - The plain object with the same key-value pairs as the input object.
         */
        function getFormData(object: {[key: string]: Ref<any>}) {
            return (
                Object.entries(object)
                    .map(([key, value]) => [key, value.value])
                    .reduce((obj, [key, value]) => {
                        obj[key] = value;
                        return obj;
                    }, {} as any)
            )
        }

        async function submitDeepSSMJob() {
            const prepFormData = getFormData(prepData);
            const augFormData = getFormData(augmentationData);
            const trainFormData = getFormData(trainingData);
            const formData = {
                ...prepFormData,
                ...augFormData,
                ...trainFormData,
            }

            console.log(formData);
            return await spawnJob("deepssm_run", formData);
        }

        return {
            openTab,
            prepData,
            augmentationData,
            trainingData,
            Sampler,
            LossFunction,
            submitDeepSSMJob,
        }
    },
}
</script>

<template>
    <div class="pa-3">
        DeepSSM Controls
        <v-tooltip bottom>
            <template v-slot:activator="{ on, attrs }">
                <v-icon
                    v-bind="attrs"
                    v-on="on"
                >
                mdi-information
                </v-icon>
            </template>
            <span>
               <v-subheader></v-subheader>
            </span>
        </v-tooltip>
        <v-expansion-panels v-model="openTab">
            <v-expansion-panel>
                <v-expansion-panel-header>
                    Prep
                </v-expansion-panel-header>
                <v-expansion-panel-content>
                    <v-text-field v-model="prepData.testingSplit" type="number" label="Test Split" suffix="%" />
                    <v-text-field v-model="prepData.validationSplit" type="number" label="Validation Split" suffix="%" />
                    <v-text-field v-model="prepData.percentVariability" type="number" label="Percent Variablity Preserved" min="0" max="100" suffix="%" />
                    <div class="image-spacing">
                        <v-label class="spacing-label">Image Spacing</v-label>
                        <v-text-field class="spacing-input" v-model="prepData.imageSpacing.value.x" type="number" label="X" />
                        <v-text-field class="spacing-input" v-model="prepData.imageSpacing.value.y" type="number" label="Y" />
                        <v-text-field class="spacing-input" v-model="prepData.imageSpacing.value.z" type="number" label="Z" />
                    </div>
                </v-expansion-panel-content>
            </v-expansion-panel>
            <v-expansion-panel>
                <v-expansion-panel-header>
                    Augmentation
                </v-expansion-panel-header>
                <v-expansion-panel-content>
                    <v-text-field v-model="augmentationData.numSamples.value" type="number" label="Number of Samples" min="1" />

                    <v-select 
                        :items="Object.values(Sampler)"
                        v-model="augmentationData.samplerType"
                        label="Sampler Type"
                    />
                    <!-- needs sub-panel for data -->
                </v-expansion-panel-content>
            </v-expansion-panel>
            <v-expansion-panel>
                <v-expansion-panel-header>
                    Training
                </v-expansion-panel-header>
                <v-expansion-panel-content>
                    <v-select 
                        :items="Object.values(LossFunction)"
                        v-model="trainingData.lossFunction"
                        label="Loss Function"
                    />
                    <v-text-field v-model="trainingData.epochs.value" type="number" label="Epochs" min="0" />
                    <v-text-field v-model="trainingData.learningRate.value" type="number" label="Learning Rate" min="0" />
                    <v-text-field v-model="trainingData.batchSize.value" type="number" label="Batch Size" min="1" />

                    <v-checkbox v-model="trainingData.decayLearningRate" label="Decay Learning Rate"></v-checkbox>

                    <v-checkbox v-model="trainingData.fineTuning" label="Fine Tuning"></v-checkbox>

                    <v-text-field v-model="trainingData.ftEpochs.value" :disabled="!trainingData.fineTuning" type="number" label="Fine Tuning Epochs" min="1" />
                    <v-text-field v-model="trainingData.ftLearningRate.value" :disabled="!trainingData.fineTuning" type="number" label="Fine Tuning Learning Rate" min="0" />

                    <!-- TODO: needs sub-panel for training output -->
                    <!-- needs data table with "Original Data" and "Generated Data" options -->
                    <!-- also needs violin plot to compare original and generated data -->
                </v-expansion-panel-content>
            </v-expansion-panel>
            <v-expansion-panel>
                <v-expansion-panel-header>
                    Testing
                </v-expansion-panel-header>
                <v-expansion-panel-content>
                    <!-- Data table for name and average distance -->
                </v-expansion-panel-content>
            </v-expansion-panel>
        </v-expansion-panels>
        <v-btn @click="submitDeepSSMJob">Run DeepSSM tasks</v-btn>
        <!-- <div class="loading-dialog"><v-dialog v-model="currentlyCaching" width="10%">Calculating...  <v-progress-circular indeterminate align-center></v-progress-circular></v-dialog></div> -->
    </div>
</template>

<style>
input::-webkit-outer-spin-button, 
input::-webkit-inner-spin-button {
    -webkit-appearance: none;
    margin: 0;
}

input[type=number] {
    appearance: textfield;
    -moz-appearance: textfield;
}

.spacing-label {
    margin-bottom: 0;
}

.spacing-input {
    margin-bottom: 0;
    width: 6%;
    margin: 0 10px;
}

.image-spacing {
    display: flex;
    flex-direction: row;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0;
}
</style>
