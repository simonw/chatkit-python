from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, Literal

from pydantic import AnyUrl, BaseModel, Field
from typing_extensions import Annotated, TypeIs, TypeVar

from chatkit.errors import ErrorCode

from .actions import Action
from .widgets import WidgetComponent, WidgetRoot

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    data: list[T] = []
    has_more: bool = False
    after: str | None = None


### REQUEST TYPES


class BaseReq(BaseModel):
    metadata: dict[str, Any] = Field(default_factory=dict)
    """Arbitrary integration-specific metadata."""


class ThreadsGetByIdReq(BaseReq):
    type: Literal["threads.get_by_id"] = "threads.get_by_id"
    params: ThreadGetByIdParams


class ThreadGetByIdParams(BaseModel):
    thread_id: str


class ThreadsCreateReq(BaseReq):
    type: Literal["threads.create"] = "threads.create"
    params: ThreadCreateParams


class ThreadCreateParams(BaseModel):
    input: UserMessageInput


class ThreadListParams(BaseModel):
    limit: int | None = None
    order: Literal["asc", "desc"] = "desc"
    after: str | None = None


class ThreadsListReq(BaseReq):
    type: Literal["threads.list"] = "threads.list"
    params: ThreadListParams


class ThreadsAddUserMessageReq(BaseReq):
    type: Literal["threads.add_user_message"] = "threads.add_user_message"
    params: ThreadAddUserMessageParams


class ThreadAddUserMessageParams(BaseModel):
    input: UserMessageInput
    thread_id: str


class ThreadsAddClientToolOutputReq(BaseReq):
    type: Literal["threads.add_client_tool_output"] = "threads.add_client_tool_output"
    params: ThreadAddClientToolOutputParams


class ThreadAddClientToolOutputParams(BaseModel):
    thread_id: str
    result: Any


class ThreadsCustomActionReq(BaseReq):
    type: Literal["threads.custom_action"] = "threads.custom_action"
    params: ThreadCustomActionParams


class ThreadCustomActionParams(BaseModel):
    thread_id: str
    item_id: str | None = None
    action: Action[str, Any]


class ThreadsRetryAfterItemReq(BaseReq):
    type: Literal["threads.retry_after_item"] = "threads.retry_after_item"
    params: ThreadRetryAfterItemParams


class ThreadRetryAfterItemParams(BaseModel):
    thread_id: str
    item_id: str


class ItemsFeedbackReq(BaseReq):
    type: Literal["items.feedback"] = "items.feedback"
    params: ItemFeedbackParams


class ItemFeedbackParams(BaseModel):
    thread_id: str
    item_ids: list[str]
    kind: FeedbackKind


class AttachmentsDeleteReq(BaseReq):
    type: Literal["attachments.delete"] = "attachments.delete"
    params: AttachmentDeleteParams


class AttachmentDeleteParams(BaseModel):
    attachment_id: str


class AttachmentsCreateReq(BaseReq):
    type: Literal["attachments.create"] = "attachments.create"
    params: AttachmentCreateParams


class AttachmentCreateParams(BaseModel):
    name: str
    size: int
    mime_type: str


class ItemsListReq(BaseReq):
    type: Literal["items.list"] = "items.list"
    params: ItemsListParams


class ItemsListParams(BaseModel):
    thread_id: str
    limit: int | None = None
    order: Literal["asc", "desc"] = "desc"
    after: str | None = None


class ThreadsUpdateReq(BaseReq):
    type: Literal["threads.update"] = "threads.update"
    params: ThreadUpdateParams


class ThreadUpdateParams(BaseModel):
    thread_id: str
    title: str


class ThreadsDeleteReq(BaseReq):
    type: Literal["threads.delete"] = "threads.delete"
    params: ThreadDeleteParams


class ThreadDeleteParams(BaseModel):
    thread_id: str


StreamingReq = (
    ThreadsCreateReq
    | ThreadsAddUserMessageReq
    | ThreadsAddClientToolOutputReq
    | ThreadsRetryAfterItemReq
    | ThreadsCustomActionReq
)

