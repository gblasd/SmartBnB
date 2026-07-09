"""Offline evaluation against golden dataset."""
import json

class OfflineEvaluator:
    def __init__(self, dataset_path: str = "evaluation/golden_dataset.json"):
        with open(dataset_path) as f:
            self.dataset = json.load(f)
