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


@my_app.callback("interactive_occurrence_matrix")
@sly.timeit
def interactive_occurrence_matrix(api: sly.Api, task_id, context, state, app_logger):
    global PROJECT_ID
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
                    counters[p].append(image_info)

    pd_data = []
    class_names = [cls.name for cls in meta.obj_classes]
    columns = ["name", *class_names]
    for cls_name1 in class_names:
        cur_row = [cls_name1]
        for cls_name2 in class_names:
            key = frozenset([cls_name1, cls_name2])
            imgs_cnt = f'<a href="#" data-row="{cls_name1}" data-col="{cls_name2}">Website</a>'
            #imgs_cnt = len(counters[key])
            #imgs_cnt = f'<el-button type="text" @click="data.clickedCell=row: {cls_name1} col:{cls_name2}">{len(counters[key])}</el-button>'
            cur_row.append(imgs_cnt)
        pd_data.append(cur_row)


    df = pd.DataFrame(data=pd_data, columns=columns)
    cm = sns.light_palette("green", as_cmap=True)

    def make_clickable(val):
        return val# '<a href="#">{}</a>'.format(val)
        index_arr = []
        values_arr = []
        row_name = ""
        for index, value in val.items():
            index_arr.append(index)
            if index == "name":
                values_arr.append(value)
                row_name = value
            else:
                #values_arr.append("777")
                values_arr.append(
                   f'<a href="#" data-row="{row_name}" data-col="{index}">{value}</a>'
                )
        return pd.Series(values_arr, index=index_arr)
        #return #'<a href="{}">{}</a>'.format(val, val)

    #df2 = df.style.background_gradient(cmap=cm)

    #tableHtml = df.style.background_gradient(cmap=cm).apply(make_clickable, axis="columns").hide_index().render()
    ppp = df.style.background_gradient(cmap=cm).hide_index().apply(make_clickable, axis=1)#.format(make_clickable)
    tableHtml = df.style.background_gradient(cmap=cm).hide_index().format(make_clickable).render()

    # xxx = df.style.format(make_clickable).render()
    fields = [
        {"field": "data.table", "payload": {
            "columns": columns,
            "data": pd_data
        }},
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
        "table": {"columns": [], "data": []}
    }
    state = {
    }

    my_app.run(data=data, state=state, initial_events=[{"command": "interactive_occurrence_matrix"}])


if __name__ == "__main__":
    sly.main_wrapper("main", main)