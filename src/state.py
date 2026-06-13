from typing import TypedDict, Optional

try:
    from typing import NotRequired
except ImportError:
    from typing_extensions import NotRequired


class PipelineState(TypedDict):
    title: str
    content: str
    polished: str
    enhanced: str
    formatted: str
    draft_media_id: str
    error: NotRequired[Optional[str]]
    metadata: dict
