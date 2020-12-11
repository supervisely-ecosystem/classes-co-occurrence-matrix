import os
import pandas as pd

import supervisely_lib as sly

my_app = sly.AppService()

TEAM_ID = int(os.environ['context.teamId'])
WORKSPACE_ID = int(os.environ['context.workspaceId'])
PROJECT_ID = int(os.environ['modal.state.slyProjectId'])
DATASET_ID = int(os.environ.get('modal.state.slyDatasetId'))


def group_labels(labels):
    d = {}
    for l in labels:
        k = l['classTitle']
        if k in d:
            d[k] = True
        else:
            d[k] = False
    return d

@my_app.callback("interactive_coexistence_matrix")
@sly.timeit
def interactive_coexistence_matrix(api: sly.Api, task_id, context, state, app_logger):
    if PROJECT_ID is not None:
        classes = api.project.get_meta(PROJECT_ID)['classes']
        datasets_list = api.dataset.get_list(PROJECT_ID)
        dataset_ids = [d.id for d in datasets_list]
    else:
        dataset_info = api.dataset.get_info_by_id(DATASET_ID)
        classes = api.project.get_meta(dataset_info.project_id)['classes']
        dataset_ids = [DATASET_ID]

    co_occurrence_table = {}
    for cls1 in classes:
        for cls2 in classes:
            co_occurrence_table[f"{cls1['title']}-{cls2['title']}"] = []

    for dataset_id in dataset_ids:
        anns = api.annotation.get_list(dataset_id)
        for ann_info in anns:
            image_id = ann_info.image_id
            classes_on_img = group_labels(ann_info.annotation['objects'])
            for cls_name1 in classes_on_img:
                for cls_name2 in classes_on_img:
                    if cls_name1 != cls_name2 or classes_on_img[cls_name1] == True:
                        co_occurrence_table[f"{cls_name1}-{cls_name2}"].append(image_id)

    pd_data = []
    columns = ["name", *[cls["title"] for cls in classes]]
    for cls1 in classes:
        cur_row = [cls1["title"]]
        for cls2 in classes:
            imgs_cnt = len(co_occurrence_table[f'{cls1["title"]}-{cls2["title"]}'])
            cur_row.append(imgs_cnt)
        pd_data.append(cur_row)

    df = pd.DataFrame(data=pd_data, columns=columns)
    df.style.background_gradient(cmap='YlGn') \
        .set_properties(**{'font-size': '20px'})

    print(df)

    my_app.stop()


def main():
    sly.logger.info("Script arguments", extra={
        "PROJECT_ID": PROJECT_ID
    })

    my_app.run(initial_events=[{"command": "interactive_coexistence_matrix"}])


if __name__ == "__main__":
    sly.main_wrapper("main", main)