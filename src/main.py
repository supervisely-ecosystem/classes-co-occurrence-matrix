import os
import pandas as pd
import seaborn as sns
import itertools
from collections import defaultdict

# https://pandas.pydata.org/pandas-docs/stable/user_guide/style.html#Builtin-styles

import supervisely_lib as sly

my_app = sly.AppService()

TEAM_ID = int(os.environ['context.teamId'])
WORKSPACE_ID = int(os.environ['context.workspaceId'])
PROJECT_ID = int(os.environ['modal.state.slyProjectId'])
DATASET_ID = os.environ.get('modal.state.slyDatasetId', None)

CELL_TO_IMAGES = None

@my_app.callback("interactive_occurrence_matrix")
@sly.timeit
def interactive_occurrence_matrix(api: sly.Api, task_id, context, state, app_logger):
    global PROJECT_ID, CELL_TO_IMAGES

    if DATASET_ID is not None:
       datasets_ids = [DATASET_ID]
       dataset = api.dataset.get_info_by_id(DATASET_ID)
       if PROJECT_ID is None:
           PROJECT_ID = dataset.project_id
    else:
       datasets_list = api.dataset.get_list(PROJECT_ID)
       datasets_ids = [d.id for d in datasets_list]

    project = api.project.get_info_by_id(PROJECT_ID)
    fields = [
        {"field": "data.projectId", "payload": project.id},
        {"field": "data.projectName", "payload": project.name},
        {"field": "data.projectPreviewUrl", "payload": api.image.preview_url(project.reference_image_url, 100, 100)},
        {"field": "data.progressCurrent", "payload": 0},
        {"field": "data.progressTotal", "payload": project.items_count},
    ]
    api.app.set_fields(task_id, fields)

    meta_json = api.project.get_meta(PROJECT_ID)
    meta = sly.ProjectMeta.from_json(meta_json)
    counters = defaultdict(list)
    for dataset_id in datasets_ids:
        dataset = api.dataset.get_info_by_id(dataset_id)
        images = api.image.get_list(dataset_id)

        for image_infos in sly.batched(images):
            image_ids = [image_info.id for image_info in image_infos]
            ann_infos = api.annotation.download_batch(dataset_id, image_ids)

            for image_info, ann_info in zip(image_infos, ann_infos):
                ann_json = ann_info.annotation
                ann = sly.Annotation.from_json(ann_json, meta)

                classes_on_image = set()
                for label in ann.labels:
                    classes_on_image.add(label.obj_class.name)

                all_pairs = set(frozenset(pair) for pair in itertools.product(classes_on_image, classes_on_image))
                for p in all_pairs:
                    counters[p].append((image_info, dataset))

    CELL_TO_IMAGES = defaultdict(lambda: defaultdict(list))
    pd_data = []
    class_names = [cls.name for cls in meta.obj_classes]
    columns = ["name", *class_names]
    for cls_name1 in class_names:
        cur_row = [cls_name1]
        for cls_name2 in class_names:
            key = frozenset([cls_name1, cls_name2])
            imgs_cnt = len(counters[key])
            cur_row.append(imgs_cnt)

            cell_images_data = []
            for (info, ds_info) in counters[key]:
                cell_images_data.append([
                    info.id,
                    '<a href="{0}" rel="noopener noreferrer" target="_blank">{1}</a>'
                        .format(api.image.url(TEAM_ID, WORKSPACE_ID, project.id, info.dataset_id, info.id), info.name),
                    ds_info.name,
                    ds_info.id
                ])

            cell_table = {
                "columns": ["id", "name", "dataset", "dataset id"],
                "data": cell_images_data
            }
            CELL_TO_IMAGES[cls_name1][cls_name2] = cell_table
            if cls_name2 != cls_name1:
                CELL_TO_IMAGES[cls_name2][cls_name1] = cell_table
        pd_data.append(cur_row)

    fields = [
        {"field": "data.table", "payload": {"columns": columns, "data": pd_data}},
        {"field": "data.cellToImages", "payload": CELL_TO_IMAGES},
    ]
    api.app.set_fields(task_id, fields)
    my_app.stop()


def main():
    sly.logger.info("Script arguments", extra={
        "TEAM_ID": TEAM_ID,
        "WORKSPACE_ID": WORKSPACE_ID,
        "PROJECT_ID": PROJECT_ID,
        "DATASET_ID": DATASET_ID
    })

    data = {
        "projectId": "",
        "projectName": "",
        "projectPreviewUrl": "",
        "progressCurrent": 0,
        "progressTotal": 0,
        "clickedCell": "not clicked",
        "table": {"columns": [], "data": []},
        "selectedRow": {},
        "selectedColumnName": "",
        "cellToImages": {"columns": [], "data": []}
    }
    state = {
    }

    my_app.run(data=data, state=state, initial_events=[{"command": "interactive_occurrence_matrix"}])


if __name__ == "__main__":
    sly.main_wrapper("main", main)