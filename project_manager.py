"""
Git 저장소 동기화를 위한 프로젝트 관리 모듈.
projects.json 파일로 프로젝트 목록을 관리한다.
"""

import os
import json
import shutil
import filecmp
import requests
from datetime import datetime

BASE_DIR = os.path.dirname(__file__)
DATA_FILE = os.path.join(BASE_DIR, "projects.json")
PROXY_FILE = os.path.join(BASE_DIR, "proxy_config.json")
ARCHIVE_ROOT = os.path.join(BASE_DIR, "archive")


# ─── 프록시 설정 ──────────────────────────────────────────
def load_proxy() -> dict:
    if os.path.exists(PROXY_FILE):
        with open(PROXY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"http": "", "https": ""}


def save_proxy(http_proxy: str, https_proxy: str):
    with open(PROXY_FILE, "w", encoding="utf-8") as f:
        json.dump({"http": http_proxy, "https": https_proxy}, f, indent=4)


def _get_proxies() -> dict | None:
    """requests용 프록시 딕셔너리. 설정이 없으면 None."""
    cfg = load_proxy()
    proxies = {}
    if cfg.get("http"):
        proxies["http"] = cfg["http"]
    if cfg.get("https"):
        proxies["https"] = cfg["https"]
    return proxies if proxies else None


# ─── 프로젝트 CRUD ────────────────────────────────────────
def load_projects() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_projects(projects: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(projects, f, ensure_ascii=False, indent=4)


def add_project(project_id: str, name: str, repo_url: str, target_folder: str, token: str = "") -> dict:
    projects = load_projects()
    if project_id in projects:
        raise ValueError("이미 존재하는 프로젝트 ID입니다.")

    projects[project_id] = {
        "name": name,
        "repo_url": repo_url,
        "target_folder": target_folder,
        "token": token,
    }
    save_projects(projects)
    return projects[project_id]


def delete_project(project_id: str):
    projects = load_projects()
    if project_id not in projects:
        raise KeyError("프로젝트를 찾을 수 없습니다.")

    del projects[project_id]
    save_projects(projects)


# ─── 파일 비교 & 동기화 공통 로직 ──────────────────────────
def get_all_relative_files(directory: str) -> list[str]:
    file_paths = []
    if not os.path.exists(directory):
        return file_paths
    for root, _, files in os.walk(directory):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, directory)
            file_paths.append(rel_path)
    return file_paths


def _sync_from_zip(project_id: str, zip_path: str) -> str:
    """ZIP 파일로부터 프로젝트를 동기화한다. 공통 로직."""
    projects = load_projects()
    if project_id not in projects:
        raise KeyError("프로젝트를 찾을 수 없습니다.")

    config = projects[project_id]
    project_name = config["name"]
    target_folder = config["target_folder"]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_folder = os.path.join(ARCHIVE_ROOT, project_id, timestamp)
    temp_extract = os.path.join(BASE_DIR, f"temp_extract_{project_id}")

    try:
        # 1. 압축 해제
        shutil.unpack_archive(zip_path, temp_extract)
        extracted_items = os.listdir(temp_extract)
        if not extracted_items:
            raise Exception("압축 파일이 비어있습니다.")

        # ZIP 안에 래퍼 폴더가 있으면 그 안으로 진입
        wrapper = os.path.join(temp_extract, extracted_items[0])
        if os.path.isdir(wrapper) and len(extracted_items) == 1:
            source_folder = wrapper
        else:
            source_folder = temp_extract

        # 2. 변경점 비교
        new_files = get_all_relative_files(source_folder)
        old_files = get_all_relative_files(target_folder)

        new_files_set = set(new_files)
        old_files_set = set(old_files)

        to_archive, to_copy, to_delete = [], [], []

        for rel_path in new_files_set:
            src_path = os.path.join(source_folder, rel_path)
            dst_path = os.path.join(target_folder, rel_path)

            if rel_path not in old_files_set:
                to_copy.append(rel_path)
            else:
                if not filecmp.cmp(src_path, dst_path, shallow=False):
                    to_archive.append(rel_path)
                    to_copy.append(rel_path)

        for rel_path in old_files_set:
            if rel_path not in new_files_set:
                to_archive.append(rel_path)
                to_delete.append(rel_path)

        # 3. 파일 작업 실행
        if not to_copy and not to_delete:
            return f"[{project_name}] 최신 상태입니다. (변경된 파일 없음)"

        if to_archive:
            for rel_path in to_archive:
                src_file = os.path.join(target_folder, rel_path)
                archive_file = os.path.join(archive_folder, rel_path)
                os.makedirs(os.path.dirname(archive_file), exist_ok=True)
                shutil.copy2(src_file, archive_file)

        for rel_path in to_delete:
            target_file = os.path.join(target_folder, rel_path)
            os.remove(target_file)

        for rel_path in to_copy:
            src_file = os.path.join(source_folder, rel_path)
            dst_file = os.path.join(target_folder, rel_path)
            os.makedirs(os.path.dirname(dst_file), exist_ok=True)
            shutil.copy2(src_file, dst_file)

        return f"[{project_name}] 동기화 완료. (변경: {len(to_copy)}건, 삭제: {len(to_delete)}건 | 백업: {archive_folder})"

    finally:
        if os.path.exists(temp_extract):
            shutil.rmtree(temp_extract)


def sync_project(project_id: str) -> str:
    """URL에서 ZIP을 다운로드하여 동기화한다. (프록시 설정 반영)"""
    projects = load_projects()
    if project_id not in projects:
        raise KeyError("프로젝트를 찾을 수 없습니다.")

    config = projects[project_id]
    repo_url = config["repo_url"]
    token = config.get("token", "")

    temp_zip = os.path.join(BASE_DIR, f"temp_{project_id}.zip")

    try:
        headers = {"Authorization": f"token {token}"} if token else {}
        proxies = _get_proxies()
        response = requests.get(repo_url, headers=headers, proxies=proxies, timeout=120)

        if response.status_code != 200:
            raise Exception(f"다운로드 실패 (상태 코드: {response.status_code}) - URL, 토큰, 또는 프록시 설정을 확인하세요.")

        with open(temp_zip, "wb") as f:
            f.write(response.content)

        return _sync_from_zip(project_id, temp_zip)

    finally:
        if os.path.exists(temp_zip):
            os.remove(temp_zip)


def sync_project_from_file(project_id: str, file_bytes: bytes) -> str:
    """업로드된 ZIP 파일로 동기화한다. (네트워크 불필요)"""
    temp_zip = os.path.join(BASE_DIR, f"temp_{project_id}.zip")

    try:
        with open(temp_zip, "wb") as f:
            f.write(file_bytes)

        return _sync_from_zip(project_id, temp_zip)

    finally:
        if os.path.exists(temp_zip):
            os.remove(temp_zip)
