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
DATASET_ID = os.environ.get('modal.state.slyDatasetId')

if DATASET_ID is not None:
  DATASET_ID = int(DATASET_ID)

@my_app.callback("interactive_coexistence_matrix")
@sly.timeit
def interactive_coexistence_matrix(api: sly.Api, task_id, context, state, app_logger):
    classes = api.project.get_meta(PROJECT_ID)['classes']

    if DATASET_ID is not None:
        dataset_ids = [DATASET_ID]
    else:
        datasets_list = api.dataset.get_list(PROJECT_ID)
        dataset_ids = [d.id for d in datasets_list]

    coexist_table = {}

    for cls1 in classes:
      for cls2 in classes:
        coexist_table[f"{cls1['title']}-{cls2['title']}"] = []

    for dataset_id in dataset_ids:
        anns = api.annotation.get_list(dataset_id)

        for ann_info in anns:
            image_id = ann_info.image_id
            classes_on_img = set([label['classTitle'] for label in ann_info.annotation['objects']])

            for cls_name1 in classes_on_img:
                for cls_name2 in classes_on_img:
                    coexist_table[f"{cls_name1}-{cls_name2}"].append(image_id)

    my_app.stop()


def main():
    sly.logger.info("Script arguments", extra={
        "PROJECT_ID": PROJECT_ID
    })

    my_app.run(initial_events=[{"command": "interactive_coexistence_matrix"}])


if __name__ == "__main__":
    sly.main_wrapper("main", main)