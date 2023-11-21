import { AnalysisParams, DataObject, Dataset, Project, Subject } from "@/types";
import { apiClient } from "./auth";
import { loadGroomedShapeForObject, loadParticlesForObject } from "@/store";


export async function getDatasets(search: string | undefined): Promise<Dataset[]>{
    const results: Dataset[] = []
    let page = 1
    let response = (await apiClient.get('/datasets', {
        params: { page, search }
    })).data
    results.push(...response.results)
    while(response.next){
        page += 1
        response = (await apiClient.get('/datasets', {
            params: { page, search }
        })).data
        results.push(...response.results)
    }
    return results
}

export async function getDataset(datasetId: number): Promise<Dataset>{
    return (await apiClient.get(`/datasets/${datasetId}`)).data
}

export async function subsetDataset(datasetId: number, formData: Object): Promise<Dataset>{
    return (await apiClient.post(`/datasets/${datasetId}/subset/`, formData)).data
}

export async function setDatasetThumbnail(datasetId: number, encoding: string) {
    return (await apiClient.post(`/datasets/${datasetId}/thumbnail/`, {
        encoding
    })).data
}

export async function setProjectThumbnail(projectId: number, encoding: string) {
    return (await apiClient.post(`/projects/${projectId}/thumbnail/`, {
        encoding
    })).data
}

export async function getSubjectsForDataset(datasetId: number): Promise<Subject[]> {
    return (await apiClient.get('/subjects', {
        params: {dataset: datasetId}
    })).data.results
}

export async function getProjectsForDataset(search: string | undefined, datasetId: number): Promise<Project[]>{
    const results: Project[] = []
    let page = 1
    let response = (await apiClient.get(`/projects`, {
        params: { page, search, dataset: datasetId }
    })).data
    results.push(...response.results)
    while(response.next){
        page += 1
        response = (await apiClient.get(`/projects`, {
            params: { page, search, dataset: datasetId }
        })).data
        results.push(...response.results)
    }
    return results
}

export async function refreshProject(projectId: number){
    return (await apiClient.get(`/projects/${projectId}`)).data
}

export async function getSubject(subjectId: number): Promise<Subject>{
    return (await apiClient.get(`/subjects/${subjectId}`)).data
}

export async function getDataObjectsForSubject(subjectId: number): Promise<DataObject[]> {
    const dataTypes = ['image', 'segmentation', 'mesh']
    return (await Promise.all(dataTypes.map((type) => {
        return apiClient.get(`/${type}${type == 'mesh' ?'es' :'s'}/`, {
            params: {subject: subjectId}
        })
    }))).map((response, index) => {
        return response.data.results.map((result: DataObject) => {
            const type = dataTypes[index]
            if(type !== 'image'){
                // don't await this, let particles and groomed shapes load in after
                loadParticlesForObject(type, result.id)
                loadGroomedShapeForObject(type, result.id)
            }
            return Object.assign(result, {type})
        })
    }).flat(2)
}

export async function getOptimizedParticlesForDataObject(
    type: string, id: number, projectId: number|undefined
){
    return (await apiClient.get('/optimized-particles', {
        params: {[`original_${type}`]: id, project: projectId}
    })).data.results
}

export async function getGroomedShapeForDataObject(
    type: string, id: number, projectId: number|undefined
) {
    const plural = `${type}${type == 'mesh' ?'es' :'s'}`
    return (await apiClient.get(`/groomed-${plural}`, {
        params: {[type]: id, project: projectId}
    })).data.results
}

export async function getReconstructedSamplesForProject(
    type: string, id: number, projectId: number|undefined
){
    return (await apiClient.get(`/reconstructed-samples/`, {
        params: {project: projectId}
    })).data.results
}

export async function createProject(formData: Record<string, any>){
    return (await apiClient.post(`/projects/`, formData))
}

export async function cloneProject(projectId: number){
    return (await apiClient.post(`/projects/${projectId}/clone/`))
}

export async function deleteProject(projectId: number){
    return (await apiClient.delete(`/projects/${projectId}/`))
}

export async function editProject(projectId: number, formData: Record<string, any>){
    return (await apiClient.put(`/projects/${projectId}/`, formData));
}

export async function groomProject(projectId: number, formData: Record<string, any>){
    return (await apiClient.post(`/projects/${projectId}/groom/`, formData))
}

export async function optimizeProject(projectId: number, formData: Record<string, any>){
    return (await apiClient.post(`/projects/${projectId}/optimize/`, formData))
}

export async function analyzeProject(projectId: number, params: AnalysisParams){
    return (await apiClient.post(`/projects/${projectId}/analyze/`, params))
}

export async function deepssmAugmentProject(projectId: number, formData: Record<string, any>) {
    return (await apiClient.post(`/projects/${projectId}/deepssm-augment/`, formData))
}

export async function deepssmTrainProject(projectId: number, formData: Record<string, any>) {
    return (await apiClient.post(`/projects/${projectId}/deepssm-train/`, formData))
}

export async function deepssmTestProject(projectId: number, formData: Record<string, any>) {
    return (await apiClient.post(`/projects/${projectId}/deepssm-test/`, formData))
}

export async function getTaskProgress(taskId: number){
    return (await apiClient.get(`/task-progress/${taskId}`)).data
}

export async function deleteTaskProgress(taskId: number){
    return (await apiClient.delete(`/task-progress/${taskId}`)).data
}

export async function abortTask(taskId: number) {
    return (await apiClient.post(`/task-progress/${taskId}/abort/`)).data
}
