from datetime import datetime
from decimal import Decimal

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from app.database import SessionLocal
from app.models.mill import Mill
from app.models.rework_ticket import REWORK_TICKET_STATUSES, ReworkTicket
from app.models.viscosity_sample import ViscositySample
from app.serializers import rework_ticket_json
from app.utils import error, normalize_datetime

bp = Blueprint("rework_tickets", __name__, url_prefix="/api/rework-tickets")

# 状态机:open -> rework_done -> closed,不可回退、不可跳级
_NEXT_STATUS = {"open": "rework_done", "rework_done": "closed"}


def _validate(body: dict) -> str | None:
    mill_id = int(body.get("millId") or 0)
    if mill_id <= 0:
        return "请选择研磨机"

    complaint_ref = str(body.get("complaintRef", "")).strip()
    if not complaint_ref:
        return "客诉单号不能为空"

    severity = float(body.get("severityPaS") or 0)
    if severity <= 0:
        return "粘度偏差(Pa·s)必须大于 0"

    opened_at = str(body.get("openedAt", "")).strip()
    if not opened_at:
        return "开立时间不能为空"

    db = SessionLocal()
    try:
        if not db.get(Mill, mill_id):
            return "研磨机不存在"
    finally:
        db.close()

    return None


def _samples_after_open_count(db, ticket: ReworkTicket) -> int:
    return (
        db.query(ViscositySample)
        .filter(
            ViscositySample.mill_id == ticket.mill_id,
            ViscositySample.sampled_at > ticket.opened_at,
        )
        .count()
    )


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
        data = rework_ticket_json(row)
        data["samplesAfterOpen"] = _samples_after_open_count(db, row)
        return jsonify(data)
    finally:
        db.close()


@bp.post("")
@jwt_required()
def create_ticket():
    body = request.get_json(silent=True) or {}
    err = _validate(body)
    if err:
        return error(err, 400)

    db = SessionLocal()
    try:
        row = ReworkTicket(
            mill_id=int(body["millId"]),
            complaint_ref=str(body["complaintRef"]).strip(),
            severity_pa_s=Decimal(str(body["severityPaS"])),
            status="open",
            opened_at=normalize_datetime(str(body["openedAt"])),
            closed_at=None,
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
        if row.status == "closed":
            return error("任务已关闭，禁止修改粘度目标等字段", 409)

        row.mill_id = int(body["millId"])
        row.complaint_ref = str(body["complaintRef"]).strip()
        row.severity_pa_s = Decimal(str(body["severityPaS"]))
        row.opened_at = normalize_datetime(str(body["openedAt"]))
        db.commit()
        db.refresh(row)
        return jsonify(rework_ticket_json(row))
    finally:
        db.close()


@bp.post("/<int:item_id>/status")
@jwt_required()
def transition_status(item_id: int):
    body = request.get_json(silent=True) or {}
    target = str(body.get("status") or "").strip()
    if target not in REWORK_TICKET_STATUSES:
        return error("目标状态无效，应为 open / rework_done / closed", 400)

    db = SessionLocal()
    try:
        row = db.get(ReworkTicket, item_id)
        if not row:
            return error("回磨任务不存在", 404)

        if _NEXT_STATUS.get(row.status) != target:
            return error(f"状态流转无效:{row.status} 不能变更为 {target}", 409)

        if target == "closed":
            if _samples_after_open_count(db, row) < 1:
                return error("关闭前要求该机在开立时间之后至少有 1 条粘度取样", 409)
            row.closed_at = datetime.now()

        row.status = target
        db.commit()
        db.refresh(row)
        return jsonify(rework_ticket_json(row))
    finally:
        db.close()
