import os
import pandas as pd
import seaborn as sns
import matplotlib
import itertools
from collections import defaultdict
import supervisely_lib as sly


my_app = sly.AppService()

TEAM_ID = int(os.environ['context.teamId'])
WORKSPACE_ID = int(os.environ['context.workspaceId'])
PROJECT_ID = int(os.environ['modal.state.slyProjectId'])
DATASET_ID = os.environ.get('modal.state.slyDatasetId', None)

CELL_TO_IMAGES = None

cmap = sns.light_palette("green", as_cmap=True)
#https://stackoverflow.com/questions/25408393/getting-individual-colors-from-a-color-map-in-matplotlib
#https://towardsdatascience.com/heatmap-basics-with-pythons-seaborn-fb92ea280a6c

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

    # for compatibility with old instances
    if project.items_count is None:
        project = project._replace(items_count=api.project.get_images_count(project.id))

    fields = [
        {"field": "data.started", "payload": True},
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

    progress = sly.Progress("Processing", project.items_count, app_logger)
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
            progress.iters_done_report(len(image_infos))
            fields = [
                {"field": "data.progressCurrent", "payload": progress.current},
                {"field": "data.progress", "payload": int(progress.current * 100 / progress.total)}

            ]
            api.app.set_fields(task_id, fields)

    class_names = [cls.name for cls in meta.obj_classes]

    #colors for pallete
    min_value = None
    max_value = None
    for cls_name1 in class_names:
        for cls_name2 in class_names:
            key = frozenset([cls_name1, cls_name2])
            imgs_cnt = len(counters[key])
            min_value = imgs_cnt if min_value is None else min(min_value, imgs_cnt)
            max_value = imgs_cnt if max_value is None else max(max_value, imgs_cnt)
    norm = matplotlib.colors.Normalize(vmin=min_value, vmax=max_value)

    # build finial table
    CELL_TO_IMAGES = defaultdict(lambda: defaultdict(list))
    pd_data = []
    columns = ["name", *class_names]
    for cls_name1 in class_names:
        cur_row = [cls_name1]
        for cls_name2 in class_names:
            key = frozenset([cls_name1, cls_name2])
            imgs_cnt = len(counters[key])
            rgba = cmap(norm(imgs_cnt), bytes=True)
            hex = sly.color.rgb2hex(rgba[:3])
            #cur_row.append(imgs_cnt)
            cur_row.append(f'<div><i class="zmdi zmdi-stop mr5" style="color: {hex}"></i>{imgs_cnt}</div>')

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

    # save report to file *.lnk (link to report)
    report_name = f"{project.id}_{project.name}.lnk"
    local_path = os.path.join(my_app.data_dir, report_name)
    sly.fs.ensure_base_path(local_path)
    with open(local_path, "w") as text_file:
        print(my_app.app_url, file=text_file)
    remote_path = f"/reports/classes-co-occurrence/{report_name}"
    remote_path = api.file.get_free_name(TEAM_ID, remote_path)
    report_name = sly.fs.get_file_name_with_ext(remote_path)
    file_info = api.file.upload(TEAM_ID, local_path, remote_path)
    report_url = api.file.get_url(file_info.id)

    fields = [
        {"field": "data.started", "payload": False},
        {"field": "data.table", "payload": {"columns": columns, "data": pd_data}},
        {"field": "data.cellToImages", "payload": CELL_TO_IMAGES},
        {"field": "data.savePath", "payload": remote_path},
        {"field": "data.reportName", "payload": report_name},
        {"field": "data.reportUrl", "payload": report_url},
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
        "progress": 0,
        "progressCurrent": 0,
        "progressTotal": 0,
        "clickedCell": "not clicked",
        "table": {"columns": [], "data": []},
        "selection": {},
        "cellToImages": {"columns": [], "data": []},
    }
    state = {
    }

    my_app.run(data=data, state=state, initial_events=[{"command": "interactive_occurrence_matrix"}])


if __name__ == "__main__":
    sly.main_wrapper("main", main)