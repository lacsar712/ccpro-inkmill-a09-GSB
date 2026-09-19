from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from app.database import SessionLocal
from app.models.mill import Mill
from app.models.rework_ticket import ReworkTicket
from app.models.viscosity_sample import ViscositySample
from app.serializers import rework_ticket_json
from app.utils import error, normalize_datetime

bp = Blueprint("rework_tickets", __name__, url_prefix="/api/rework-tickets")

# 单向流转:open -> rework_done -> closed
_TRANSITIONS = {"open": "rework_done", "rework_done": "closed"}


def _validate(body: dict) -> str | None:
    mill_id = int(body.get("millId") or 0)
    if mill_id <= 0:
        return "请选择研磨机"

    complaint_ref = str(body.get("complaintRef", "")).strip()
    if not complaint_ref:
        return "客诉编号不能为空"

    try:
        severity = Decimal(str(body.get("severityPaS") or 0))
    except InvalidOperation:
        return "粘度目标(Pa·s)格式无效"
    if severity <= 0:
        return "粘度目标(Pa·s)必须大于 0"

    db = SessionLocal()
    try:
        if not db.get(Mill, mill_id):
            return "研磨机不存在"
    finally:
        db.close()

    return None


@bp.get("")
@jwt_required()
def list_tickets():
    db = SessionLocal()
    try:
        rows = (
            db.query(ReworkTicket)
            .order_by(ReworkTicket.id.desc())
            .all()
        )
        return jsonify([rework_ticket_json(r) for r in rows])
    finally:
        db.close()


@bp.get("/<int:item_id>")
@jwt_required()
def get_ticket(item_id: int):
    db = SessionLocal()
    try:
        row = db.get(ReworkTicket, item_id)
        if not row:
            return error("回磨任务不存在", 404)
        return jsonify(rework_ticket_json(row))
    finally:
        db.close()


@bp.post("")
@jwt_required()
def create_ticket():
    body = request.get_json(silent=True) or {}
    err = _validate(body)
    if err:
        return error(err, 400)

    opened_raw = str(body.get("openedAt", "")).strip()
    db = SessionLocal()
    try:
        row = ReworkTicket(
            mill_id=int(body["millId"]),
            complaint_ref=str(body["complaintRef"]).strip(),
            severity_pa_s=Decimal(str(body["severityPaS"])),
            status="open",
            opened_at=normalize_datetime(opened_raw) if opened_raw else datetime.now(),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return jsonify(rework_ticket_json(row)), 201
    finally:
        db.close()


@bp.put("/<int:item_id>")
@jwt_required()
def update_ticket(item_id: int):
    body = request.get_json(silent=True) or {}
    err = _validate(body)
    if err:
        return error(err, 400)

    db = SessionLocal()
    try:
        row = db.get(ReworkTicket, item_id)
        if not row:
            return error("回磨任务不存在", 404)

        new_severity = Decimal(str(body["severityPaS"]))
        if row.status == "closed" and new_severity != row.severity_pa_s:
            return error("工单已关闭，禁止修改粘度目标", 409)

        row.mill_id = int(body["millId"])
        row.complaint_ref = str(body["complaintRef"]).strip()
        row.severity_pa_s = new_severity
        opened_raw = str(body.get("openedAt", "")).strip()
        if opened_raw:
            row.opened_at = normalize_datetime(opened_raw)
        db.commit()
        db.refresh(row)
        return jsonify(rework_ticket_json(row))
    finally:
        db.close()


@bp.post("/<int:item_id>/transition")
@jwt_required()
def transition_ticket(item_id: int):
    body = request.get_json(silent=True) or {}
    target = str(body.get("status") or "").strip()

    db = SessionLocal()
    try:
        row = db.get(ReworkTicket, item_id)
        if not row:
            return error("回磨任务不存在", 404)

        if _TRANSITIONS.get(row.status) != target:
            return error(
                f"状态流转无效:{row.status} 不能直接变为 {target or '(空)'}", 409
            )

        if target == "closed":
            has_sample = (
                db.query(ViscositySample)
                .filter(
                    ViscositySample.mill_id == row.mill_id,
                    ViscositySample.sampled_at > row.opened_at,
                )
                .first()
            )
            if not has_sample:
                return error(
                    "关闭前需要该研磨机在客诉登记(openedAt)之后至少有 1 条粘度取样", 409
                )
            row.closed_at = datetime.now()

        row.status = target
        db.commit()
        db.refresh(row)
        return jsonify(rework_ticket_json(row))
    finally:
        db.close()
