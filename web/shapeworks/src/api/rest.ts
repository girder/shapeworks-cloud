import { Dataset, Subject } from "@/types";
import { apiClient } from "./auth";

export async function getDatasets(): Promise<Dataset[]>{
    return (await apiClient.get('/datasets')).data.results
}

export async function getDataset(datasetId: string): Promise<Dataset>{
    return (await apiClient.get(`/datasets/${datasetId}`)).data
}

export async function getSubjectsForDataset(datasetId: number): Promise<Subject[]> {
    return (await apiClient.get('/subjects', {
        params: {dataset: datasetId}
    })).data.results
}

export async function getSubject(subjectId: string): Promise<Subject>{
    return (await apiClient.get(`/subjects/${subjectId}`)).data
}
