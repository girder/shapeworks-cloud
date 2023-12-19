from enum import Enum
from random import shuffle

from shapeworks_cloud.core import models


class DeepSSMFileType(Enum):
    ID = 1
    IMAGE = 2
    PARTICLE = 3


class DeepSSMSplitType(Enum):
    TRAIN = 1
    TEST = 2


def get_list(
    project, file_type: DeepSSMFileType, split_type: DeepSSMSplitType, testing_split: float
):
    """
    Get a list of subjects, ids, filenames, or particle filenames based on the given file type and split type.

    Args:
        file_type (DeepSSMFileType): The type of file to retrieve the list for.
        split_type (DeepSSMSplitType): The type of split to determine the range of subjects to include in the list.

    Returns:
        list: A list of subjects, ids, filenames, or particle filenames based on the given file type and split type.
    """
    dataset = models.Dataset.objects.get(id=project.dataset.id)
    subjects = list(project.subjects)

    num_subjects = len(list(project.subjects))
    # make a list of ids (shuffled order of indicies)
    ids = list(range(num_subjects))
    shuffle(ids)
    # make a list of strings
    output = []
    # get start and end indicies based on split values and type
    start = 0

    end = round(num_subjects * (100.0 - testing_split) / 100.0)

    # if the spit type is TEST, use the second half of the list (start = end, end = subjects.length)
    if split_type == DeepSSMSplitType.TEST:
        start = end
        end = num_subjects

    # NOTE: SINGLE DOMAIN ASSUMPTION
    #       currently, DeepSSM only supports a single domain
    for i in range(start, end):
        # if the file type is ID, add the id to the list
        if file_type == DeepSSMFileType.ID:
            output.append(ids[i])
        # if the file type is IMAGE, add the suject filenames to the list
        elif file_type == DeepSSMFileType.IMAGE:
            images = dataset.get_contents('image')
            subject = subjects[ids[i]]

            print(subject)

            print(list(filter(lambda x: x.name == subject.name, images)))

            output.append(filter(lambda x: x.name == subject.name, images))
        # if the file type is PARTICLE, add the first particle filename to the list
        elif file_type == DeepSSMFileType.PARTICLE:
            output.append(subjects[ids[i]].particles[0].filename)

    return output
