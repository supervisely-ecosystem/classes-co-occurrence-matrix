import os
import pandas as pd
import seaborn as sns
import itertools
from collections import defaultdict

import supervisely_lib as sly

my_app = sly.AppService()

TEAM_ID = int(os.environ['context.teamId'])
WORKSPACE_ID = int(os.environ['context.workspaceId'])
PROJECT_ID = int(os.environ['modal.state.slyProjectId'])
DATASET_ID = int(os.environ.get('modal.state.slyDatasetId'))

@my_app.callback("interactive_coexistence_matrix")
@sly.timeit
def interactive_coexistence_matrix(api: sly.Api, task_id, context, state, app_logger):
    if DATASET_ID is not None:
       datasets_ids = [DATASET_ID]
    else:
       datasets_list = api.dataset.get_list(PROJECT_ID)
       datasets_ids = [d.id for d in datasets_list]

    meta_json = api.project.get_meta(PROJECT_ID)
    meta = sly.ProjectMeta.from_json(meta_json)
    counters = defaultdict(list)
    for dataset_id in datasets_ids:
        images = api.image.get_list(dataset_id)

        for batch in sly.batched(images):
            image_ids = [image_info.id for image_info in batch]
            ann_infos = api.annotation.download_batch(dataset_id, image_ids)

            for idx, ann_info in enumerate(ann_infos):
                ann_json = ann_info.annotation
                ann = sly.Annotation.from_json(ann_json, meta)
                image_info = batch[idx]

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
            imgs_cnt = len(counters[key])
            cur_row.append(imgs_cnt)
        pd_data.append(cur_row)

    df = pd.DataFrame(data=pd_data, columns=columns)
    cm = sns.light_palette("green", as_cmap=True)
    html = df.style.background_gradient(cmap=cm, low=0, high=1).hide_index().set_properties(**{'font-size': '20px', 'text-align': 'center',
                       'border-color': 'black'}).set_table_styles([{'selector': '',
                        'props' : [('border',
                                    '2px solid green')]}]).render()

    my_app.stop()


def main():
    sly.logger.info("Script arguments", extra={
        "PROJECT_ID": PROJECT_ID
    })

    my_app.run(initial_events=[{"command": "interactive_coexistence_matrix"}])


if __name__ == "__main__":
    sly.main_wrapper("main", main)