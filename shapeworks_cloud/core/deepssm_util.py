from enum import Enum


class DeepSSMFileType(Enum):
    ID = 1
    IMAGE = 2
    PARTICLE = 3


class DeepSSMSplitType(Enum):
    TRAIN = 1
    TEST = 2


def get_list(file_type: DeepSSMFileType, split_type: DeepSSMSplitType):
    """
    Get a list of subjects, ids, filenames, or particle filenames based on the given file type and split type.

    Args:
        file_type (DeepSSMFileType): The type of file to retrieve the list for.
        split_type (DeepSSMSplitType): The type of split to determine the range of subjects to include in the list.

    Returns:
        list: A list of subjects, ids, filenames, or particle filenames based on the given file type and split type.
    """
    # get subjects
    # make a list of ids (one for each subject)
    # shuffle the id list
    # make a list of strings
    # get start and end indicies based on split values and type
    # if the spit type is TEST, use the second half of the list (start = end, end = subjects.length)
    # from start to end,
    # if the file type is ID, add the id to the list
    # if the file type is IMAGE, add the suject filenames to the list
    # if the file type is PARTICLE, add the first particle filename to the list
    # return the list
    return ['subject1', 'subject2', 'subject3']