NonStreamingReq = (
    ThreadsGetByIdReq
    | ThreadsListReq
    | ItemsListReq
    | ItemsFeedbackReq
    | AttachmentsCreateReq
    | AttachmentsDeleteReq
    | ThreadsUpdateReq
    | ThreadsDeleteReq
)

ChatKitReq = Annotated[
    StreamingReq | NonStreamingReq,
    Field(discriminator="type"),
]


def is_streaming_req(request: ChatKitReq) -> TypeIs[StreamingReq]:
    return isinstance(
        request,
        (
            ThreadsCreateReq,
            ThreadsAddUserMessageReq,
            ThreadsRetryAfterItemReq,
            ThreadsAddClientToolOutputReq,
            ThreadsCustomActionReq,
        ),
    )


### THREAD STREAM EVENT TYPES


class ThreadCreatedEvent(BaseModel):
    type: Literal["thread.created"] = "thread.created"
    thread: Thread


class ThreadUpdatedEvent(BaseModel):
    type: Literal["thread.updated"] = "thread.updated"
    thread: Thread


class ThreadItemAddedEvent(BaseModel):
    type: Literal["thread.item.added"] = "thread.item.added"
    item: ThreadItem


class ThreadItemUpdated(BaseModel):
    type: Literal["thread.item.updated"] = "thread.item.updated"
    item_id: str
    update: ThreadItemUpdate


class ThreadItemDoneEvent(BaseModel):
    type: Literal["thread.item.done"] = "thread.item.done"
    item: ThreadItem


class ThreadItemRemovedEvent(BaseModel):
    type: Literal["thread.item.removed"] = "thread.item.removed"
    item_id: str


class ThreadItemReplacedEvent(BaseModel):
    type: Literal["thread.item.replaced"] = "thread.item.replaced"
    item: ThreadItem


class ProgressUpdateEvent(BaseModel):
    type: Literal["progress_update"] = "progress_update"
    icon: IconName | None = None
    text: str


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    code: ErrorCode | Literal["custom"] = Field(default="custom")
    message: str | None = None
    allow_retry: bool = Field(default=False)


class NoticeEvent(BaseModel):
    type: Literal["notice"] = "notice"
    level: Literal["info", "warning", "danger"]
    message: str
    """
    Supports markdown e.g. "You've reached your limit of 100 messages. [Upgrade](https://...) to a paid plan."
    """
    title: str | None = None


ThreadStreamEvent = Annotated[
    ThreadCreatedEvent
    | ThreadUpdatedEvent
    | ThreadItemDoneEvent
    | ThreadItemAddedEvent
    | ThreadItemUpdated
    | ThreadItemRemovedEvent
    | ThreadItemReplacedEvent
    | ProgressUpdateEvent
    | ErrorEvent
    | NoticeEvent,
    Field(discriminator="type"),
]

### THREAD ITEM UPDATE TYPES


class AssistantMessageContentPartAdded(BaseModel):
    type: Literal["assistant_message.content_part.added"] = (
        "assistant_message.content_part.added"
    )
    content_index: int
    content: AssistantMessageContent


class AssistantMessageContentPartTextDelta(BaseModel):
    type: Literal["assistant_message.content_part.text_delta"] = (
        "assistant_message.content_part.text_delta"
    )
    content_index: int
    delta: str


class AssistantMessageContentPartAnnotationAdded(BaseModel):
    type: Literal["assistant_message.content_part.annotation_added"] = (
        "assistant_message.content_part.annotation_added"
    )
    content_index: int
    annotation_index: int
    annotation: Annotation


class AssistantMessageContentPartDone(BaseModel):
    type: Literal["assistant_message.content_part.done"] = (
        "assistant_message.content_part.done"
    )
    content_index: int
    content: AssistantMessageContent


class WidgetStreamingTextValueDelta(BaseModel):
    type: Literal["widget.streaming_text.value_delta"] = (
        "widget.streaming_text.value_delta"
    )
    component_id: str
    delta: str
    done: bool


class WidgetRootUpdated(BaseModel):
    type: Literal["widget.root.updated"] = "widget.root.updated"
    widget: WidgetRoot


