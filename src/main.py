import os
import itertools
from collections import defaultdict
import supervisely as sly
from supervisely.app.v1.app_service import AppService

my_app: AppService = AppService()

TEAM_ID = int(os.environ['context.teamId'])
WORKSPACE_ID = int(os.environ['context.workspaceId'])
PROJECT_ID = int(os.environ['modal.state.slyProjectId'])
DATASET_ID = os.environ.get('modal.state.slyDatasetId', None)

project = None
CELL_TO_IMAGES = None


@my_app.callback("interactive_occurrence_matrix")
@sly.timeit
def interactive_occurrence_matrix(api: sly.Api, task_id, context, state, app_logger):
    global PROJECT_ID, CELL_TO_IMAGES, project
    project = api.project.get_info_by_id(PROJECT_ID)
    input_name = project.name
    if DATASET_ID is not None:
        datasets_ids = [DATASET_ID]
        dataset = api.dataset.get_info_by_id(DATASET_ID)
        if PROJECT_ID is None:
            PROJECT_ID = dataset.project_id
        total_progress = api.dataset.get_info_by_id(DATASET_ID).items_count
        input_name += f" / Dataset: {dataset.name}"
    else:
        datasets_list = api.dataset.get_list(PROJECT_ID)
        datasets_ids = [d.id for d in datasets_list]
        total_progress = project.items_count

    fields = [
        {"field": "data.started", "payload": True},
        {"field": "data.loading", "payload": True},
        {"field": "data.projectId", "payload": project.id},
        {"field": "data.projectName", "payload": input_name},
        {"field": "data.projectPreviewUrl", "payload": api.image.preview_url(project.reference_image_url, 100, 100)},
        {"field": "data.progressCurrent", "payload": 0},
        {"field": "data.progressTotal", "payload": total_progress},
    ]
    api.app.set_fields(task_id, fields)

    meta_json = api.project.get_meta(PROJECT_ID)
    meta = sly.ProjectMeta.from_json(meta_json)
    class_names = [cls.name for cls in meta.obj_classes]
    counters = defaultdict(list)

    progress = sly.Progress("Processing", total_progress, app_logger)
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

    # build finial table
    CELL_TO_IMAGES = counters # defaultdict(lambda: defaultdict(list))
    pd_data = []
    columns = ["name", *class_names]
    for cls_name1 in class_names:
        cur_row = [cls_name1]
        for cls_name2 in class_names:
            key = frozenset([cls_name1, cls_name2])
            imgs_cnt = len(counters[key])
            cur_row.append(imgs_cnt)
        pd_data.append(cur_row)

    # save report to file *.lnk (link to report)
    report_name = f"{project.id}_{project.name}.lnk"
    local_path = os.path.join(my_app.data_dir, report_name)
    sly.fs.ensure_base_path(local_path)
    with open(local_path, "w") as text_file:
        print(my_app.app_url, file=text_file)
    remote_path = api.file.get_free_name(TEAM_ID, f"/reports/classes-co-occurrence/{report_name}")
    report_name = sly.fs.get_file_name_with_ext(remote_path)
    file_info = api.file.upload(TEAM_ID, local_path, remote_path)
    report_url = api.file.get_url(file_info.id)
    api.task.set_output_report(task_id, file_info.id, file_info.name)

    fields = [
        {"field": "data.started", "payload": False},
        {"field": "data.loading", "payload": False},
        {"field": "data.table", "payload": {"columns": columns, "data": pd_data}},
        {"field": "data.savePath", "payload": remote_path},
        {"field": "data.reportName", "payload": report_name},
        {"field": "data.reportUrl", "payload": report_url},
    ]
    api.app.set_fields(task_id, fields)


@my_app.callback("show_images")
@sly.timeit
def show_images(api: sly.Api, task_id, context, state, app_logger):
    if state["selection"]["selectedRowData"] is not None and state["selection"]["selectedColumnName"] is not None:
        class1 = state["selection"]["selectedRowData"]["name"]
        class2 = state["selection"]["selectedColumnName"]
    else:
        return
    key = frozenset([class1, class2])
    
    bad_path = "/bad/path/not_exists.tar"

    api.file.get_info_by_path(TEAM_ID, bad_path).sizeb

    images = CELL_TO_IMAGES[key]
    cell_images_data = []
    for (info, ds_info) in images:
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

    fields = [
        {"field": "data.cellToImages", "payload": cell_table},
    ]
    api.app.set_fields(task_id, fields)


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
        "loading": True
    }
    state = {
        "selection": {}
    }
    my_app.run(data=data, state=state, initial_events=[{"command": "interactive_occurrence_matrix"}])


if __name__ == "__main__":
    sly.main_wrapper("main", main)