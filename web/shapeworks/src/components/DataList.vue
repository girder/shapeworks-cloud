<script lang="ts">
import { groupBy, shortDateString, shortFileName } from '../helper';
import { getDataObjectsForSubject } from '@/api/rest';
import { onMounted, ref, watch } from 'vue';
import { Subject } from '@/types';
import { getSubjectsForDataset } from '@/api/rest'
import {
    selectedDataset,
    allSubjectsForDataset,
    allDataObjectsInDataset,
    anatomies,
    selectedAnatomies,
    selectedDataObjects,
    loadingState,
    loadReconstructedSamplesForProject,
imageViewMode,
} from '@/store';


export default {
    props: {
        dataset: {
            type: Number,
            required: true,
        },
        autoSelectAll: {
            type: Boolean,
            default: false,
        },
        autoSelectOne: {
            type: Boolean,
            default: false,
        }
    },
    setup(props) {
        const selectedSubjects = ref<number[]>([])
        const headers =  [
            {text: 'ID', value: 'id'},
            {text: 'Anatomy', value: 'anatomy_type'},
            {text: 'Type', value: 'type'},
            {text: 'File Name', value: 'file', cellClass: 'file-column'},
        ];

        async function fetchData(datasetId: number) {
            loadingState.value = true;
            allSubjectsForDataset.value = (await getSubjectsForDataset(datasetId)).sort((a, b) => {
                if(a.created < b.created) return 1;
                if(a.created > b.created) return -1;
                return 0;
            });
            allDataObjectsInDataset.value =  (await Promise.all(
                allSubjectsForDataset.value.map(
                    async (subject: Subject) => (await getDataObjectsForSubject(subject.id)).map(
                        (dataObj) => {
                            let assignments = {'uid': `${dataObj.type}_${dataObj.id}`}
                            return Object.assign(dataObj, assignments)
                        }
                    )
                )
            )).flat()
            loadReconstructedSamplesForProject('', 0)
            anatomies.value = Object.keys(
                {
                    ...groupBy(allDataObjectsInDataset.value, 'anatomy_type'),
                    ...groupBy(allDataObjectsInDataset.value, 'modality'),
                }
            ).filter((key) => key !== 'undefined')
            selectedAnatomies.value = anatomies.value;
            if(allSubjectsForDataset.value.length > 0) {
                const subjectIds = allSubjectsForDataset.value.map(
                    (subject: Subject) => subject.id
                )
                if(props.autoSelectAll){
                    selectedSubjects.value = subjectIds
                }
                if(props.autoSelectOne && allSubjectsForDataset.value.length > 0) {
                    selectedSubjects.value = [subjectIds[0]]
                }
            }
            loadingState.value = false;
        }

        function updateSelectedObjects() {
            selectedDataObjects.value = allDataObjectsInDataset.value.filter(
                (dataObject) => {
                    return (
                        (
                            !selectedAnatomies.value.length ||
                            selectedAnatomies.value.includes(dataObject.anatomy_type) ||
                            selectedAnatomies.value.includes(dataObject.modality)
                        ) && selectedSubjects.value.includes(dataObject.subject)
                    )
                }
            )
        }

        function selectedObjectsUpdated() {
            const uniqueAnatomies = [...new Set(selectedDataObjects.value.map(item => {
                // if the item is an image, it will have "modality" instead of anatomy_type
                if (item.modality && imageViewMode.value) {
                    return item.modality
                }
                return item.anatomy_type
            }))].filter((anatomy) => anatomy !== undefined);
            const uniqueSubjects = [...new Set(selectedDataObjects.value.map(item => item.subject))]
            if (JSON.stringify(uniqueAnatomies) !== JSON.stringify(selectedAnatomies.value)) {
                selectedAnatomies.value = uniqueAnatomies
            }
            if (JSON.stringify(uniqueSubjects) !== JSON.stringify(selectedSubjects.value)) {
                selectedSubjects.value = uniqueSubjects
            }
        }

        onMounted(async () => {
            if(!selectedDataset.value) {
                await fetchData(props.dataset)
            } else {
                await fetchData(selectedDataset.value.id)
            }
        })

        watch(selectedAnatomies, updateSelectedObjects)
        watch(selectedSubjects, updateSelectedObjects)
        watch(selectedDataObjects, selectedObjectsUpdated)

        return {
            anatomies,
            selectedAnatomies,
            allSubjectsForDataset,
            selectedSubjects,
            headers,
            allDataObjectsInDataset,
            selectedDataObjects,
            shortFileName,
            shortDateString,
        }
    }
}
</script>

<template>
    <div style="width:100%">
        <v-list dense shaped>
            <v-subheader>ANATOMIES</v-subheader>
            <v-list-item-group>
                <!-- Anatomy list. Filter out any anatomies that match the image modality label (ex: anatomy_mri) -->
                <v-list-item
                    v-for="anatomy_type in anatomies.filter((anatomy) => anatomy !== allDataObjectsInDataset[0].modality)"
                    :key="anatomy_type"
                >
                        <v-checkbox
                        color="primary"
                        v-model="selectedAnatomies"
                        :value="anatomy_type"
                    ></v-checkbox>
                    <v-list-item-title>
                        {{ anatomy_type }}
                    </v-list-item-title>
                </v-list-item>
            </v-list-item-group>
            <v-subheader>SUBJECTS</v-subheader>
            <v-list-item-group>
                <v-list-group
                    v-for="subject in allSubjectsForDataset"
                    :key="subject.id"
                    v-model="subject.showDetails"
                >
                    <template v-slot:activator>
                        <v-checkbox
                            color="primary"
                            v-model="selectedSubjects"
                            :value="subject.id"
                            @click.native="$event.stopPropagation()"
                        ></v-checkbox>
                        <v-tooltip bottom>
                            <template v-slot:activator="{ on, attrs }">
                                <v-list-item-title
                                    v-bind="attrs"
                                    v-on="on"
                                >
                                    Subject: {{ subject.name }}
                                </v-list-item-title>
                            </template>
                            <span>
                                ID: {{ subject.id }} |
                                Created: {{ shortDateString(subject.created) }} |
                                Modified: {{ shortDateString(subject.modified) }}
                            </span>
                        </v-tooltip>
                    </template>

                    <div class="pa-3" v-if="subject.groups && Object.keys(subject.groups).length > 0">
                        Subject Groups
                        {{
                            JSON.stringify(subject.groups)
                            .replace(/"/g, '').replace(/:/g, ': ').replace(/,/g, ', ')
                        }}
                    </div>

                    <v-data-table
                        :headers="headers"
                        :items="allDataObjectsInDataset.filter((obj) => obj.subject === subject.id)"
                        item-key="uid"
                        disable-pagination
                        hide-default-footer
                        dense
                        width="100%"
                    >
                        <!-- eslint-disable-next-line -->
                        <template v-slot:item.file="{ item }">
                            <span>{{ shortFileName(item.file) }}</span>
                        </template>
                    </v-data-table>
                </v-list-group>
            </v-list-item-group>
        </v-list>
    </div>
</template>

<style>
.file-column {
    width: 100px!important;
    overflow: hidden;
    text-overflow: ellipsis;
}
.v-data-table td {
    border-bottom: none !important;
}
.v-row-group__header {
    background: none !important;
    border-top: 1px solid white !important;
}
</style>