class WidgetComponentUpdated(BaseModel):
    type: Literal["widget.component.updated"] = "widget.component.updated"
    component_id: str
    component: WidgetComponent


class WorkflowTaskAdded(BaseModel):
    type: Literal["workflow.task.added"] = "workflow.task.added"
    task_index: int
    task: Task


class WorkflowTaskUpdated(BaseModel):
    type: Literal["workflow.task.updated"] = "workflow.task.updated"
    task_index: int
    task: Task


ThreadItemUpdate = (
    AssistantMessageContentPartAdded
    | AssistantMessageContentPartTextDelta
    | AssistantMessageContentPartAnnotationAdded
    | AssistantMessageContentPartDone
    | WidgetStreamingTextValueDelta
    | WidgetComponentUpdated
    | WidgetRootUpdated
    | WorkflowTaskAdded
    | WorkflowTaskUpdated
)


### THREAD TYPES


class ThreadMetadata(BaseModel):
    title: str | None = None
    id: str
    created_at: datetime
    status: ThreadStatus = Field(default_factory=lambda: ActiveStatus())
    # TODO - make not client rendered
    metadata: dict[str, Any] = Field(default_factory=dict)


class ActiveStatus(BaseModel):
    type: Literal["active"] = Field(default="active", frozen=True)


class LockedStatus(BaseModel):
    type: Literal["locked"] = Field(default="locked", frozen=True)
    reason: str | None = None


class ClosedStatus(BaseModel):
    type: Literal["closed"] = Field(default="closed", frozen=True)
    reason: str | None = None


ThreadStatus = Annotated[
    ActiveStatus | LockedStatus | ClosedStatus,
    Field(discriminator="type"),
]


class Thread(ThreadMetadata):
    items: Page[ThreadItem]


### THREAD ITEM TYPES


class ThreadItemBase(BaseModel):
    id: str
    thread_id: str
    created_at: datetime


class UserMessageItem(ThreadItemBase):
    type: Literal["user_message"] = "user_message"
    content: list[UserMessageContent]
    attachments: list[Attachment] = Field(default_factory=list)
    quoted_text: str | None = None
    inference_options: InferenceOptions


class AssistantMessageItem(ThreadItemBase):
    type: Literal["assistant_message"] = "assistant_message"
    content: list[AssistantMessageContent]


class ClientToolCallItem(ThreadItemBase):
    type: Literal["client_tool_call"] = "client_tool_call"
    status: Literal["pending", "completed"] = "pending"
    call_id: str
    name: str
    arguments: dict[str, Any]
    output: Any | None = None


class WidgetItem(ThreadItemBase):
    type: Literal["widget"] = "widget"
    widget: WidgetRoot
    copy_text: str | None = None


class TaskItem(ThreadItemBase):
    type: Literal["task"] = "task"
    task: Task


class WorkflowItem(ThreadItemBase):
    type: Literal["workflow"] = "workflow"
    workflow: Workflow


class EndOfTurnItem(ThreadItemBase):
    type: Literal["end_of_turn"] = "end_of_turn"


class HiddenContextItem(ThreadItemBase):
    """HiddenContext is never sent to the client. It's not officially part of ChatKit. It is only used internally to store additional context in a specific place in the thread."""

    type: Literal["hidden_context_item"] = "hidden_context_item"
    content: Any


ThreadItem = Annotated[
    UserMessageItem
    | AssistantMessageItem
    | ClientToolCallItem
    | WidgetItem
    | WorkflowItem
    | TaskItem
    | HiddenContextItem
    | EndOfTurnItem,
    Field(discriminator="type"),
]


### ASSISTANT MESSAGE TYPES


class AssistantMessageContent(BaseModel):
    annotations: list[Annotation] = Field(default_factory=list)
    text: str
    type: Literal["output_text"] = "output_text"


class Annotation(BaseModel):
    type: Literal["annotation"] = "annotation"
    source: URLSource | FileSource | EntitySource
    index: int | None = None


### USER MESSAGE TYPES


