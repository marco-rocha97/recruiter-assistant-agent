from fastapi import APIRouter, HTTPException

from src.features.dataset.schemas import DatasetInfo
from src.lib.vectorstore.chroma import DATA_DIR

router = APIRouter()

_dataset_info: DatasetInfo | None = None


@router.get("/dataset", response_model=DatasetInfo)
def get_dataset() -> DatasetInfo:
    global _dataset_info
    if _dataset_info is None:
        path = DATA_DIR / "exclusions.json"
        try:
            _dataset_info = DatasetInfo.model_validate_json(path.read_text())
        except Exception:
            raise HTTPException(status_code=500, detail="Dataset info unavailable")
    return _dataset_info
