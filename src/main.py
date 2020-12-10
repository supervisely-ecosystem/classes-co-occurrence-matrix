import os
from collections import Counter
from itertools import chain, combinations
from collections import defaultdict
import pandas as pd

import supervisely_lib as sly


my_app = sly.AppService()

TEAM_ID = int(os.environ['context.teamId'])
WORKSPACE_ID = int(os.environ['context.workspaceId'])
PROJECT_ID = int(os.environ['modal.state.slyProjectId'])
DATASET_ID = int(os.environ['modal.state.slyDatasetId'])


@my_app.callback("interactive_coexistence_matrix")
@sly.timeit
def interactive_coexistence_matrix(api: sly.Api, task_id, context, state, app_logger):

    # meta_json = api.project.get_meta(PROJECT_ID)
    # meta = sly.ProjectMeta.from_json(meta_json)
    # if len(meta.obj_classes) == 0:
    #     raise ValueError("No classes in project")


    if DATASET_ID is not None:
        dataset_ids = [DATASET_ID]
    else:
        datasets_list = api.dataset.get_list(PROJECT_ID)
        dataset_ids = [d.id for d in datasets_list]

    for dataset_id in dataset_ids:
        anns = api.annotation.get_list(dataset_id)
        class_names = []
        image_ids = []
        for ann_info in anns:
            class_names.append([label['classTitle'] for label in ann_info.annotation['objects']])
            if ann_info.annotation['objects']['classTitle'] in ann_info:
                image_ids.append(ann_info.image_id)

        # for img_id in image_ids:
        #     if class_names[0][0] in ann_info.annotation['objects']:
        #         print(class_names)

        pairs = Counter(
            chain.from_iterable(combinations(sorted(classes_per_img), 2) for classes_per_img in class_names))

        for classes, pairs_counter in pairs.items():
            ...
            print(classes, pairs_counter, image_ids)

    my_app.stop()


def main():
    sly.logger.info("Script arguments", extra={
        "PROJECT_ID": PROJECT_ID
    })

    my_app.run(initial_events=[{"command": "interactive_coexistence_matrix"}])


if __name__ == "__main__":
    sly.main_wrapper("main", main)