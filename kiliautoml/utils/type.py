from typing_extensions import Literal

AssetStatusT = Literal["TODO", "ONGOING", "LABELED", "TO_REVIEW", "REVIEWED"]
LabelTypeT = Literal["PREDICTION", "DEFAULT", "AUTOSAVE", "REVIEW", "INFERENCE"]
CommandT = Literal["train", "predict", "label_errors", "prioritize"]
