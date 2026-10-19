"""Danh mục 400 bài học: tên ký hiệu, chủ đề, video mẫu."""
import json
from functools import lru_cache

import numpy as np
import pandas as pd

from ..config import GLOSS_CSV, REFERENCE_KEYPOINT_DIR, REFERENCE_VIDEO_DIR, REFERENCES_JSON, TOPICS_JSON

REFERENCE_URL = "/media/reference"


class CatalogError(LookupError):
    pass


class Catalog:
    def __init__(self):
        glosses = pd.read_csv(GLOSS_CSV, encoding="utf-8-sig")
        self.gloss = {int(r.label): str(r.gloss) for r in glosses.itertuples(index=False)}

        topics = json.loads(TOPICS_JSON.read_text(encoding="utf-8"))
        self.groups = topics["groups"]
        self.topic_of = {}
        self.topics = {}
        for group in self.groups:
            for topic in group["topics"]:
                self.topics[topic["id"]] = {**topic, "group": group["id"], "group_name": group["name"]}
                for label in topic["labels"]:
                    self.topic_of[int(label)] = topic["id"]

        missing = sorted(set(self.gloss) - set(self.topic_of))
        if missing:
            raise ValueError(f"topics.json thiếu các label: {missing}")

        if REFERENCES_JSON.exists():
            refs = json.loads(REFERENCES_JSON.read_text(encoding="utf-8"))
        else:
            refs = {"signer": None, "fps": 25.0, "items": {}}
        self.reference_signer = refs.get("signer")
        self.reference_fps = float(refs.get("fps", 25.0))
        self.references = {int(k): v for k, v in refs.get("items", {}).items()}

    # ------------------------------------------------------------------
    def gloss_of_index(self, index):
        """Chỉ số lớp của model (0-399) -> tên ký hiệu."""
        return self.gloss[index + 1]

    def has_reference(self, label):
        item = self.references.get(label)
        return bool(item) and (REFERENCE_VIDEO_DIR / f"{item['video_id']}.mp4").exists()

    def summary(self):
        """Toàn bộ danh mục cho trang thư viện (nhỏ, gửi một lần)."""
        groups = []
        for group in self.groups:
            groups.append({
                "id": group["id"],
                "name": group["name"],
                "topics": [
                    {"id": t["id"], "name": t["name"], "labels": [int(x) for x in t["labels"]]}
                    for t in group["topics"]
                ],
            })
        lessons = [
            {"label": label, "gloss": gloss, "topic": self.topic_of[label], "reference": self.has_reference(label)}
            for label, gloss in sorted(self.gloss.items())
        ]
        return {"groups": groups, "lessons": lessons, "signer": self.reference_signer}

    def lesson(self, label):
        if label not in self.gloss:
            raise CatalogError(f"Không có bài học số {label}.")
        topic = self.topics[self.topic_of[label]]
        labels = [int(x) for x in topic["labels"]]
        pos = labels.index(label)

        def brief(lab):
            return {"label": lab, "gloss": self.gloss[lab]} if lab is not None else None

        lesson = {
            "label": label,
            "gloss": self.gloss[label],
            "topic": {"id": topic["id"], "name": topic["name"], "group": topic["group_name"]},
            "position": pos + 1,
            "count": len(labels),
            "prev": brief(labels[pos - 1] if pos > 0 else None),
            "next": brief(labels[pos + 1] if pos + 1 < len(labels) else None),
            "reference": None,
        }
        if self.has_reference(label):
            item = self.references[label]
            lesson["reference"] = {
                "video_url": f"{REFERENCE_URL}/{item['video_id']}.mp4",
                "video_id": item["video_id"],
                "signer": self.reference_signer,
                "fps": self.reference_fps,
                "frames": int(self.reference_keypoints(label).shape[0]),
            }
        return lesson

    @lru_cache(maxsize=64)
    def reference_keypoints(self, label):
        item = self.references.get(label)
        if not item:
            raise CatalogError(f"Bài {label} chưa có video mẫu. Chạy scripts/build_references.py.")
        return np.load(REFERENCE_KEYPOINT_DIR / f"{item['video_id']}.npy")
