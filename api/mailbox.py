# api/mailbox.py - 邮箱与表单路由

from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(prefix="/api", tags=["mailbox"])

_PROJECT_ROOT = Path(__file__).parent.parent


# ========== 邮箱 ==========
# 注意: /mailbox/file 必须放在 /mailbox/{player_name} 之前

@router.get("/mailbox/file")
async def api_get_mailbox_file(path: str):
    full_path = (_PROJECT_ROOT / path).resolve()
    try:
        full_path.relative_to(_PROJECT_ROOT.resolve())
    except ValueError:
        return {"status": "error", "message": "Path traversal detected"}

    path_parts = path.replace("\\", "/").split("/")
    if len(path_parts) < 1 or path_parts[0] not in ["workspace", "data"]:
        return {"status": "error", "message": "Access denied - only workspace/ and data/ allowed"}
    if not full_path.exists():
        return {"status": "error", "message": f"File not found: {path}"}
    if not full_path.is_file():
        return {"status": "error", "message": "Not a file"}

    return FileResponse(path=str(full_path), filename=full_path.name)


@router.get("/mailbox/{player_name}")
async def api_get_mailbox(player_name: str):
    from tools import mailbox as mailbox_module
    mails = mailbox_module.get_inbox(player_name)
    unread_count = mailbox_module.get_unread_count(player_name)
    return {"status": "ok", "mails": mails, "unread_count": unread_count}


@router.get("/mailbox/{player_name}/unread")
async def api_get_unread_count(player_name: str):
    from tools import mailbox as mailbox_module
    return {"status": "ok", "unread_count": mailbox_module.get_unread_count(player_name)}


@router.post("/mailbox/{player_name}/read/{mail_id}")
async def api_mark_as_read(player_name: str, mail_id: str):
    from tools import mailbox as mailbox_module
    success = mailbox_module.mark_as_read(player_name, mail_id)
    if success:
        return {"status": "ok", "message": "Marked as read"}
    return {"status": "error", "message": "Mail not found"}


@router.post("/mailbox/{player_name}/read-all")
async def api_mark_all_as_read(player_name: str):
    from tools import mailbox as mailbox_module
    count = mailbox_module.mark_all_as_read(player_name)
    return {"status": "ok", "message": f"Marked {count} mails as read", "count": count}


@router.delete("/mailbox/{player_name}/{mail_id}")
async def api_delete_mail(player_name: str, mail_id: str):
    from tools import mailbox as mailbox_module
    success = mailbox_module.delete_mail(player_name, mail_id)
    if success:
        return {"status": "ok", "message": "Mail deleted"}
    return {"status": "error", "message": "Mail not found"}


@router.post("/mailbox/{player_name}/star/{mail_id}")
async def api_toggle_star(player_name: str, mail_id: str):
    from tools import mailbox as mailbox_module
    new_state = mailbox_module.toggle_star(player_name, mail_id)
    if new_state is not None:
        return {"status": "ok", "starred": new_state}
    return {"status": "error", "message": "Mail not found"}


# ========== 表单 ==========

@router.get("/form/pending")
async def api_get_pending_forms():
    from tools import form as form_module
    forms = form_module.get_pending_forms()
    return {"status": "ok", "forms": forms, "count": len(forms)}


@router.get("/form/{form_id}")
async def api_get_form(form_id: str):
    from tools import form as form_module
    form = form_module.get_form(form_id)
    if form is None:
        return {"status": "error", "message": "Form not found or expired"}
    return {"status": "ok", "form": form}


@router.post("/form/{form_id}/submit")
async def api_submit_form(form_id: str, response: dict):
    from tools import form as form_module
    return form_module.submit_form(form_id, response)


@router.post("/form/{form_id}/cancel")
async def api_cancel_form(form_id: str):
    from tools import form as form_module
    success = form_module.cancel_form(form_id)
    if success:
        return {"status": "ok", "message": "Form cancelled"}
    return {"status": "error", "message": "Form not found"}
