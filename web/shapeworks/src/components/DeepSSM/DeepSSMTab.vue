<script lang="ts">
import { allSubjectsForDataset } from '@/store';
import { defineComponent, ref } from '@vue/composition-api';


export default defineComponent({
    components: {
        
    },
    setup() {
        const openTab = ref<number>(0);

        // Split
        const splitData = {
            testSplit: ref<number>(20),
            validationSplit: ref<number>(20),
        }

        // Augmentation
        const augmentationData = {
            numSamples: ref<number>(3),
            numDimensions: ref<number>(3),
            variablity: ref<number>(95),
        }
        // Training
        const trainingData = {
            epochs: ref<number>(2),
            learningRate: ref<number>(0.001),
            batchSize: ref<number>(8),
            decayLearningRate: ref<boolean>(true),
            fineTuning: ref<boolean>(true),
            ftEpochs: ref<number>(2),
            ftLearningRate: ref<number>(0.001),
        }

        enum Sampler {
            Gaussian = "Gaussian",
            Mixture = "Mixture",
            KDE = "KDE",
        }

        const samplerType = ref<Sampler>(Sampler.Gaussian);

        console.log(allSubjectsForDataset);

        return {
            openTab,
            splitData,
            augmentationData,
            trainingData,
            Sampler,
            samplerType,
        }
    },
})
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
                    Split
                </v-expansion-panel-header>
                <v-expansion-panel-content>
                    <v-text-field v-model="splitData.testSplit" type="number" label="Test Split" suffix="%" />
                    <v-text-field v-model="splitData.validationSplit" type="number" label="Validation Split" suffix="%" />
                </v-expansion-panel-content>
            </v-expansion-panel>
            <v-expansion-panel>
                <v-expansion-panel-header>
                    Augmentation
                </v-expansion-panel-header>
                <v-expansion-panel-content>
                    <v-text-field v-model="augmentationData.numSamples" type="number" label="Number of Samples" min="1" />
                    <v-text-field v-model="augmentationData.numDimensions" type="number" label="Number of PCA Dimensions" min="1" />
                    <v-text-field v-model="augmentationData.variablity" type="number" label="Percent Variablity Preserved" min="0" max="100" suffix="%" />

                    <v-select 
                        :items="Object.values(Sampler)"
                        v-model="samplerType"
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
                    <v-text-field v-model="trainingData.epochs" type="number" label="Epochs" min="0" />
                    <v-text-field v-model="trainingData.learningRate" type="number" label="Learning Rate" min="0" />
                    <v-text-field v-model="trainingData.batchSize" type="number" label="Batch Size" min="1" />

                    <v-checkbox v-model="trainingData.decayLearningRate" label="Decay Learning Rate"></v-checkbox>

                    <v-checkbox v-model="trainingData.fineTuning" label="Fine Tuning"></v-checkbox>

                    <v-text-field v-model="trainingData.ftEpochs" type="number" label="Fine Tuning Epochs" min="1" />
                    <v-text-field v-model="trainingData.ftLearningRate" type="number" label="Fine Tuning Learning Rate" min="0" />
                    
                    <!-- TODO: needs sub-panel for training output -->
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
</style>