class UserMessageInput(BaseModel):
    content: list[UserMessageContent]
    attachments: list[str]
    quoted_text: str | None = None
    inference_options: InferenceOptions


class UserMessageTextContent(BaseModel):
    type: Literal["input_text"] = "input_text"
    text: str


class UserMessageTagContent(BaseModel):
    type: Literal["input_tag"] = "input_tag"
    id: str
    text: str
    data: dict[str, Any]
    interactive: bool = False


UserMessageContent = Annotated[
    UserMessageTextContent | UserMessageTagContent, Field(discriminator="type")
]


class InferenceOptions(BaseModel):
    tool_choice: ToolChoice | None = None
    model: str | None = None


class ToolChoice(BaseModel):
    id: str


class AttachmentBase(BaseModel):
    id: str
    name: str
    mime_type: str
    upload_url: AnyUrl | None = None
    """
    The URL to upload the file, used for two-phase upload.
    Should be set to None after upload is complete or when using direct upload where uploading happens when creating the attachment object.
    """


class FileAttachment(AttachmentBase):
    type: Literal["file"] = "file"


class ImageAttachment(AttachmentBase):
    type: Literal["image"] = "image"
    preview_url: AnyUrl


Attachment = Annotated[
    FileAttachment | ImageAttachment,
    Field(discriminator="type"),
]


### WORKFLOW TYPES


class Workflow(BaseModel):
    type: Literal["custom", "reasoning"]
    tasks: list[Task]
    summary: WorkflowSummary | None = None
    expanded: bool = False


class CustomSummary(BaseModel):
    title: str
    icon: str | None = None


class DurationSummary(BaseModel):
    duration: int
    """The duration of the workflow in seconds"""


WorkflowSummary = CustomSummary | DurationSummary

### TASK TYPES


class BaseTask(BaseModel):
    status_indicator: Literal["none", "loading", "complete"] = "none"
    """Only used when rendering the task as part of a workflow. Indicates the status of the task."""


class CustomTask(BaseTask):
    type: Literal["custom"] = "custom"
    title: str | None = None
    icon: str | None = None
    content: str | None = None


class SearchTask(BaseTask):
    type: Literal["web_search"] = "web_search"
    title: str | None = None
    title_query: str | None = None
    queries: list[str] = Field(default_factory=list)
    sources: list[URLSource] = Field(default_factory=list)


class ThoughtTask(BaseTask):
    type: Literal["thought"] = "thought"
    title: str | None = None
    content: str


class FileTask(BaseTask):
    type: Literal["file"] = "file"
    title: str | None = None
    sources: list[FileSource] = Field(default_factory=list)


class ImageTask(BaseTask):
    type: Literal["image"] = "image"
    title: str | None = None


Task = Annotated[
    CustomTask | SearchTask | ThoughtTask | FileTask | ImageTask,
    Field(discriminator="type"),
]


### SOURCE TYPES


class SourceBase(BaseModel):
    title: str
    description: str | None = None
    timestamp: str | None = None
    group: str | None = None


class FileSource(SourceBase):
    type: Literal["file"] = "file"
    filename: str


class URLSource(SourceBase):
    type: Literal["url"] = "url"
    url: str
    attribution: str | None = None


class EntitySource(SourceBase):
    type: Literal["entity"] = "entity"
    id: str
    icon: str | None = None
    preview: Literal["lazy"] | None = None


Source = URLSource | FileSource | EntitySource


### MISC TYPES


FeedbackKind = Literal["positive", "negative"]

IconName = Literal[
    "analytics",
    "atom",
    "bolt",
    "book-open",
    "book-closed",
    "calendar",
    "chart",
    "circle-question",
    "compass",
    "cube",
    "globe",
    "keys",
    "lab",
    "images",
    "lifesaver",
    "lightbulb",
    "map-pin",
    "name",
    "notebook",
    "notebook-pencil",
    "page-blank",
    "profile",
    "profile-card",
    "search",
    "sparkle",
    "sparkle-double",
    "square-code",
    "square-image",
    "square-text",
    "suitcase",
    "write",
    "write-alt",
    "write-alt2",
]
